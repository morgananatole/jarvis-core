import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from fastapi import FastAPI, HTTPException
import httpx
from business_setup import BusinessSetup, apply_updates, converse
from business_profile import BusinessProfile, context, validate
from test_business_intake import Collection
from crm_admin import router


class SetupTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p=patch.dict(os.environ,{'BUSINESS_ID':'nova_vida','GROQ_API_KEY':'test',
                                'CRM_ADMIN_TOKEN':'x'*32},clear=True)
        p.start();self.addCleanup(p.stop)
        # Deliberately no contacts/inbox/customer_events collections.
        self.db=SimpleNamespace(business_setup_drafts=Collection(),business_profiles=Collection(),
                                business_profile_proposals=Collection())
        self.service=BusinessSetup(self.db)
        self.source='Somos Aurora, no segmento jardinagem. Oferecemos manutenção de jardins. Serviço poda: poda de árvores, R$ 100 por visita, pagamento na entrega.'
        self.answer={'reply':'Entendi a proposta da Aurora. Quem vocês querem atender?',
                     'suggestions':['Atendemos residências','Atendemos empresas'],'actions':[],
                     'updates':[{'field':k,'value':v,'evidence':self.source} for k,v in [
                         ('business_name','Aurora'),('segment','jardinagem'),('offer','manutenção de jardins'),
                         ('products.0.name','poda'),('products.0.description','poda de árvores'),
                         ('products.0.price','R$ 100 por visita'),('products.0.conditions','pagamento na entrega')]]}

    async def send(self,key='request_setup_12345678',revision=0):
        return await self.service.chat({'text':self.source,'revision':revision,'request_id':key},'owner')

    async def test_free_conversation_extracts_multiple_fields_and_saves_before_ai(self):
        async def provider(*args):
            saved=await BusinessSetup(self.db).public()
            self.assertEqual(saved['messages'][-1]['text'],self.source)
            self.assertEqual(saved['mode'],'thinking')
            self.assertEqual(args[0],'free')
            return json.dumps(self.answer),0
        with patch('business_setup.provider_call',side_effect=provider):
            result=await self.send()
        self.assertEqual(result['mode'],'ai');self.assertEqual(result['profile']['business_name'],'Aurora')
        self.assertEqual(result['profile']['products'][0]['price'],'R$ 100 por visita')
        self.assertEqual(await context(self.db),'')
        recovered=await BusinessSetup(self.db).public()
        self.assertEqual(recovered['messages'],result['messages'])

    async def test_duplicate_and_stale_requests_do_not_call_ai_again(self):
        with patch('business_setup.provider_call',AsyncMock(return_value=(json.dumps(self.answer),0))) as provider:
            first=await self.send();second=await self.send()
            self.assertEqual(first,second);self.assertEqual(provider.await_count,1)
            with self.assertRaises(HTTPException) as error: await self.send('other_request_1234567')
            self.assertEqual(error.exception.status_code,409);self.assertEqual(provider.await_count,1)

    async def test_invented_value_is_not_applied_and_original_can_be_retried(self):
        self.answer['updates'].append({'field':'products.0.price','value':'R$ 50','evidence':self.source})
        with patch('business_setup.provider_call',AsyncMock(return_value=(json.dumps(self.answer),0))):
            first=await self.send()
        self.assertEqual(first['mode'],'unavailable');self.assertEqual(first['profile'],{})
        self.answer['updates'].pop()
        with patch('business_setup.provider_call',AsyncMock(return_value=(json.dumps(self.answer),0))):
            recovered=await self.service.retry(first['revision'])
        self.assertEqual(recovered['profile']['segment'],'jardinagem')

    async def test_unavailable_preserves_conversation_without_fake_script_or_paid_calls(self):
        with patch('business_setup.provider_call',AsyncMock(side_effect=TimeoutError())):
            result=await self.send()
        self.assertEqual(result['mode'],'unavailable');self.assertEqual(result['profile'],{})
        self.assertIn('não alterei o cadastro',result['messages'][-1]['text'])
        self.assertEqual(result['suggestions'],[])

    async def test_draft_and_reviewed_catalog_are_scoped_and_snapshot_is_frozen(self):
        with patch('business_setup.provider_call',AsyncMock(return_value=(json.dumps(self.answer),0))):
            result=await self.send()
        proposal=await self.service.propose(result['revision'],'owner')
        changed={**result['profile'],'offer':'Oferta corrigida pelo responsável'}
        await self.service.save_review({'revision':result['revision'],'profile':changed},'owner')
        await BusinessProfile(self.db).approve(proposal['_id'])
        value=await context(self.db)
        self.assertIn('R$ 100 por visita',value);self.assertNotIn('Oferta corrigida',value)
        with patch.dict(os.environ,{'BUSINESS_ID':'other_business'}):
            self.assertEqual(await context(self.db),'')
            draft=await BusinessSetup(self.db).public()
            self.assertEqual(draft['profile'],{})
            self.assertNotIn('Aurora',json.dumps(draft,default=str))

    async def test_parallel_message_is_saved_once_and_cannot_clobber_inflight_draft(self):
        started=asyncio.Event();release=asyncio.Event()
        async def provider(*args):
            started.set();await release.wait();return json.dumps(self.answer),0
        with patch('business_setup.provider_call',side_effect=provider):
            task=asyncio.create_task(self.send());await started.wait()
            with self.assertRaises(HTTPException) as e: await self.send('parallel_request_12345',1)
            self.assertEqual(e.exception.detail,'setup_busy')
            release.set();await task
        self.assertEqual(len((await self.service.public())['messages']),3)

    async def test_dynamic_actions_are_validated_and_links_use_reviewed_number(self):
        self.answer['updates']=[];self.answer['actions']=['tasks','contact_call']
        with patch('business_setup.provider_call',AsyncMock(return_value=(json.dumps(self.answer),0))):
            result=await self.send()
        self.assertEqual(result['actions'][0]['area'],'tasks')
        self.assertEqual(result['actions'][1]['href'],'tel:+5581989927699')
        self.answer['actions']=['delete_all']
        with patch('business_setup.provider_call',AsyncMock(return_value=(json.dumps(self.answer),0))):
            result=await self.send('new_request_12345678',result['revision'])
        self.assertEqual(result['mode'],'unavailable');self.assertEqual(result['actions'],[])

    async def test_private_api_requires_authorization(self):
        app=FastAPI();app.include_router(router(lambda:self.db,lambda db:None))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            self.assertEqual((await client.get('/crm/business-setup')).status_code,401)
            self.assertEqual((await client.get('/crm/business-setup',headers={'Authorization':'Bearer '+'x'*32})).status_code,200)

    def test_forbidden_or_unsupported_facts_rejected_and_catalog_bounds(self):
        for field,value in [('human_mode','false'),('products.7.name','Aurora'),('segment','missing')]:
            with self.assertRaises(ValueError):apply_updates({},[{'field':field,'value':value,'evidence':self.source}],self.source)
        for products in ([{'name':'poda'}],[{'name':'poda','description':'x','price':99}],
                         [{'name':'poda','description':'x'}]*9):
            with self.assertRaises(HTTPException):validate({'segment':'jardim','offer':'poda','products':products})


if __name__=='__main__':unittest.main()
