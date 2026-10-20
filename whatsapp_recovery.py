"""One owner-authorized recovery target. No generic Graph proxy or credential output."""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
import httpx
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError
from pymongo.write_concern import WriteConcern

# Private target values stay in server configuration, never in the public repository.
POLICY_SHA256 = 'f77e0db5cab58b3e42250a1148b699033f7e163d3b5553546f7e89f8efed88c6'
try:
    POLICY = json.loads(os.getenv('WHATSAPP_RECOVERY_POLICY', '{}'))
except ValueError:
    POLICY = {}
TARGET_ID = POLICY.get('phone_number_id', '')
OWNER_PHONE = POLICY.get('owner_phone', '')
META_DISPLAY_PHONE = POLICY.get('meta_display_phone', '')
ACCOUNT = POLICY.get('account', '')
OPERATION = POLICY.get('operation', '')

def fail(code, status=409):
    raise HTTPException(status, code)

def digits(value):
    return re.sub(r'[^0-9]', '', str(value))

def name(value):
    return ' '.join(str(value or '').casefold().split())

def fingerprint(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

class Recovery:
    def __init__(self, database, client):
        # Majority acknowledged writes; never run Graph mutation if journal is unavailable.
        self.log = database.whatsapp_recovery_operations.with_options(write_concern=WriteConcern(w='majority',j=True,wtimeout=10000))
        self.client = client

    def config(self):
        if fingerprint(POLICY) != POLICY_SHA256:
            fail('private_recovery_policy_not_configured',503)
        if os.getenv('WHATSAPP_PHONE_NUMBER_ID') != TARGET_ID:
            fail('configured_phone_id_mismatch')
        token = os.getenv('WHATSAPP_ACCESS_TOKEN','')
        version = os.getenv('META_GRAPH_VERSION','')
        waba = os.getenv('WHATSAPP_WABA_ID','') or os.getenv('WHATSAPP_BUSINESS_ACCOUNT_ID','')
        if not token or not re.fullmatch(r'v[0-9]+\.[0-9]+',version) or not waba.isdigit():
            fail('recovery_server_configuration_incomplete',503)
        return 'https://graph.facebook.com/'+version, {'Authorization':'Bearer '+token}, waba

    async def read_graph(self, url, headers, fields):
        try:
            response = await self.client.get(url,headers=headers,params={'fields':fields})
            if response.status_code != 200: fail('identity_graph_read_failed',502)
            data = response.json()
            if not isinstance(data,dict):fail('identity_graph_invalid',502)
            return data
        except (httpx.HTTPError,ValueError):
            fail('identity_graph_unavailable',502)

    async def identity(self):
        base, headers, waba = self.config()
        phone = await self.read_graph(base+'/'+TARGET_ID,headers,'id,display_phone_number,verified_name,platform_type,is_on_biz_app')
        account = await self.read_graph(base+'/'+waba,headers,'id,name,phone_numbers.limit(100){id}')
        members = account.get('phone_numbers',{})
        numbers = members.get('data',[]) if isinstance(members,dict) else []
        observed = digits(phone.get('display_phone_number',''))
        if str(phone.get('id')) != TARGET_ID or str(account.get('id')) != waba:
            fail('remote_identity_id_mismatch')
        if name(account.get('name')) != name(ACCOUNT) or name(phone.get('verified_name')) != name(ACCOUNT):
            fail('remote_account_name_mismatch')
        if not any(str(p.get('id')) == TARGET_ID for p in numbers if isinstance(p,dict)):
            # No pagination guessing: missing membership blocks rather than selecting another number.
            fail('waba_membership_not_proven')
        if observed not in (OWNER_PHONE,META_DISPLAY_PHONE): fail('remote_phone_mismatch')
        result={'phone_number_id':TARGET_ID,'owner_phone':OWNER_PHONE,'observed_phone':observed,
                'waba_id':waba,'account_name':account['name'],'verified_name':phone['verified_name'],
                'phone_match':'exact' if observed==OWNER_PHONE else 'ninth_digit_difference_requires_explicit_ack',
                'platform':phone.get('platform_type'),'business_app_connected':phone.get('is_on_biz_app')}
        return {**result,'fingerprint':fingerprint(result)}

    async def status(self):
        doc=await self.log.find_one({'_id':OPERATION})
        if not doc:return {'operation':OPERATION,'state':'not_started'}
        # A persisted posting state after a worker stops is uncertain, never a retry permission.
        return {k:doc[k] for k in ['operation','state','intention_at','result_at','identity','graph_http','graph_success'] if k in doc}

    async def execute(self, body):
        if not isinstance(body,dict) or set(body)-{'identity_fingerprint','acknowledge_ninth_digit_difference','confirm_operation'}:
            fail('invalid_recovery_request',400)
        if body.get('confirm_operation') != OPERATION:fail('specific_confirmation_required',400)
        if await self.log.find_one({'_id':OPERATION}):
            return {'repeated':True,**await self.status()}
        identity=await self.identity()
        if body.get('identity_fingerprint') != identity['fingerprint']:fail('identity_changed_or_not_reviewed')
        if identity['phone_match'] != 'exact' and body.get('acknowledge_ninth_digit_difference') is not True:
            fail('ninth_digit_difference_not_accepted')
        if identity['platform']!='CLOUD_API' or identity['business_app_connected'] is not False:
            fail('remote_registration_not_eligible')
        now=lambda:datetime.now(timezone.utc).isoformat()
        intent={'_id':OPERATION,'operation':OPERATION,'state':'posting_uncertain_until_receipt',
                'identity':identity,'intention_at':now()}
        try:await self.log.insert_one(intent)
        except DuplicateKeyError:return {'repeated':True,**await self.status()}
        # No await/call to Graph occurs before the durable unique-target claim above.
        base,headers,_=self.config()
        result={'state':'uncertain','result_at':now()}
        try:
            response=await self.client.post(base+'/'+TARGET_ID+'/deregister',headers=headers,json={})
            result['graph_http']=response.status_code
            payload=response.json()
            success=isinstance(payload,dict) and payload.get('success') is True
            result['graph_success']=success
            result['state']='acknowledged_success' if response.status_code==200 and success else 'rejected_no_auto_retry' if 400<=response.status_code<500 else 'uncertain'
        except (httpx.HTTPError,ValueError):
            pass
        await self.log.update_one({'_id':OPERATION},{'$set':result})
        # Read-only verification is separate: an exception here cannot erase the receipt.
        return await self.status()

async def open_recovery(database, mode, body=None):
    async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
        service=Recovery(database,client)
        if mode=='identity':return await service.identity()
        if mode=='status':return await service.status()
        return await service.execute(body)
