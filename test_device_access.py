import base64
import copy
import hashlib
import os
import subprocess
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from starlette.requests import Request
import httpx
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives import hashes
from pymongo.errors import DuplicateKeyError
from device_access import DeviceAccess, digest
from crm_admin import router, enrollment_router
import knowledge_base
from ai_router import ReplyRouter, ProviderFailure
from test_ai_router import Database

class Collection:
    def __init__(self): self.docs={}
    async def create_index(self,*a,**k): pass
    async def insert_one(self,doc):
        if doc['_id'] in self.docs: raise DuplicateKeyError('duplicate')
        self.docs[doc['_id']]=copy.deepcopy(doc)
    def matches(self,doc,q):
        for k,v in q.items():
            if isinstance(v,dict) and '$gt' in v:
                if doc.get(k)<=v['$gt']: return False
            elif doc.get(k)!=v: return False
        return True
    async def find_one(self,q):
        return next((copy.deepcopy(x) for x in self.docs.values() if self.matches(x,q)),None)
    async def find_one_and_update(self,q,u,**kw):
        d=next((x for x in self.docs.values() if self.matches(x,q)),None)
        if d is None: return None
        d.update(u['$set']);return copy.deepcopy(d)
    async def update_one(self,q,u,upsert=False):
        d=next((x for x in self.docs.values() if self.matches(x,q)),None)
        if d is None and upsert: d=self.docs.setdefault(q['_id'],{'_id':q['_id']})
        if d is not None:d.update(copy.deepcopy(u['$set']))
        return SimpleNamespace(matched_count=int(d is not None))

