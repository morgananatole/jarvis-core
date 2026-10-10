import asyncio
import copy
import json
import httpx
from fastapi import FastAPI
from crm_admin import router
import os
import secrets
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch
from fastapi import HTTPException
import test_device_access as dev
from commercial_licenses import Licenses

class Collection(dev.Collection):
    def matches(self, doc, query):
        for key, value in query.items():
            if key == '$expr':
                if not len(doc['devices']) < doc['max_devices']: return False
            elif not super().matches(doc, {key:value}): return False
        return True
    async def update_one(self, query, update, **kwargs):
        doc = next((d for d in self.docs.values() if self.matches(d, query)), None)
        if doc is None: return SimpleNamespace(matched_count=0)
        doc.update(copy.deepcopy(update.get('$set', {})))
        for key, value in update.get('$push', {}).items(): doc.setdefault(key, []).append(value)
        for key, value in update.get('$pull', {}).items(): doc[key] = [x for x in doc[key] if x != value]
        return SimpleNamespace(matched_count=1)
    async def find_one_and_update(self, query, update, **kwargs):
        doc = await self.find_one(query)
        if not doc: return None
        await self.update_one(query, update)
        return await self.find_one({'_id':doc['_id']})

class Tests(dev.Tests):
    def setUp(self):
        super().setUp()
        self.db.commercial_licenses = Collection()
        self.licenses = Licenses(self.db)
        p=patch.dict(os.environ, {'BUSINESS_ID':'nova_vida'});p.start();self.addCleanup(p.stop)
    def request(self, identity, *args, **kwargs):
        kwargs.setdefault('nonce', secrets.token_urlsafe(24))
        return super().request(identity, *args, **kwargs)
    async def license(self, kind='subscription', seats=1):
        return await self.licenses.issue({'label':'Venda especial','kind':kind,'max_devices':seats,
            'expires_at':(datetime.now(timezone.utc)+timedelta(days=30)).isoformat()})
    async def enroll_license(self, lic):
        code=(await self.service.issue('Cliente',lic['license_id']))['code']
        return (await self.service.enroll(code,self.jwk,lic['activation_key']))['device_id']
    async def test_expiry_blocks_signed_request_and_confirmed_payment_renews(self):
        lic=await self.license();identity=await self.enroll_license(lic)
        await self.service.verify(self.request(identity))
        row=self.db.commercial_licenses.docs[lic['license_id']]
        row['expires_at']=datetime.now(timezone.utc)-timedelta(seconds=1)
        with self.assertRaises(HTTPException) as e: await self.service.verify(self.request(identity))
        self.assertEqual(e.exception.detail,'license_expired')
        await self.licenses.renew(lic['license_id'], {'expires_at':lic['expires_at'].isoformat(),'payment_reference':'pagamento-123'})
        await self.service.verify(self.request(identity))
        self.assertEqual(row['renewals'][0]['payment_reference'],'pagamento-123')
    async def test_permanent_revocation_and_tenant_binding(self):
        lic=await self.license('permanent');identity=await self.enroll_license(lic)
        self.assertIsNone(lic['expires_at']);await self.service.verify(self.request(identity))
        with patch.dict(os.environ, {'BUSINESS_ID':'outra_empresa'}):
            with self.assertRaises(HTTPException): await self.service.verify(self.request(identity))
        self.db.commercial_licenses.docs[lic['license_id']]['revoked']=True
        with self.assertRaises(HTTPException): await self.service.verify(self.request(identity))
    async def test_secret_not_stored_and_simultaneous_seat_limit(self):
        lic=await self.license()
        self.assertNotIn(lic['activation_key'],str(self.db.commercial_licenses.docs))
        results=await asyncio.gather(*[self.enroll_license(lic) for _ in range(2)],return_exceptions=True)
        self.assertEqual(sum(isinstance(x,str) for x in results),1)
        self.assertEqual(len(self.db.commercial_licenses.docs[lic['license_id']]['devices']),1)
        identity=next(x for x in results if isinstance(x,str))
        await self.licenses.release(lic['license_id'],identity)
        with self.assertRaises(HTTPException): await self.service.verify(self.request(identity))
        await self.enroll_license(lic)
    async def test_wrong_key_missing_payment_and_invalid_expiration(self):
        lic=await self.license();code=(await self.service.issue('Cliente',lic['license_id']))['code']
        with self.assertRaises(HTTPException): await self.service.enroll(code,self.jwk,'errada')
        self.assertEqual(self.db.commercial_licenses.docs[lic['license_id']]['devices'],[])
        for body in ({'expires_at':'2027-01-01'},{'expires_at':lic['expires_at'].isoformat()}):
            with self.assertRaises(HTTPException):await self.licenses.renew(lic['license_id'],body)

    async def test_explicit_30_day_start_requires_no_date(self):
        before = datetime.now(timezone.utc)
        lic = await self.licenses.issue({'label': 'Novo assinante', 'kind': 'subscription',
                                         'max_devices': 1, 'trial_days': 30})
        after = datetime.now(timezone.utc)
        self.assertEqual(lic['trial_days'], 30)
        self.assertGreaterEqual(lic['expires_at'], before + timedelta(days=30))
        self.assertLessEqual(lic['expires_at'], after + timedelta(days=30))
        self.assertEqual(self.db.commercial_licenses.docs[lic['license_id']]['trial_days'], 30)

    async def test_trial_rejects_invalid_duration_or_conflicting_dates(self):
        original = len(self.db.commercial_licenses.docs)
        cases = [
            {'kind': 'subscription', 'trial_days': 7},
            {'kind': 'subscription', 'trial_days': True},
            {'kind': 'subscription', 'trial_days': 30, 'expires_at':
                (datetime.now(timezone.utc) + timedelta(days=40)).isoformat()},
            {'kind': 'permanent', 'trial_days': 30}
        ]
        for extra in cases:
            with self.assertRaises(HTTPException) as error:
                await self.licenses.issue({'label': 'Teste', 'max_devices': 1, **extra})
            self.assertEqual(error.exception.detail, 'invalid_30_day_trial')
        self.assertEqual(len(self.db.commercial_licenses.docs), original)

    async def test_trial_is_not_a_payment_authorization(self):
        lic = await self.licenses.issue({'label': 'Sem preco', 'kind': 'subscription',
                                         'max_devices': 1, 'trial_days': 30})
        data = self.db.commercial_licenses.docs[lic['license_id']]
        self.assertNotIn('billing_price', data)
        self.assertNotIn('auto_debit_authorization', data)
        self.assertNotIn('payment_id', data)

    async def test_customer_device_cannot_issue_or_renew_licenses(self):
        identity=await self.enrolled()
        app=FastAPI();app.include_router(router(lambda:self.db,lambda db:None))
        with patch.dict(os.environ, {'CRM_ADMIN_TOKEN':'owner-secret-for-test-'+'x'*32}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                for path in ('/crm/licenses','/crm/licenses/'+'a'*32+'/renew'):
                    body=json.dumps({'label':'Tentativa','kind':'permanent'}).encode()
                    req=self.request(identity,body=body,path=path)
                    result=await client.post(path,headers=dict(req.headers),content=body)
                    self.assertEqual(result.status_code,401)
        self.assertEqual(self.db.commercial_licenses.docs,{})
