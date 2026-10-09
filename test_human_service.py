import asyncio
import copy
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace
from pymongo.errors import DuplicateKeyError
from human_service import HumanService, takeover_reason, active_window, conversation_lock
from contact_memory import ContactMemory, contact_key
from test_contact_memory import Collection, set_field


class Store(Collection):
    async def find_one(self, query):
        if '_id' in query and isinstance(query['_id'], str): return await super().find_one(query)
        for row in self.docs.values():
            if all(row.get(k) == v for k, v in query.items()): return copy.deepcopy(row)
        return None


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p=patch.dict(os.environ, {'META_APP_SECRET':'fake', 'JARVIS_REPLY_MODE':'hybrid',
            'AI_ALLOWED_TEST_ONLY':'false'}, clear=True)
        p.start();self.addCleanup(p.stop)
        self.db=SimpleNamespace(**{name:Store() for name in ['contacts','contact_events','conversation_tasks',
            'crm_counters','human_requests','operator_jobs','delivery_receipts']})
        self.phone='5584981584252'
        self.now=datetime.now(timezone.utc)
        self.send=AsyncMock(return_value='out1')
        self.service=HumanService(self.db,self.send,lambda _:True)

    async def profile(self):
        p=await ContactMemory(self.db).ensure(self.phone)
        await self.db.contacts.update_one({'_id':p['_id']},{'$set':{'last_inbound_at':self.now}})
        return await ContactMemory(self.db).ensure(self.phone)

    def test_customer_request_urgent_and_negation(self):
        self.assertEqual(takeover_reason('Preciso de resgate urgente'), 'urgent')
        self.assertEqual(takeover_reason('Quero falar com Morgan'), 'customer_request')
        self.assertIsNone(takeover_reason('não é urgente, qual o valor?'))
        self.assertIsNone(takeover_reason('Não quero falar com atendente'))

    async def test_queue_ack_once_and_pause_survives_new_service(self):
        await self.profile()
        self.assertTrue(await self.service.request(self.phone,'in1','urgent'))
        other=HumanService(self.db,self.send,lambda _:True)
        self.assertFalse(await other.request(self.phone,'in2','human_conversation'))
        p=await ContactMemory(self.db).ensure(self.phone)
        self.assertTrue(p['human_mode'])
        self.assertEqual(len(self.db.human_requests.docs),1)
        await other.mode(p['contact_no'],False)
        self.assertFalse((await ContactMemory(self.db).ensure(self.phone))['human_mode'])
        self.assertEqual(next(iter(self.db.human_requests.docs.values()))['state'],'resolved')

    async def test_operator_double_click_and_unknown_acceptance_never_resend(self):
        p=await self.profile();await self.service.mode(p['contact_no'],True)
        nonce='nonce-12345678901234567890'
        a=await self.service.reply(p['contact_no'],'Olá, sou Morgan.',nonce)
        b=await self.service.reply(p['contact_no'],'Olá, sou Morgan.',nonce)
        self.assertEqual(a['state'],'accepted');self.assertTrue(b['duplicate'])
        self.assertEqual(self.send.await_count,1)
        self.send.side_effect=TimeoutError('uncertain')
        nonce2='nonce-abcdefgh123456789012'
        self.assertEqual((await self.service.reply(p['contact_no'],'teste',nonce2))['state'],'review_required')
        self.assertTrue((await self.service.reply(p['contact_no'],'teste',nonce2))['duplicate'])
        self.assertEqual(self.send.await_count,2)

    async def test_manual_reply_needs_takeover_and_customer_window(self):
        p=await self.profile()
        with self.assertRaisesRegex(ValueError,'take_over_first'):
            await self.service.reply(p['contact_no'],'Olá','nonce-12345678901234567890')
        await self.service.mode(p['contact_no'],True)
        await self.db.contacts.update_one({'_id':p['_id']},{'$set':{'last_inbound_at':self.now-timedelta(days=2)}})
        with self.assertRaisesRegex(ValueError,'approved_template_required'):
            await self.service.reply(p['contact_no'],'Olá','nonce-12345678901234567890')
        self.send.assert_not_awaited()

    async def test_takeover_waits_for_current_contact_operation(self):
        p=await self.profile()
        async with conversation_lock(p['_id']):
            action=asyncio.create_task(self.service.mode(p['contact_no'],True))
            await asyncio.sleep(0)
            self.assertFalse(action.done())
        await action
        self.assertTrue((await ContactMemory(self.db).ensure(self.phone))['human_mode'])

    async def test_webhook_urgent_queue_has_one_ack_and_no_ai_calls(self):
        import main
        inbox=Store();inbox.database=self.db
        with patch.object(main,'inbox',inbox), patch.object(main,'send_reply',self.send), patch.object(main,'generate_reply',AsyncMock()) as ai:
            for i,text in enumerate(['Preciso de resgate urgente','Quero explicar a situação','Você está aí?']):
                await main.process_message({'id':'in'+str(i),'from':self.phone,
                    'timestamp':str(self.now.timestamp()),'text':{'body':text}})
            self.send.assert_awaited_once()
            ai.assert_not_awaited()
            self.assertEqual(inbox.docs['in2']['state'],'human_waiting')
            self.assertEqual(len([x for x in self.db.contact_events.docs.values() if x['direction']=='inbound']),3)

    async def test_public_customer_can_receive_reply_without_being_test_sender(self):
        import main
        inbox=Store();inbox.database=self.db
        other_phone='5511988887777'
        with patch.object(main,'inbox',inbox), patch.object(main,'send_reply',self.send), patch.object(main,'generate_reply',AsyncMock(return_value='Como posso ajudar?')) as ai:
            await main.process_message({'id':'public1','from':other_phone,
                'timestamp':str(self.now.timestamp()),'text':{'body':'Olá, como funciona?'}})
            self.send.assert_awaited_once_with(other_phone,'Como posso ajudar?')
            ai.assert_awaited_once()
            self.assertEqual(inbox.docs['public1']['state'],'sent')

    async def test_human_history_is_available_when_jarvis_resumes(self):
        p=await self.profile();await self.service.mode(p['contact_no'],True)
        memory=ContactMemory(self.db)
        await memory.record_inbound(self.phone,'in1','Posso retornar amanhã?',self.now.timestamp())
        await self.service.reply(p['contact_no'],'Sim, retomaremos amanhã.','nonce-12345678901234567890')
        await self.service.mode(p['contact_no'],False)
        turns=await memory.recent_turns(self.phone,'in2')
        self.assertEqual(turns[-1]['content'],'Sim, retomaremos amanhã.')
        self.assertEqual(turns[-2]['role'],'user')

if __name__=='__main__':unittest.main()
