import asyncio
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec,utils
import copy
import hashlib
import hmac
import json
import os
import time
import unittest
from datetime import datetime,timedelta,timezone
from types import SimpleNamespace
from unittest.mock import patch,AsyncMock
import httpx
from fastapi import FastAPI,HTTPException
from starlette.requests import Request
from pymongo.errors import DuplicateKeyError
from pix_billing import PixBilling,billing_router,signature,configured
from commercial_licenses import Licenses
from crm_admin import router
from test_contact_memory import Cursor
import test_device_access as dev

class Collection:
    def __init__(self):self.docs={}
    def match(self,d,q):
        for k,v in q.items():
            if k=='$or':
                if not any(self.match(d,x) for x in v):return False
                continue
            val=d.get(k)
            if isinstance(v,dict):
                for op,x in v.items():
                    if op=='$in' and val not in x:return False
                    if op=='$exists' and (k in d)!=x:return False
                    if op=='$lt' and (val is None or not val<x):return False
                    if op=='$gt' and (val is None or not val>x):return False
                    if op=='$ne' and (x in val if isinstance(val,list) else val==x):return False
            elif val!=v:return False
        return True
    async def find_one(self,q):return next((copy.deepcopy(d) for d in self.docs.values() if self.match(d,q)),None)
    def find(self,q):return Cursor([d for d in self.docs.values() if self.match(d,q)])
    async def insert_one(self,d):
        if d['_id'] in self.docs:raise DuplicateKeyError('duplicate')
        self.docs[d['_id']]=copy.deepcopy(d)
    async def update_one(self,q,u,upsert=False):
        d=next((d for d in self.docs.values() if self.match(d,q)),None)
        if d is None and upsert:
            d=self.docs.setdefault(q['_id'],{'_id':q['_id']});d.update(copy.deepcopy(u.get('$setOnInsert',{})))
        if d is None:return SimpleNamespace(matched_count=0)
        d.update(copy.deepcopy(u.get('$set',{})))
        for k,v in u.get('$addToSet',{}).items():
            if v not in d.setdefault(k,[]):d[k].append(v)
        return SimpleNamespace(matched_count=1)
    async def find_one_and_update(self,q,u,**kw):
        d=await self.find_one(q)
        if not d:return None
        await self.update_one(q,u)
        return await self.find_one({'_id':d['_id']})

class Provider:
    def __init__(self):self.calls=[];self.payments={};self.count=0
    async def create(self,body,key):
        self.calls.append(key)
        if key in self.payments:return copy.deepcopy(self.payments[key])
        self.count+=1
        data={'id':self.count,'status':'pending','external_reference':key,'transaction_amount':body['transaction_amount'],
            'currency_id':'BRL','payment_method_id':'pix','collector_id':123,'live_mode':False,
            'point_of_interaction':{'transaction_data':{'qr_code':'test-pix-not-payable','qr_code_base64':''}}}
        self.payments[key]=data
        return copy.deepcopy(data)
    async def get(self,identity):return copy.deepcopy(next(p for p in self.payments.values() if str(p['id'])==identity))

