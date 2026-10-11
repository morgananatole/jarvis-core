import json
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
import customer_care
from test_business_intake import Collection
from test_human_waiting import WaitingTests


class CareTests(unittest.IsolatedAsyncioTestCase):
    async def test_waiting_generation_sends_name_but_no_clinical_facts(self):
        db=SimpleNamespace(business_profiles=Collection())
        profile={'phone':'private-phone','facts':{'contact_name':{'value':'Ana'},
            'patient_name':{'value':'PRIVATE_PATIENT'},'substances':{'value':'PRIVATE_SUBSTANCE'}}}
        reply='Ana, você já conseguiu o atendimento de que precisava? Sou o JARVIS, assistente virtual, e continuo por aqui se ficou alguma dúvida.'
        with patch('ai_router.settings',return_value={'free_key':'fake'}), \
             patch('ai_router.provider_call',AsyncMock(return_value=(json.dumps({'reply':reply}),0))) as provider:
            self.assertEqual(await customer_care.waiting_message(db,profile),reply)
        payload=json.dumps(provider.call_args.args)
        self.assertIn('Ana',payload)
        for private in ('private-phone','PRIVATE_PATIENT','PRIVATE_SUBSTANCE'):self.assertNotIn(private,payload)

    async def test_waiting_generated_links_rejected(self):
        db=SimpleNamespace(business_profiles=Collection())
        with patch('ai_router.settings',return_value={'free_key':'fake'}), \
             patch('ai_router.provider_call',AsyncMock(return_value=(json.dumps({'reply':
                 'Você foi atendido? Sou assistente virtual. Abra https://wa.me/12345678'}),0))):
            self.assertIsNone(await customer_care.waiting_message(db,{}))

    def test_stages_respect_known_contact_and_human_queue(self):
        self.assertIn('primeiro atendimento',customer_care.stage({'inbound_count':1}))
        self.assertIn('sem reapresentação',customer_care.stage({'inbound_count':2}))
        self.assertIn('Não interromper',customer_care.stage({'inbound_count':4,'human_mode':True}))
        self.assertIn('pós-atendimento',customer_care.stage({'facts':{'lifecycle':{'value':'postcare'}}}))
        self.assertIn('não a IA que configura a empresa',customer_care.GUIDANCE)


class NaturalWait(WaitingTests):
    async def test_composed_message_or_provider_failure_preserves_one_notice(self):
        key=await self.waiting()
        worker=self.worker();worker.compose=AsyncMock(return_value='Ana, já foi atendida? Sou assistente virtual; sigo por aqui se precisar.')
        self.assertEqual((await worker.run_one(key))['state'],'accepted')
        self.assertTrue(self.send.call_args.args[1].startswith('Ana'))
        self.assertEqual((await worker.run_one(key))['state'],'already_claimed')
        worker.compose.assert_awaited_once()

    async def test_protected_wait_never_uses_conversational_composer(self):
        key=await self.waiting('urgent');worker=self.worker();worker.compose=AsyncMock()
        await worker.run_one(key);worker.compose.assert_not_awaited()

    async def test_failed_composer_uses_acknowledgement_without_losing_customer(self):
        key=await self.waiting();worker=self.worker();worker.compose=AsyncMock(side_effect=TimeoutError())
        self.assertEqual((await worker.run_one(key))['state'],'accepted')
        self.assertIn('Você já conseguiu receber',self.send.call_args.args[1])


def load_tests(loader,tests,pattern):
    suite=loader.loadTestsFromTestCase(CareTests)
    for name in ('test_composed_message_or_provider_failure_preserves_one_notice',
                 'test_protected_wait_never_uses_conversational_composer',
                 'test_failed_composer_uses_acknowledgement_without_losing_customer'):
        suite.addTest(NaturalWait(name))
    return suite
