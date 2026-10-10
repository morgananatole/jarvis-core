import asyncio
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException
from peripheral import Peripheral, inventory, proposals, DECISION
from test_business_intake import Collection
from business_intake import validate
import json
import httpx
from fastapi import FastAPI
from crm_admin import router

class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db=SimpleNamespace(peripheral_runs=Collection(),peripheral_decisions=Collection())
        self.service=Peripheral(self.db)
    async def test_simulation_is_idempotent_and_cannot_execute(self):
        await self.service.simulate({'media':'image','goal':'organize'},'abc')
        await self.service.simulate({'media':'image','goal':'organize'},'abc')
        self.assertEqual(len(self.db.peripheral_runs.docs),1)
        self.assertEqual(len(self.db.peripheral_decisions.docs),1)
        row=next(iter(self.db.peripheral_runs.docs.values()))
        self.assertFalse(row['executed']);self.assertEqual(row['planner'],'rules_v1')
        self.assertTrue(all(not p['executed'] for p in row['proposals']))
    async def test_inventory_and_observation_never_store_secrets_or_document(self):
        with patch.dict(os.environ, {'CRM_ADMIN_TOKEN':'DO-NOT-STORE-SECRET'}):
            self.assertNotIn('DO-NOT-STORE-SECRET',str(inventory()))
        await self.service.observe({'text':'private patient text','file':{'mime':'application/pdf','data':'private base64'}},'key')
        saved=str(self.db.peripheral_runs.docs)
        self.assertNotIn('private',saved);self.assertIn('ocr',saved)
        self.assertNotIn('key',saved)
    async def test_failure_does_not_block_primary_intake(self):
        with patch.object(self.service,'simulate',AsyncMock(side_effect=RuntimeError('DB offline'))):
            self.assertIsNone(await self.service.observe({'text':'a'},'key'))
    async def test_simulated_inputs_are_bounded_and_questions_are_untrusted_text(self):
        for signals in ({'code':'execute'}, {'goal':'execute'}, {'media':'secret'},[]):
            with self.assertRaises(HTTPException):proposals(signals)
        result=validate(json.dumps({'summary':'Ok','items':[],'questions':['Qual o nome?',{},'x'*300,'extra']}),'source')
        self.assertEqual(result['questions'],['Qual o nome?','x'*180])
        self.assertEqual(DECISION['execution_mode'],'simulation_only')

    async def test_peripheral_and_intake_start_concurrently(self):
        event=asyncio.Event()
        async def analyze(*args):
            await event.wait()
            return {'state':'preview'}
        async def observe(*args): event.set()
        app=FastAPI();app.include_router(router(lambda:self.db,lambda db:None))
        with patch.dict(os.environ,{'CRM_ADMIN_TOKEN':'x'*32}), patch('business_intake.BusinessIntake.analyze',side_effect=analyze), patch('peripheral.Peripheral.observe',side_effect=observe):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
                result=await asyncio.wait_for(client.post('/crm/intake',headers={'Authorization':'Bearer '+'x'*32,'Idempotency-Key':'test-entry-123456'},json={'text':'informação'}),timeout=1)
        self.assertEqual(result.status_code,200)
        self.assertTrue(event.is_set())