class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'BUSINESS_ID':'nova_vida','MP_ACCESS_TOKEN':'test-token','MP_WEBHOOK_SECRET':'test-signature-secret',
            'MP_COLLECTOR_ID':'123','BILLING_PUBLIC_BASE_URL':'https://jarvis.test','BILLING_MP_LIVE_MODE':'false','CRM_ADMIN_TOKEN':'x'*32});self.env.start();self.addCleanup(self.env.stop)
        self.db=SimpleNamespace(commercial_licenses=Collection(),billing_orders=Collection())
        self.provider=Provider();self.service=PixBilling(self.db,self.provider)
        self.payer={'email':'payer@example.test','cpf':'12345678909'}
    async def license(self,expired=False,kind='subscription'):
        data=await Licenses(self.db).issue({'label':'Assinatura de teste','kind':kind,'max_devices':1,
            'expires_at':(datetime.now(timezone.utc)+timedelta(days=3)).isoformat()})
        if kind=='subscription':await self.service.price(data['license_id'],{'amount_cents':2990,'period_days':30})
        if expired:self.db.commercial_licenses.docs[data['license_id']]['expires_at']=datetime.now(timezone.utc)-timedelta(days=2)
        return data
    async def checkout(self,expired=False):
        lic=await self.license(expired)
        order=await self.service.checkout(lic['license_id'],self.payer)
        return lic,order
    async def test_pending_never_unlocks_and_duplicate_approved_extends_once(self):
        lic,order=await self.checkout(True)
        await self.service.reconcile(order['_id'])
        with self.assertRaises(HTTPException):await Licenses(self.db).active(lic['license_id'])
        self.provider.payments[order['_id']]['status']='approved'
        results=await asyncio.gather(*[self.service.reconcile(order['_id']) for _ in range(3)])
        row=self.db.commercial_licenses.docs[lic['license_id']]
        self.assertEqual(len(row['billing_applied_orders']),1)
        self.assertTrue(datetime.now(timezone.utc)+timedelta(days=29)<row['expires_at']<datetime.now(timezone.utc)+timedelta(days=31))
        self.assertTrue(all(r['status']=='granted' for r in results))
        await Licenses(self.db).active(lic['license_id'])
    async def test_early_payment_preserves_existing_validity(self):
        lic,order=await self.checkout()
        before=self.db.commercial_licenses.docs[lic['license_id']]['expires_at']
        self.provider.payments[order['_id']]['status']='approved'
        await self.service.reconcile(order['_id'])
        self.assertEqual(self.db.commercial_licenses.docs[lic['license_id']]['expires_at'],before+timedelta(days=30))
    async def test_wrong_amount_reference_collector_currency_or_live_mode_never_grants(self):
        lic,order=await self.checkout()
        original=copy.deepcopy(self.provider.payments[order['_id']]);original['status']='approved'
        for field,value in [('transaction_amount',1),('external_reference','wrong'),('collector_id',999),('currency_id','USD'),('live_mode',True),('payment_method_id','credit_card')]:
            self.provider.payments[order['_id']]={**original,field:value}
            with self.assertRaises(HTTPException):await self.service.reconcile(order['_id'])
        self.assertNotIn('billing_applied_orders',self.db.commercial_licenses.docs[lic['license_id']])
    async def test_repeated_checkout_keeps_one_payment_and_no_payer_persistence(self):
        lic=await self.license()
        first=await self.service.checkout(lic['license_id'],self.payer)
        second=await self.service.checkout(lic['license_id'],self.payer)
        self.assertEqual(first['_id'],second['_id']);self.assertEqual(self.provider.count,1)
        self.assertNotIn(self.payer['cpf'],str(self.db.billing_orders.docs));self.assertNotIn(self.payer['email'],str(self.db.billing_orders.docs))
        with self.assertRaises(HTTPException):await self.service.checkout(lic['license_id'],{**self.payer,'amount_cents':1})
    async def test_timeout_retry_uses_same_provider_key(self):
        lic=await self.license()
        original=self.provider.create
        async def uncertain(body,key):
            await original(body,key)
            raise TimeoutError()
        self.provider.create=uncertain
        with self.assertRaises(HTTPException):await self.service.checkout(lic['license_id'],self.payer)
        self.provider.create=original
        order=await self.service.checkout(lic['license_id'],self.payer)
        self.assertEqual(self.provider.count,1);self.assertEqual(self.provider.calls[0],self.provider.calls[1])
        self.assertEqual(order['status'],'pending')
    async def test_revoked_and_permanent_do_not_get_reactivated_or_charged(self):
        lic,order=await self.checkout()
        self.provider.payments[order['_id']]['status']='approved'
        self.db.commercial_licenses.docs[lic['license_id']]['revoked']=True
        with self.assertRaises(HTTPException):await self.service.reconcile(order['_id'])
        permanent=await self.license(kind='permanent')
        with self.assertRaises(HTTPException):await self.service.checkout(permanent['license_id'],self.payer)
        self.assertEqual(self.provider.count,1)
    async def test_missing_provider_configuration_generates_no_fake_qr(self):
        lic=await self.license()
        with patch.dict(os.environ,{'MP_ACCESS_TOKEN':''}):
            self.assertFalse(configured())
            self.assertFalse((await self.service.account(lic['license_id']))['configured'])
            with self.assertRaises(HTTPException):await self.service.checkout(lic['license_id'],self.payer)
        self.assertEqual(self.provider.count,0)
    async def test_signature_and_stale_notifications(self):
        stamp=str(int(time.time()));request_id='request-123';payment='123'
        manifest=f'id:{payment};request-id:{request_id};ts:{stamp};'
        digest=hmac.new(b'test-signature-secret',manifest.encode(),hashlib.sha256).hexdigest()
        def req(header,query='data.id=123'):
            return Request({'type':'http','method':'POST','path':'/billing/webhook/mercadopago','query_string':query.encode(),
                'headers':[(b'x-request-id',request_id.encode()),(b'x-signature',header.encode())]})
        self.assertEqual(signature(req('ts='+stamp+',v1='+digest)),payment)
        for request in [req('ts='+stamp+',v1='+'0'*64),req('ts='+stamp+',v1='+digest,'data.id=999'),req('ts=1000000000,v1='+digest)]:
            with self.assertRaises(HTTPException):signature(request)
    async def test_expired_device_can_pay_but_cannot_read_crm(self):
        device=dev.Tests();device.setUp()
        self.db.device_codes=device.db.device_codes;self.db.device_nonces=device.db.device_nonces;self.db.authorized_devices=device.db.authorized_devices
        device.service.db=self.db
        lic=await self.license()
        # Enrollment already exists before expiration; reserve does not need the test's Mongo expression.
        identity=await device.enrolled();self.db.authorized_devices.docs[identity]['license_id']=lic['license_id']
        row=self.db.commercial_licenses.docs[lic['license_id']];row['devices']=[identity];row['expires_at']=datetime.now(timezone.utc)-timedelta(days=1)
        app=FastAPI();app.include_router(router(lambda:self.db,lambda db:None));app.include_router(billing_router(lambda:self.db))
        def signed_get(path,nonce):
            request=device.request(identity,path=path,nonce=nonce)
            headers=dict(request.headers);stamp=headers['x-jarvis-time']
            payload='\n'.join(['GET',path,stamp,nonce,hashlib.sha256(b'').hexdigest(),'']).encode()
            r,s=utils.decode_dss_signature(device.key.sign(payload,ec.ECDSA(hashes.SHA256())))
            headers['x-jarvis-signature']=base64.urlsafe_b64encode(r.to_bytes(32,'big')+s.to_bytes(32,'big')).decode().rstrip('=')
            return headers
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            for path,expected,nonce in [('/billing/account',200,'billing_access_nonce_123'),('/crm/contacts',403,'crm_denied_nonce_12345')]:
                result=await client.get(path,headers=signed_get(path,nonce))
                self.assertEqual(result.status_code,expected)
            self.db.authorized_devices.docs[identity]['revoked']=True
            result=await client.get('/billing/account',headers=signed_get('/billing/account','revoked_billing_nonce_123'))
            self.assertEqual(result.status_code,401)
    async def test_webhook_ignores_claimed_approval_and_reads_provider_status(self):
        lic,order=await self.checkout(True)
        payment=str(self.provider.payments[order['_id']]['id']);stamp=str(int(time.time()));request_id='webhook-123'
        manifest=f'id:{payment};request-id:{request_id};ts:{stamp};'
        digest=hmac.new(b'test-signature-secret',manifest.encode(),hashlib.sha256).hexdigest()
        app=FastAPI();app.include_router(billing_router(lambda:self.db))
        with patch('pix_billing.MercadoPago.get',side_effect=self.provider.get):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                result=await client.post('/billing/webhook/mercadopago?data.id='+payment,
                    headers={'x-request-id':request_id,'x-signature':'ts='+stamp+',v1='+digest},
                    json={'type':'payment','data':{'id':payment},'status':'approved'})
                self.assertEqual(result.status_code,200)
        self.assertNotIn('billing_applied_orders',self.db.commercial_licenses.docs[lic['license_id']])
    async def test_background_reconciliation_recovers_missed_webhook(self):
        lic,order=await self.checkout(True)
        self.provider.payments[order['_id']]['status']='approved'
        await self.service.recover()
        self.assertEqual(self.db.billing_orders.docs[order['_id']]['status'],'granted')
        await Licenses(self.db).active(lic['license_id'])