class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db=SimpleNamespace(**{n:Collection() for n in ['device_codes','device_nonces','authorized_devices','institutional_knowledge']})
        self.service=DeviceAccess(self.db)
        self.key=ec.generate_private_key(ec.SECP256R1())
        numbers=self.key.public_key().public_numbers()
        enc=lambda n:base64.urlsafe_b64encode(n.to_bytes(32,'big')).decode().rstrip('=')
        self.jwk={'kty':'EC','crv':'P-256','x':enc(numbers.x),'y':enc(numbers.y)}
    async def enrolled(self):
        code=(await self.service.issue('Celular'))['code']
        return (await self.service.enroll(code,self.jwk))['device_id']
    def request(self,identity,body=b'',nonce='unique_nonce_123456',stamp=None,path='/crm/human'):
        stamp=str(int(time.time())) if stamp is None else str(stamp)
        payload='\n'.join(['POST',path,stamp,nonce,hashlib.sha256(body).hexdigest(),'']).encode()
        r,s=utils.decode_dss_signature(self.key.sign(payload,ec.ECDSA(hashes.SHA256())))
        sig=base64.urlsafe_b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode().rstrip('=')
        headers={'x-jarvis-device':identity,'x-jarvis-time':stamp,'x-jarvis-nonce':nonce,'x-jarvis-signature':sig}
        scope={'type':'http','method':'POST','path':path,'query_string':b'', 'headers':[(k.encode(),v.encode()) for k,v in headers.items()]}
        async def receive():return {'type':'http.request','body':body,'more_body':False}
        return Request(scope,receive)
    async def test_code_is_hashed_single_use_and_expires(self):
        issued=await self.service.issue('Celular');code=issued['code']
        self.assertNotIn(code,str(self.db.device_codes.docs))
        await self.service.enroll(code,self.jwk)
        with self.assertRaises(HTTPException):await self.service.enroll(code,self.jwk)
        code=(await self.service.issue('Outro'))['code']
        self.db.device_codes.docs[digest(code)]['expires_at']=datetime.now(timezone.utc)-timedelta(seconds=1)
        with self.assertRaises(HTTPException):await self.service.enroll(code,self.jwk)
    async def test_signature_replay_tamper_expiry_and_revocation(self):
        identity=await self.enrolled();r=self.request(identity,b'abc')
        self.assertEqual(await self.service.verify(r),identity)
        with self.assertRaises(HTTPException):await self.service.verify(r)
        for mode in ['body','path','time','key','revoked']:
            req=self.request(identity,b'abc',nonce='unique_nonce_'+mode+'12345',stamp=int(time.time())-200 if mode=='time' else None)
            if mode=='body':req._body=b'changed'
            if mode=='path':req.scope['path']='/crm/devices/code'
            if mode=='key':self.key=ec.generate_private_key(ec.SECP256R1());req=self.request(identity,nonce='unique_nonce_key23456')
            if mode=='revoked':self.db.authorized_devices.docs[identity]['revoked']=True
            with self.assertRaises(HTTPException):await self.service.verify(req)
    async def test_device_cannot_authorize_another_device(self):
        identity=await self.enrolled();req=self.request(identity,path='/crm/devices/code')
        app=FastAPI();app.include_router(router(lambda:self.db,lambda db:None))
        with patch.dict(os.environ,{'CRM_ADMIN_TOKEN':'x'*48}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as c:
                r=await c.post('/crm/devices/code',headers=dict(req.headers),content=b'')
                self.assertEqual(r.status_code,401)
    async def test_node_webcrypto_signature_is_verified(self):
        # Real WebCrypto key format and raw signature, same API used by Chromium.
        script="""(async()=>{const c=require('node:crypto').webcrypto;let k=await c.subtle.generateKey({name:'ECDSA',namedCurve:'P-256'},false,['sign','verify']);let stamp=String(Math.floor(Date.now()/1000)),nonce='node_nonce_12345678';let hash=Buffer.from(await c.subtle.digest('SHA-256',new Uint8Array())).toString('hex');let sig=await c.subtle.sign({name:'ECDSA',hash:'SHA-256'},k.privateKey,new TextEncoder().encode(['POST','/crm/human',stamp,nonce,hash,''].join('\\n')));console.log(JSON.stringify({jwk:await c.subtle.exportKey('jwk',k.publicKey),stamp,nonce,sig:Buffer.from(sig).toString('base64url'),extractable:k.privateKey.extractable}));})()"""
        data=json.loads(subprocess.check_output(['node','-e',script]))
        self.assertFalse(data['extractable'])
        code=(await self.service.issue('Chrome'))['code']
        identity=(await self.service.enroll(code,data['jwk']))['device_id']
        req=self.request(identity);req.scope['headers']=[(k.encode(),v.encode()) for k,v in {'x-jarvis-device':identity,'x-jarvis-time':data['stamp'],'x-jarvis-nonce':data['nonce'],'x-jarvis-signature':data['sig']}.items()]
        self.assertEqual(await self.service.verify(req),identity)
    async def test_owner_facts_are_seeded_and_shared_by_free_and_paid(self):
        await knowledge_base.initialize(self.db)
        doc=await self.db.institutional_knowledge.find_one({'_id':'nova_vida'})
        self.assertEqual(doc['facts']['duration_months'],6);self.assertEqual(doc['facts']['meals_per_day'],4)
        db=Database();db.institutional_knowledge=self.db.institutional_knowledge;calls=[]
        async def call(provider,messages,config):
            calls.append((provider,messages[0]['content']))
            if provider=='free':raise ProviderFailure(True,60)
            return 'Resposta',0
        with patch.dict(os.environ,{'META_APP_SECRET':'fake','GROQ_API_KEY':'fake','OPENAI_API_KEY':'fake','AI_PAID_FALLBACK_ENABLED':'true','AI_PAID_MAX_CALLS_PER_DAY':'1'}):
            await ReplyRouter(db,call).reply('55123456789','qual a duração?','base')
        self.assertEqual([x[0] for x in calls],['free','paid'])
        self.assertEqual(calls[0][1],calls[1][1]);self.assertIn('6 meses',calls[0][1]);self.assertIn('4 refeições',calls[0][1])
