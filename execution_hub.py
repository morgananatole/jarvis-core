"""Owner-issued tasks; signed enrolled devices consume once, never retry blindly."""
import hashlib
import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pymongo import ReturnDocument
from device_access import DeviceAccess

CAPABILITIES = {'system.info', 'pulse.doctor', 'pulse.test', 'command.run',
                'screen.capture', 'screen.click', 'screen.type', 'screen.key',
                'android.info', 'android.capture', 'android.tap', 'android.key',
                'google.drive.list', 'google.docs.read', 'google.docs.append'}

def now(): return datetime.now(timezone.utc)

def valid_identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise HTTPException(400, 'invalid_identity')
    return value

class ExecutionHub:
    def __init__(self, db): self.db = db

    async def initialize(self):
        await self.db.execution_tasks.create_index('purge_at', expireAfterSeconds=0)
        await self.db.execution_tasks.create_index([('device_id',1),('state',1),('created_at',1)])

    async def device(self, identity):
        record = await self.db.authorized_devices.find_one({'_id':valid_identity(identity), 'revoked':False})
        # Licensed customers cannot use the owner's execution hub.
        if not record or record.get('license_id'): raise HTTPException(403, 'owner_device_required')
        return record

    async def register(self, identity, body):
        await self.device(identity)
        await self.initialize()
        if not isinstance(body, dict) or set(body) != {'platform', 'capabilities'}:
            raise HTTPException(400, 'invalid_registration')
        caps = body['capabilities']
        if body['platform'] not in ('Linux', 'Windows', 'Darwin') or not isinstance(caps, list) or not caps or len(caps)>len(CAPABILITIES) or any(not isinstance(c,str) or c not in CAPABILITIES for c in caps):
            raise HTTPException(400, 'invalid_registration')
        await self.db.authorized_devices.update_one({'_id':identity}, {'$set':{
            'execution': {'platform':body['platform'], 'capabilities':sorted(set(caps)), 'last_seen':now()}}})
        return {'registered':True}

    async def submit(self, body, key):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}',key):
            raise HTTPException(400, 'idempotency_key_required')
        if not isinstance(body,dict) or set(body)-{'device_id','capability','args','ttl_seconds'}:
            raise HTTPException(400, 'invalid_task')
        device = await self.device(body.get('device_id'))
        capability, args, ttl = body.get('capability'),body.get('args',{}),body.get('ttl_seconds',300)
        if capability not in device.get('execution',{}).get('capabilities',[]):
            raise HTTPException(409, 'capability_not_registered')
        if not isinstance(args,dict) or len(json.dumps(args).encode())>16000 or type(ttl) is not int or not 10<=ttl<=3600:
            raise HTTPException(400, 'invalid_task')
        identity = hashlib.sha256(key.encode()).hexdigest()[:32]
        fingerprint = hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
        await self.db.execution_tasks.update_one({'_id':identity}, {'$setOnInsert':{
            '_id':identity,'device_id':device['_id'],'capability':capability,'args':args,
            'fingerprint':fingerprint,'state':'queued','created_at':now(),
            'expires_at':now()+timedelta(seconds=ttl),'purge_at':now()+timedelta(days=7)}},upsert=True)
        task = await self.db.execution_tasks.find_one({'_id':identity})
        if task['fingerprint']!=fingerprint: raise HTTPException(409,'idempotency_conflict')
        return task

    async def claim(self, identity):
        await self.device(identity)
        await self.db.authorized_devices.update_one({'_id':identity},{'$set':{'execution.last_seen':now()}})
        token=secrets.token_urlsafe(32)
        return await self.db.execution_tasks.find_one_and_update({
            'device_id':identity,'state':'queued','expires_at':{'$gt':now()}},
            {'$set':{'state':'claimed','claimed_at':now(),'claim_token':token}},
            sort=[('created_at',1)],return_document=ReturnDocument.AFTER)

    async def result(self, identity, task_id, body):
        await self.device(identity)
        if not isinstance(body,dict) or set(body)!={'claim_token','state','output'} or not isinstance(body['claim_token'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',body['claim_token']) or body['state'] not in ('succeeded','failed','uncertain') or not isinstance(body['output'],dict) or len(json.dumps(body['output']).encode())>2_000_000:
            raise HTTPException(400,'invalid_result')
        task = await self.db.execution_tasks.find_one_and_update({
            '_id':valid_identity(task_id),'device_id':identity,'state':'claimed',
            'claim_token':body['claim_token']}, {'$set':{
                'state':body['state'],'output':body['output'],'finished_at':now()}},
            return_document=ReturnDocument.AFTER)
        if task: return {'accepted':True}
        old=await self.db.execution_tasks.find_one({'_id':task_id,'device_id':identity})
        if old and old.get('claim_token')==body['claim_token'] and old.get('state')==body['state'] and old.get('output')==body['output']:
            return {'accepted':True,'duplicate':True}
        raise HTTPException(409,'task_not_claimed')

def router(database, owner_authorize):
    api=APIRouter(prefix='/execution')
    def hub():
        db=database()
        if db is None: raise HTTPException(503,'database_unavailable')
        return ExecutionHub(db)
    async def signed(request:Request):
        request.state.execution_device=await DeviceAccess(hub().db).verify(request)
    async def body(request,limit=20000):
        if len(await request.body())>limit: raise HTTPException(413,'payload_too_large')
        try: return await request.json()
        except ValueError: raise HTTPException(400,'invalid_json') from None
    @api.get('/devices',dependencies=[Depends(owner_authorize)])
    async def devices():
        return jsonable_encoder(await hub().db.authorized_devices.find(
            {'revoked':False,'license_id':None},{'public_key':0}).limit(200).to_list(200))
    @api.post('/tasks',dependencies=[Depends(owner_authorize)])
    async def submit(request:Request):
        return jsonable_encoder(await hub().submit(await body(request),request.headers.get('idempotency-key')))
    @api.get('/tasks/{identity}',dependencies=[Depends(owner_authorize)])
    async def status(identity:str):
        task=await hub().db.execution_tasks.find_one({'_id':valid_identity(identity)}, {'claim_token':0,'fingerprint':0})
        if not task: raise HTTPException(404,'task_not_found')
        # Claimed tasks with lost results remain uncertain, never returned to queue.
        if task['state']=='claimed' and task['expires_at'].replace(tzinfo=timezone.utc)<now():
            task['observed_state']='uncertain'
        return jsonable_encoder(task)
    @api.post('/agent/register',dependencies=[Depends(signed)])
    async def register(request:Request): return await hub().register(request.state.execution_device,await body(request))
    @api.post('/agent/claim',dependencies=[Depends(signed)])
    async def claim(request:Request): return jsonable_encoder(await hub().claim(request.state.execution_device))
    @api.post('/agent/tasks/{identity}/result',dependencies=[Depends(signed)])
    async def result(identity:str,request:Request):
        return await hub().result(request.state.execution_device,identity,await body(request,2_000_000))
    return api
