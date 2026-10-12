import asyncio
import os
import unittest
from datetime import timedelta
from unittest.mock import AsyncMock, patch

import test_human_service as fixtures
from test_human_service import Store
from contact_memory import ContactMemory
from human_service import exclusive_human, conversation_lock
from human_waiting import WaitingService, can_assist


class WaitingTests(unittest.IsolatedAsyncioTestCase):
    setUp = fixtures.Tests.setUp
    profile = fixtures.Tests.profile
    async def waiting(self, reason='customer_request'):
        profile = await self.profile()
        await self.service.request(self.phone, 'first-request', reason)
        self.db.human_requests.docs[profile['_id']]['pending_since'] = self.now
        return profile['_id']

    def worker(self, minutes=5):
        return WaitingService(self.db, self.send, lambda _: True,
                              clock=lambda: self.now + timedelta(minutes=minutes))

    async def test_five_minutes_one_notice_and_assistance_survive_restart(self):
        key = await self.waiting()
        self.assertEqual((await self.worker(4.99).run_one(key))['state'], 'not_due')
        self.assertEqual((await self.worker().run_one(key))['state'], 'accepted')
        self.assertEqual((await self.worker(6).run_one(key))['state'], 'already_claimed')
        self.send.assert_awaited_once()
        profile = await ContactMemory(self.db).ensure(self.phone)
        self.assertTrue(profile['human_mode'])  # Queue is not silently closed.
        self.assertTrue(can_assist(profile, self.db.human_requests.docs[key]))
        self.assertEqual(self.db.human_requests.docs[key]['state'], 'waiting')
        text = self.send.call_args.args[1]
        self.assertTrue(text.startswith('Você já conseguiu receber o atendimento humano'))
        self.assertEqual(text.count('?'), 1)
        self.assertNotIn('tel:', text)
        self.assertNotIn('wa.me', text)
        self.assertNotIn('7699', text)
        self.assertNotIn('está em reunião', text)

    async def test_new_customer_messages_do_not_restart_timer(self):
        key = await self.waiting()
        await self.service.request(self.phone, 'second-request', 'human_conversation')
        self.assertEqual(self.db.human_requests.docs[key]['pending_since'], self.now)
        self.assertEqual(self.db.human_requests.docs[key]['wait_episode'], 'first-request')
        self.assertEqual((await self.worker().run_one(key))['state'], 'accepted')

    async def test_operator_reply_cancels_notice_and_assistance(self):
        key = await self.waiting()
        profile = await ContactMemory(self.db).ensure(self.phone)
        await self.service.reply(profile['contact_no'], 'Morgan respondeu.', 'nonce-12345678901234567890')
        self.assertEqual((await self.worker().run_one(key))['state'], 'not_due')
        self.send.assert_awaited_once()  # Only the human reply.
        self.assertFalse((await ContactMemory(self.db).ensure(self.phone))['ai_waiting_assist'])

    async def test_urgent_and_exclusive_only_get_fixed_wait_ack_not_ai(self):
        for reason, exclusive in [('urgent', False), ('customer_request', True)]:
            with self.subTest(reason=reason):
                self.setUp()
                key = await self.waiting(reason)
                self.db.contacts.docs[key]['human_only'] = exclusive
                result = await self.worker().run_one(key)
                self.assertFalse(result['assistance'])
                self.assertFalse(can_assist(self.db.contacts.docs[key], self.db.human_requests.docs[key]))

    async def test_optout_window_and_test_scope_block_without_send(self):
        key = await self.waiting()
        self.db.contacts.docs[key]['do_not_contact'] = True
        self.assertEqual((await self.worker().run_one(key))['state'], 'suppressed')
        self.db.contacts.docs[key]['do_not_contact'] = False
        self.db.contacts.docs[key]['last_inbound_at'] = self.now - timedelta(days=2)
        self.assertEqual((await self.worker().run_one(key))['state'], 'window_expired')
        self.db.contacts.docs[key]['last_inbound_at'] = self.now
        with patch.dict(os.environ, {'AI_ALLOWED_TEST_ONLY': 'true'}):
            service = WaitingService(self.db, self.send, lambda _: False,
                                     clock=lambda: self.now + timedelta(minutes=5))
            self.assertEqual((await service.run_one(key))['state'], 'test_recipient_only')
        self.send.assert_not_awaited()

    async def test_unknown_acceptance_and_old_uncertain_job_never_resend(self):
        key = await self.waiting()
        self.send.side_effect = TimeoutError('unknown')
        self.assertEqual((await self.worker().run_one(key))['state'], 'review_required')
        self.assertEqual((await self.worker().run_one(key))['state'], 'already_claimed')
        self.send.assert_awaited_once()
        self.assertFalse(self.db.contacts.docs[key].get('ai_waiting_assist', False))

    async def test_existing_uncertain_reply_not_followed_by_another_send(self):
        key = await self.waiting('reply_failed_or_uncertain')
        self.assertEqual((await self.worker().run_one(key))['state'], 'review_required')
        self.send.assert_not_awaited()

    async def test_contact_lock_allows_operator_to_cancel_before_worker(self):
        key = await self.waiting()
        profile = await ContactMemory(self.db).ensure(self.phone)
        async with conversation_lock(key):
            reply = asyncio.create_task(self.service.reply(profile['contact_no'], 'Já estou aqui.',
                                                           'nonce-12345678901234567890'))
            await asyncio.sleep(0)
            notice = asyncio.create_task(self.worker().run_one(key))
            await asyncio.sleep(0)
        await reply
        self.assertEqual((await notice)['state'], 'not_due')
        self.send.assert_awaited_once()

    async def test_next_customer_message_gets_commercial_ai_but_keeps_human_queue(self):
        import main
        key = await self.waiting()
        await self.worker().run_one(key)
        self.send.reset_mock()
        inbox = Store(); inbox.database = self.db
        with patch.object(main, 'inbox', inbox), patch.object(main, 'send_reply', self.send), \
                patch.object(main, 'generate_reply', AsyncMock(return_value='Programa de seis meses.')) as ai:
            await main.process_message({'id': 'new-question', 'from': self.phone,
                'timestamp': str(self.now.timestamp()), 'text': {'body': 'Qual a duração do tratamento?'}})
            ai.assert_awaited_once_with('Qual a duração do tratamento?', self.phone,
                                       'new-question', waiting_for_human=True)
            self.send.assert_awaited_once()
            self.assertTrue(self.db.contacts.docs[key]['human_mode'])
            self.assertEqual(self.db.human_requests.docs[key]['state'], 'waiting')

    async def test_legacy_waiting_queue_recovers_but_active_legacy_does_not(self):
        key = await self.waiting()
        queue = self.db.human_requests.docs[key]
        queue.pop('pending_since'); queue.pop('wait_episode')
        self.db.contacts.docs[key]['human_since'] = self.now
        queue['state'] = 'active'
        self.assertEqual((await self.worker().run_one(key))['state'], 'not_due')
        queue['state'] = 'waiting'
        self.assertEqual((await self.worker().run_one(key))['state'], 'accepted')

    async def test_takeover_cancels_support_and_starts_new_wait_episode(self):
        key = await self.waiting()
        await self.worker().run_one(key)
        profile = await ContactMemory(self.db).ensure(self.phone)
        await self.service.mode(profile['contact_no'], True)
        self.assertFalse(self.db.contacts.docs[key]['ai_waiting_assist'])
        self.assertNotEqual(self.db.human_requests.docs[key]['wait_episode'], 'first-request')

    async def test_explicit_panel_takeover_never_restarts_ai_after_wait(self):
        key = await self.waiting()
        profile = await ContactMemory(self.db).ensure(self.phone)
        await self.service.mode(profile['contact_no'], True)
        self.db.human_requests.docs[key]['pending_since'] = self.now
        compose = AsyncMock(return_value='Automação indevida')
        worker = WaitingService(self.db, self.send, lambda _: True,
            clock=lambda: self.now + timedelta(minutes=30), compose=compose)
        self.assertEqual((await worker.run_one(key))['state'], 'human_takeover')
        compose.assert_not_awaited()
        self.send.assert_not_awaited()
        self.assertFalse(self.db.contacts.docs[key]['ai_waiting_assist'])
        # Stale support flags cannot bypass an explicit operator takeover.
        self.db.contacts.docs[key]['ai_waiting_assist'] = True
        self.assertFalse(can_assist(self.db.contacts.docs[key], self.db.human_requests.docs[key]))

    async def test_panel_takeover_blocks_contact_menu_until_explicit_resume(self):
        import main
        key = await self.waiting()
        profile = await ContactMemory(self.db).ensure(self.phone)
        await self.service.mode(profile['contact_no'], True)
        inbox = Store(); inbox.database = self.db
        info = {'phone': '5581999991111', 'display': '+55 81 99999-1111'}
        with patch.object(main, 'inbox', inbox), patch.object(main, 'send_reply', self.send), \
                patch.object(main, 'generate_reply', AsyncMock(return_value='Resposta retomada')) as ai, \
                patch.object(main.contact_options, 'contact', AsyncMock(return_value=info)):
            for i, text in enumerate(['Qual o valor?', 'Me envie o telefone']):
                await main.process_message({'id': 'panel-in-' + str(i), 'from': self.phone,
                    'timestamp': str(self.now.timestamp()), 'text': {'body': text}})
                self.assertEqual(inbox.docs['panel-in-' + str(i)]['state'], 'human_waiting')
            ai.assert_not_awaited()
            self.send.assert_not_awaited()
            # Operator can still answer manually, and only explicit resume enables AI.
            await self.service.reply(profile['contact_no'], 'Já estou atendendo.',
                'nonce-panel-12345678901234')
            self.send.assert_awaited_once()
            self.send.reset_mock()
            await self.service.mode(profile['contact_no'], False)
            await main.process_message({'id': 'panel-resumed', 'from': self.phone,
                'timestamp': str(self.now.timestamp()), 'text': {'body': 'Qual o valor?'}})
            ai.assert_awaited_once()
            self.send.assert_awaited_once()

    async def test_new_request_after_resume_does_not_inherit_operator_control(self):
        key = await self.waiting()
        profile = await ContactMemory(self.db).ensure(self.phone)
        await self.service.mode(profile['contact_no'], True)
        await self.service.mode(profile['contact_no'], False)
        await self.service.request(self.phone, 'new-customer-request', 'customer_request')
        self.db.human_requests.docs[key]['pending_since'] = self.now
        self.assertEqual(self.db.contacts.docs[key]['human_takeover_source'], 'customer_request')
        self.assertEqual((await self.worker().run_one(key))['state'], 'accepted')
        self.send.assert_awaited_once()

    async def test_due_scan_excludes_already_notified_records(self):
        self.db.human_requests.find = unittest.mock.Mock()
        self.db.human_requests.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        await self.worker().run_due()
        query = self.db.human_requests.find.call_args.args[0]
        self.assertIn('accepted', query['wait_notice_state']['$nin'])
        self.assertIn('review_required', query['wait_notice_state']['$nin'])

    def test_explicit_human_preference_detected(self):
        self.assertTrue(exclusive_human('Quero somente humano'))
        self.assertTrue(exclusive_human('Não quero conversar com a IA'))
        self.assertFalse(exclusive_human('Quanto custa?'))


if __name__ == '__main__':
    unittest.main()
