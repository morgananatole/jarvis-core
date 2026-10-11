import copy
import hashlib
import hmac
import os
import time
import unittest
from unittest.mock import AsyncMock,patch
from fastapi import HTTPException
from starlette.requests import Request
from pix_billing import MercadoPago,PixBilling,signature
import test_pix_billing as billing_tests

ORDER={'user_id':123,'id':'ORD01HRYFWNYRE1MR1E60MW3X0T2P','type':'online','total_amount':'29.90',
 'external_reference':'reference','country_code':'BRA','status':'action_required','status_detail':'waiting_transfer',
 'transactions':{'payments':[{'id':'PAY01HRYFXQ53Q3JPEC48MYWMR0TE','amount':'29.90',
 'status':'action_required','status_detail':'waiting_transfer','payment_method':{'id':'pix','type':'bank_transfer',
 'qr_code':'pix-test-not-payable','qr_code_base64':''}}]}}
ACCOUNT={'id':123,'site_id':'MLB','tags':['test_user']}

class OrdersTests(unittest.IsolatedAsyncioTestCase):
    setUp=billing_tests.Tests.setUp
    license=billing_tests.Tests.license
    async def test_orders_pending_credit_and_duplicate_confirmation(self):
        lic=await self.license(True);provider=MercadoPago();raw=copy.deepcopy(ORDER)
        async def call(method,path,body=None,key=None):
            if path=='/users/me':return copy.deepcopy(ACCOUNT)
            if method=='POST':raw['external_reference']=key
            return copy.deepcopy(raw)
        provider.call=call;service=PixBilling(self.db,provider)
        order=await service.checkout(lic['license_id'],self.payer)
        self.assertEqual(order['qr_code'],'pix-test-not-payable')
        self.assertEqual((await service.reconcile(order['_id']))['status'],'pending')
        raw.update(status='processed',status_detail='accredited',total_paid_amount='29.90')
        raw['transactions']['payments'][0].update(status='processed',status_detail='accredited',paid_amount='29.90')
        self.assertEqual((await service.reconcile(order['_id']))['status'],'granted')
        until=self.db.commercial_licenses.docs[lic['license_id']]['expires_at']
        await service.reconcile(order['_id'])
        self.assertEqual(self.db.commercial_licenses.docs[lic['license_id']]['expires_at'],until)
        raw['total_paid_amount']='0.01'
        with self.assertRaises(HTTPException):await service.reconcile(order['_id'])
    async def test_orders_schema_and_receiver_pin(self):
        provider=MercadoPago();provider.call=AsyncMock(side_effect=[ACCOUNT,copy.deepcopy(ORDER)])
        await provider.create({'transaction_amount':29.90,'external_reference':'reference','payer':self.payer},'stable-key')
        call=provider.call.call_args
        self.assertEqual(call.args[:2],('POST','/v1/orders'))
        payload=call.args[2]
        self.assertEqual(payload['total_amount'],'29.90')
        self.assertEqual(payload['transactions']['payments'][0]['expiration_time'],'PT1H')
        self.assertNotIn('notification_url',payload)
        provider.call=AsyncMock(return_value={**ACCOUNT,'id':999})
        with self.assertRaises(HTTPException):await provider.create({'transaction_amount':1,'payer':self.payer},'key')
        self.assertEqual(provider.call.await_count,1)
    async def test_async_order_refreshes_qr_without_unlocking(self):
        lic=await self.license(True);provider=MercadoPago();raw=copy.deepcopy(ORDER)
        async def call(method,path,body=None,key=None):
            if path=='/users/me':return ACCOUNT
            if method=='POST':
                raw['external_reference']=key
                return {'id':raw['id'],'user_id':123,'status':'processing'}
            return raw
        provider.call=call;service=PixBilling(self.db,provider)
        order=await service.checkout(lic['license_id'],self.payer)
        self.assertEqual(order['qr_code'],'')
        refreshed=await service.reconcile(order['_id'])
        self.assertEqual(refreshed['qr_code'],'pix-test-not-payable')
        self.assertEqual(refreshed['status'],'pending')
        self.assertNotIn('billing_applied_orders',self.db.commercial_licenses.docs[lic['license_id']])
    async def test_order_signature_lowercases_identifier(self):
        identity=ORDER['id'];stamp=str(int(time.time()))
        digest=hmac.new(os.environ['MP_WEBHOOK_SECRET'].encode(),f'id:{identity.lower()};request-id:req1;ts:{stamp};'.encode(),hashlib.sha256).hexdigest()
        request=Request({'type':'http','method':'POST','path':'/','query_string':f'data.id={identity}'.encode(),
            'headers':[(b'x-request-id',b'req1'),(b'x-signature',f'ts={stamp},v1={digest}'.encode())]})
        self.assertEqual(signature(request),identity)
    async def test_owner_diagnostic_works_before_receiver_configuration(self):
        import httpx
        from fastapi import FastAPI
        from pix_billing import billing_router
        app=FastAPI();app.include_router(billing_router(lambda:self.db))
        with patch.dict(os.environ,{'MP_COLLECTOR_ID':'','BILLING_PUBLIC_BASE_URL':''}),patch.object(MercadoPago,'call',AsyncMock(return_value=ACCOUNT)):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://jarvis.test') as client:
                self.assertEqual((await client.get('/billing/connection')).status_code,401)
                response=await client.get('/billing/connection',headers={'Authorization':'Bearer '+os.environ['CRM_ADMIN_TOKEN']})
                self.assertEqual(response.status_code,200)
                data=response.json()
                self.assertEqual(data['receiver_id'],'123')
                self.assertEqual(data['missing'],['MP_COLLECTOR_ID','BILLING_PUBLIC_BASE_URL'])
                self.assertFalse(data['configured'])
                self.assertNotIn(os.environ['MP_ACCESS_TOKEN'],response.text)

    async def test_order_receiver_required_and_pinned(self):
        for receiver in (None,999,True,''):
            raw=copy.deepcopy(ORDER);raw['user_id']=receiver
            with self.assertRaises(HTTPException) as error:
                MercadoPago().normalize(raw,ACCOUNT,False)
            self.assertEqual(error.exception.detail,'payment_receiver_mismatch')
        raw=copy.deepcopy(ORDER);raw['user_id']='123'
        self.assertEqual(MercadoPago().normalize(raw,ACCOUNT,False)['collector_id'],123)

    async def test_sandbox_apro_opt_in_and_production_guard(self):
        body={'transaction_amount':50,'external_reference':'reference','payer':{'email':'test_user_br@testuser.com'}}
        provider=MercadoPago()
        with patch.dict(os.environ,{'BILLING_MP_SANDBOX_APRO':'true'}):
            provider.call=AsyncMock(side_effect=[ACCOUNT,copy.deepcopy(ORDER)])
            await provider.create(body,'key')
            self.assertEqual(provider.call.call_args.args[2]['payer']['first_name'],'APRO')
            provider.call=AsyncMock(return_value=ACCOUNT)
            with self.assertRaises(HTTPException):
                await provider.create({**body,'transaction_amount':1},'key')
            self.assertEqual(provider.call.await_count,1)
            with patch.dict(os.environ,{'BILLING_MP_LIVE_MODE':'true'}):
                provider.call=AsyncMock(return_value={**ACCOUNT,'tags':[]})
                with self.assertRaises(HTTPException) as error:await provider.create(body,'key')
                self.assertEqual(error.exception.detail,'sandbox_approval_requires_test_environment')
                self.assertEqual(provider.call.await_count,1)
        with patch.dict(os.environ,{'BILLING_MP_SANDBOX_APRO':'false'}):
            provider.call=AsyncMock(side_effect=[ACCOUNT,copy.deepcopy(ORDER)])
            await provider.create(body,'key')
            self.assertNotIn('first_name',provider.call.call_args.args[2]['payer'])

    async def test_diagnostic_rejects_environment_and_invalid_configuration(self):
        import httpx
        from fastapi import FastAPI
        from pix_billing import billing_router
        app=FastAPI();app.include_router(billing_router(lambda:self.db))
        with patch.object(MercadoPago,'call',AsyncMock(return_value=ACCOUNT)):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://jarvis.test') as client:
                for env,reason in (({'BILLING_MP_LIVE_MODE':'true'},'payment_environment_mismatch'),
                    ({'BILLING_MP_LIVE_MODE':'invalid'},'invalid_live_mode'),
                    ({'BILLING_PUBLIC_BASE_URL':'http://test.invalid'},'invalid_public_base_url')):
                    with patch.dict(os.environ,env):
                        data=(await client.get('/billing/connection',headers={'Authorization':'Bearer '+os.environ['CRM_ADMIN_TOKEN']})).json()
                        self.assertFalse(data['configured']);self.assertIn(reason,data['errors'])
                data=(await client.get('/billing/connection',headers={'Authorization':'Bearer '+os.environ['CRM_ADMIN_TOKEN']})).json()
                self.assertTrue(data['configured']);self.assertTrue(data['environment_matches'])
