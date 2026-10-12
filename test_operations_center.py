import os
import unittest
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import patch
from fastapi import FastAPI,HTTPException
import httpx
from test_business_intake import Collection
from setup_terms import SetupTerms,VERSION
from crm_admin import router
from outreach_overview import classify,interest
from knowledge_center import read_bundle
from import_google_contacts import import_phone
from installation_page import installation,launcher
class OperationsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'BUSINESS_ID':'one','CRM_ADMIN_TOKEN':'x'*32},clear=True);self.env.start();self.addCleanup(self.env.stop)
        self.db=SimpleNamespace(setup_terms=Collection());self.terms=SetupTerms(self.db)
    async def test_terms_default_refusal_revocation_and_actor_business_isolation(self):
        with self.assertRaises(HTTPException): await self.terms.require('owner')
        await self.terms.decide({'version':VERSION,'accepted':True},'owner');await self.terms.require('owner')
        self.assertFalse((await self.terms.status('device:test'))['accepted'])
        with patch.dict(os.environ,{'BUSINESS_ID':'two'}): self.assertFalse((await self.terms.status('owner'))['accepted'])
        result=await self.terms.decide({'version':VERSION,'accepted':False},'owner')
        self.assertFalse(result['accepted']);self.assertIsNotNone(result['decided_at'])
        with self.assertRaises(HTTPException): await self.terms.require('owner')
    async def test_terms_rejects_stale_and_injected_decisions(self):
        for body in [{'version':'old','accepted':True},{'version':VERSION,'accepted':1},{'version':VERSION,'accepted':True,'scope':'all_clients'}]:
            with self.assertRaises(HTTPException):await self.terms.decide(body,'owner')
        self.assertFalse(self.db.setup_terms.docs)
    async def test_http_setup_and_import_enforced_before_any_side_effect(self):
        app=FastAPI();app.include_router(router(lambda:self.db,lambda _:None))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='https://test') as c:
            headers={'Authorization':'Bearer '+'x'*32}
            for method,path in [('POST','/crm/business-setup/chat'),('PUT','/crm/business-setup/review'),('POST','/crm/import/google')]:
                r=await c.request(method,path,headers=headers,content=b'{}');self.assertEqual(r.status_code,403)
            r=await c.post('/crm/setup-terms',headers=headers,json={'version':VERSION,'accepted':True});self.assertEqual(r.status_code,200)
            self.assertEqual((await c.get('/crm/knowledge')).status_code,401)
            r=await c.get('/crm/knowledge',headers=headers);self.assertEqual(r.status_code,200)
            self.assertIn('CENTRAL_NORMAS.md',[d['path'] for d in r.json()['documents']])
    async def test_outreach_never_infers_opt_in_from_address_book_or_inbound(self):
        p={'phone':5581999999999,'facts':{'contact_name':{'value':'Synthetic'}},'last_inbound_at':datetime.now(timezone.utc)}
        self.assertEqual(classify(p,lambda _:True),'permission_required')
        p['facts']['contact_permission']={'value':'allowed'}
        self.assertEqual(classify(p,lambda _:True),'hybrid_ai_required')
        p['human_mode']=True;self.assertEqual(classify(p,lambda _:True),'human_takeover')
        p['do_not_contact']=True;self.assertEqual(classify(p,lambda _:True),'declined')
    async def test_country_is_explicit_and_ambiguous_numbers_not_guessed(self):
        with self.assertRaises(ValueError):import_phone('81999999999')
        self.assertEqual(import_phone('(81) 99999-9999','BR'),import_phone('+5581999999999'))
        for phone in ['999999999','00999999999','abc81999999999','999999999999999']:
            with self.assertRaises(ValueError):import_phone(phone,'BR')
    async def test_installation_has_no_keys_and_does_not_claim_meta_registration(self):
        self.assertIn('/painel',installation().body.decode());self.assertIn('Não é APK',installation().body.decode())
        self.assertIn('Abrir_JARVIS_PULSE.html',launcher().headers['content-disposition'])
        self.assertNotIn('CRM_ADMIN_TOKEN',launcher().body.decode())
        self.assertFalse(read_bundle()['semantic_comprehension_automatically_verified'])

    async def test_interest_is_grounded_and_never_grants_permission(self):
        p={'facts':{},'inbound_count':200}
        self.assertEqual(interest(p)['interest'],'unknown')
        p['signals']={'price':True};self.assertEqual(interest(p)['interest'],'exploring')
        p['signals']['decision']=True;self.assertEqual(interest(p)['interest'],'deciding')
        self.assertEqual(classify(p,lambda _:True),'permission_required')
        p['facts']['lifecycle']={'value':'postcare'};self.assertEqual(interest(p)['interest'],'customer')
        p['do_not_contact']=True;self.assertEqual(interest(p)['interest'],'not_interested')
