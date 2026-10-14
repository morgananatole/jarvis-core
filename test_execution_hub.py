import asyncio
import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from fastapi import FastAPI,HTTPException
from execution_hub import ExecutionHub,router,now
from crm_admin import authorize
from test_device_access import Collection as DeviceCollection, Tests as DeviceSignatureTests
from connectors.adapters import Adapters,AdapterError,private_write
from connectors.agent import Client,run

class Collection(DeviceCollection):
    async def update_one(self,q,u,upsert=False):
        d=next((x for x in self.docs.values() if self.matches(x,q)),None)
        if d is None and upsert:
            d=self.docs.setdefault(q['_id'],copy.deepcopy(u.get('$setOnInsert',{'_id':q['_id']})))
        if d is not None:d.update(copy.deepcopy(u.get('$set',{})))
        return SimpleNamespace(matched_count=int(d is not None))

class HubTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.identity='a'*32;self.other='b'*32
        self.db=SimpleNamespace(authorized_devices=Collection(),execution_tasks=Collection(),device_nonces=Collection())
        for i in (self.identity,self.other):self.db.authorized_devices.docs[i]={'_id':i,'revoked':False,'license_id':None}
        self.hub=ExecutionHub(self.db)
    async def task(self,key='task_key_12345678',cap='system.info',identity=None):
        identity=identity or self.identity
        await self.hub.register(identity,{'platform':'Linux','capabilities':[cap]})
        return await self.hub.submit({'device_id':identity,'capability':cap,'args':{}},key)
    async def test_idempotency_and_conflict(self):
        a=await self.task();b=await self.task();self.assertEqual(a['_id'],b['_id']);self.assertEqual(len(self.db.execution_tasks.docs),1)
        with self.assertRaises(HTTPException):await self.hub.submit({'device_id':self.identity,'capability':'system.info','args':{'changed':True}},'task_key_12345678')
    async def test_concurrent_claim_only_once(self):
        await self.task();claims=await asyncio.gather(self.hub.claim(self.identity),self.hub.claim(self.identity))
        self.assertEqual(sum(x is not None for x in claims),1)
    async def test_expiry_and_other_device_do_not_claim(self):
        t=await self.task();self.assertIsNone(await self.hub.claim(self.other))
        self.db.execution_tasks.docs[t['_id']]['expires_at']=now()-timedelta(seconds=1)
        self.assertIsNone(await self.hub.claim(self.identity))
    async def test_revocation_and_customer_license_block(self):
        await self.task();self.db.authorized_devices.docs[self.identity]['revoked']=True
        with self.assertRaises(HTTPException):await self.hub.claim(self.identity)
        self.db.authorized_devices.docs[self.other]['license_id']='customer'
        with self.assertRaises(HTTPException):await self.hub.register(self.other,{'platform':'Linux','capabilities':['system.info']})
    async def test_result_bound_to_device_claim_and_duplicate(self):
        await self.task();t=await self.hub.claim(self.identity)
        body={'claim_token':t['claim_token'],'state':'succeeded','output':{'ok':True}}
        with self.assertRaises(HTTPException):await self.hub.result(self.other,t['_id'],body)
        with self.assertRaises(HTTPException):await self.hub.result(self.identity,t['_id'],{**body,'claim_token':'wrong'})
        self.assertTrue((await self.hub.result(self.identity,t['_id'],body))['accepted'])
        self.assertTrue((await self.hub.result(self.identity,t['_id'],body))['duplicate'])
        self.assertIsNone(await self.hub.claim(self.identity))
    async def test_capability_limits(self):
        with self.assertRaises(HTTPException):await self.hub.register(self.identity,{'platform':'Linux','capabilities':['shell.anything']})
        await self.task()
        with self.assertRaises(HTTPException):await self.hub.submit({'device_id':self.identity,'capability':'screen.click','args':{}},'task_key_abcdefgh')
    async def test_api_owner_required_and_malformed_body(self):
        app=FastAPI();app.include_router(router(lambda:self.db,authorize))
        with patch.dict(os.environ,{'CRM_ADMIN_TOKEN':'s'*48}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
                r=await c.post('/execution/tasks',json={});self.assertEqual(r.status_code,401)
                r=await c.post('/execution/tasks',headers={'authorization':'Bearer '+'s'*48},content='broken');self.assertEqual(r.status_code,400)

class SignedExecutionTests(DeviceSignatureTests):
    # Existing enrollment/signature tests plus real signed claim integration.
    async def test_execution_signed_claim_tamper_replay(self):
        identity=await self.enrolled();self.db.execution_tasks=Collection()
        app=FastAPI();app.include_router(router(lambda:self.db,authorize))
        req=self.request(identity,b'{}',path='/execution/agent/claim')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
            r=await c.post('/execution/agent/claim',headers=dict(req.headers),content=b'{}');self.assertEqual(r.status_code,200)
            r=await c.post('/execution/agent/claim',headers=dict(req.headers),content=b'{}');self.assertEqual(r.status_code,401)

class AdapterTests(unittest.TestCase):
    def test_named_command_executes_real_process_no_remote_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            a=Adapters({'enabled':['command.run'],'commands':{'probe':{'argv':[sys.executable,'-c','print(6*7)'],'cwd':tmp}}})
            result=a.execute('command.run',{'name':'probe'});self.assertEqual(result['exit_code'],0);self.assertEqual(result['text'].strip(),'42')
            with self.assertRaises(AdapterError):a.execute('command.run',{'name':'probe','shell':'rm anything'})
    def test_disabled_screen_and_invalid_android_args(self):
        with self.assertRaises(AdapterError):Adapters({}).execute('screen.click',{'x':1,'y':1})
        with self.assertRaises(AdapterError):Adapters({'enabled':['android.tap'],'android_serial':'bad;command'}).execute('android.tap',{'x':1,'y':1})
    def test_android_uses_fixed_serial_and_argv(self):
        a=Adapters({'enabled':['android.tap'],'android_serial':'device123'})
        with patch.object(a,'run',return_value={'exit_code':0}) as run:
            a.execute('android.tap',{'x':12,'y':34})
            self.assertEqual(run.call_args.args[0],['adb','-s','device123','shell','input','tap','12','34'])
    def test_server_rejects_http_and_embedded_credentials(self):
        for url in ('http://localhost','https://user:secret@example.com','https://example.com/path'):
            with self.assertRaises(ValueError):Client({'server':url})
    def test_local_result_resend_does_not_repeat_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg={'server':'https://example.com','state_file':tmp+'/state.db','enabled':['system.info']}
            task={'_id':'a'*32,'claim_token':'secret','capability':'system.info','args':{}}
            calls=[];fail=[True]
            def call(client,path,body=None,signed=True):
                calls.append(path)
                if path.endswith('/register'):return {}
                if path.endswith('/claim'):return task if fail[0] else None
                if path.endswith('/result') and fail[0]:fail[0]=False;raise OSError('network_down')
                return {'accepted':True}
            with patch.object(Client,'call',call),patch.object(Adapters,'execute',return_value={'ok':True}) as execute:
                with self.assertRaises(OSError):run(cfg,once=True)
                run(cfg,once=True);self.assertEqual(execute.call_count,1)
                self.assertEqual(sum(p.endswith('/result') for p in calls),2)
    def test_private_permissions_and_no_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'key';private_write(p,'private');self.assertEqual(p.stat().st_mode&0o777,0o600)
            link=Path(tmp)/'link';link.symlink_to(p)
            with self.assertRaises(AdapterError):private_write(link,'bad')
