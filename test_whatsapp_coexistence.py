import asyncio
import os
import re
import secrets
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from contact_memory import ContactMemory
from human_service import HumanService
from human_waiting import WaitingService, can_assist
from test_contact_memory import Database
from whatsapp_coexistence import text_echo, record_text_echo
import test_main
import main


class EchoTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'META_APP_SECRET': 'isolated-echo-test'})
        env.start(); self.addCleanup(env.stop)
        self.db = Database()
        self.metadata = {'display_phone_number': '15550783881'}

    def echo(self, identity='echo-one', stamp=None):
        return text_echo({'id': identity, 'from': '15550783881', 'to': '16505551234',
            'type': 'text', 'text': {'body': 'Synthetic operator message'},
            'timestamp': stamp or time.time()}, self.metadata)

    async def test_outbound_attribution_pauses_automation_without_inbound_permission(self):
        echo = self.echo()
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        await self.db.conversation_tasks.insert_one({'_id': profile['_id'] + ':next', 'state': 'planned'})
        await record_text_echo(self.db, echo)
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        self.assertTrue(profile['human_mode'])
        self.assertNotIn('last_inbound_at', profile)
        event = self.db.contact_events.docs[echo['id']]
        self.assertEqual(event['direction'], 'outbound')
        self.assertEqual(event['source'], 'whatsapp_business_app')
        self.assertNotIn('delivery', event)
        self.assertTrue(event['app_sync_applied'])
        self.assertEqual(self.db.conversation_tasks.docs[profile['_id'] + ':next']['state'], 'held')

    async def test_repeated_and_concurrent_echo_has_one_event_and_one_takeover(self):
        echo = self.echo()
        await asyncio.gather(*(record_text_echo(self.db, echo) for _ in range(16)))
        self.assertEqual(len(self.db.contact_events.docs), 1)
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        self.assertEqual(profile['automation_epoch'], 1)

    async def test_failed_side_effect_retries_to_completion(self):
        echo = self.echo()
        with patch.object(self.db.human_requests, 'update_one', AsyncMock(side_effect=RuntimeError('temporary'))):
            with self.assertRaises(RuntimeError): await record_text_echo(self.db, echo)
        self.assertNotIn('app_sync_applied', self.db.contact_events.docs[echo['id']])
        await record_text_echo(self.db, echo)
        self.assertTrue(self.db.contact_events.docs[echo['id']]['app_sync_applied'])
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        self.assertEqual(self.db.human_requests.docs[profile['_id']]['state'], 'active')
        self.assertEqual(profile['automation_epoch'], 1)

    async def test_duplicate_id_with_changed_text_is_rejected(self):
        echo = self.echo()
        await record_text_echo(self.db, echo)
        with self.assertRaises(ValueError):
            await record_text_echo(self.db, echo | {'text': 'Changed content'})

    async def test_new_inbound_does_not_restart_ai_after_business_takeover(self):
        echo = self.echo()
        await record_text_echo(self.db, echo)
        await ContactMemory(self.db).record_inbound(echo['phone'], 'later-inbound', 'Hello', time.time())
        await HumanService(self.db, AsyncMock(), lambda phone: True).request(
            echo['phone'], 'later-inbound', 'human_conversation')
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        send, compose = AsyncMock(), AsyncMock(return_value='Synthetic waiting reply')
        worker = WaitingService(self.db, send, lambda phone: True,
            clock=lambda: datetime.now(timezone.utc) + timedelta(minutes=6), compose=compose)
        await worker.run_one(profile['_id'])
        send.assert_not_awaited(); compose.assert_not_awaited()
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        self.assertFalse(can_assist(profile, self.db.human_requests.docs[profile['_id']]))

    async def test_brazilian_recipient_alias_uses_same_contact_and_leaves_others_active(self):
        memory = ContactMemory(self.db)
        target = await memory.ensure('5584981584252')
        other = await memory.ensure('16505559999')
        await record_text_echo(self.db, self.echo() | {'phone': '558481584252'})
        self.assertTrue((await memory.ensure('5584981584252'))['human_mode'])
        self.assertFalse((await memory.ensure(other['phone'])).get('human_mode', False))
        self.assertEqual(self.db.contact_events.docs['echo-one']['contact_key'], target['_id'])
        self.assertEqual(len(self.db.contacts.docs), 2)

    async def test_delayed_echo_cannot_undo_owner_resume_or_newer_app_reply(self):
        echo = self.echo()
        await record_text_echo(self.db, echo)
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        # Mock collection does not support find_one by contact_no; update control directly.
        await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
            'human_mode': False, 'human_control_at': datetime.now(timezone.utc)}})
        await record_text_echo(self.db, echo)
        await record_text_echo(self.db, self.echo('delayed-two', time.time() - 5))
        self.assertFalse((await ContactMemory(self.db).ensure(echo['phone']))['human_mode'])
        self.assertEqual(len(self.db.contact_events.docs), 2)

    async def test_old_echo_archived_without_takeover(self):
        echo = self.echo(stamp=time.time() - 172800)
        await record_text_echo(self.db, echo)
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        self.assertFalse(profile.get('human_mode', False))
        self.assertEqual(len(self.db.contact_events.docs), 1)

    async def test_collision_never_overwrites_an_inbound_event(self):
        echo = self.echo()
        await self.db.contact_events.insert_one({'_id': echo['id'], 'direction': 'inbound', 'text': 'original'})
        with self.assertRaises(ValueError): await record_text_echo(self.db, echo)
        self.assertEqual(self.db.contact_events.docs[echo['id']]['text'], 'original')

    async def test_parser_rejects_wrong_sender_invalid_destination_text_and_time(self):
        body = {'id': 'sample', 'from': '15550783881', 'to': '16505551234', 'type': 'text',
            'text': {'body': 'Synthetic text'}, 'timestamp': time.time()}
        for change in ({'from': '15550000000'}, {'to': 'bad'}, {'text': {'body': ''}},
                       {'timestamp': 'NaN'}, {'timestamp': time.time() + 1000}, {'id': ''}):
            with self.assertRaises(ValueError): text_echo(body | change, self.metadata)
        self.assertIsNone(text_echo(body | {'type': 'image'}, self.metadata))


@unittest.skipUnless(os.getenv('PULSE_TEST_MONGO_URI'), 'isolated MongoDB not configured')
class MongoEchoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        uri = os.environ['PULSE_TEST_MONGO_URI']
        if not re.fullmatch(r'mongodb://127\.0\.0\.1:[0-9]{2,5}', uri):
            raise ValueError('Only an explicit loopback test server is allowed')
        env = patch.dict(os.environ, {'META_APP_SECRET': 'isolated-mongo-echo'})
        env.start(); self.addCleanup(env.stop)
        self.client = AsyncIOMotorClient(uri, tz_aware=True, serverSelectionTimeoutMS=3000)
        self.db = self.client['pulse_test_' + secrets.token_hex(12)]
        await self.client.admin.command('ping')
        await ContactMemory(self.db).initialize()

    async def asyncTearDown(self):
        await self.client.drop_database(self.db.name)
        self.client.close()

    async def test_concurrent_echo_resume_and_reconnect_are_durable(self):
        from motor.motor_asyncio import AsyncIOMotorClient
        echo = {'id': 'synthetic-mongo-echo', 'phone': '16505551234',
            'text': 'Synthetic message', 'sent_at': datetime.now(timezone.utc)}
        await asyncio.gather(*(record_text_echo(self.db, echo) for _ in range(32)))
        self.assertEqual(await self.db.contact_events.count_documents({}), 1)
        profile = await ContactMemory(self.db).ensure(echo['phone'])
        self.assertEqual(profile['automation_epoch'], 1)
        await HumanService(self.db, AsyncMock(), lambda phone: True).mode(profile['contact_no'], False)
        second = AsyncIOMotorClient(os.environ['PULSE_TEST_MONGO_URI'], tz_aware=True)
        try:
            await record_text_echo(second[self.db.name], echo)
            await record_text_echo(second[self.db.name], echo | {'id': 'late-echo', 'sent_at': echo['sent_at'] - timedelta(seconds=5)})
            profile = await ContactMemory(second[self.db.name]).ensure(echo['phone'])
            self.assertFalse(profile['human_mode'])
            self.assertEqual(profile['automation_epoch'], 2)
        finally:
            second.close()

    async def test_old_echo_keeps_timestamp_without_changing_control(self):
        sent = datetime.now(timezone.utc) - timedelta(days=2)
        await record_text_echo(self.db, {'id': 'old-echo', 'phone': '16505551234', 'text': 'Old synthetic message', 'sent_at': sent})
        row = await self.db.contact_events.find_one({'_id': 'old-echo'})
        self.assertLess(abs((row['created_at'] - sent).total_seconds()), .001)
        profile = await ContactMemory(self.db).ensure('16505551234')
        self.assertFalse(profile.get('human_mode', False))

    async def test_partial_failures_retry_once_without_reviving_terminal_tasks(self):
        # Real Mongo matches state filters and stores datetimes at millisecond precision.
        for boundary in ('human_requests', 'conversation_tasks', 'contact_events'):
            echo = {'id': 'failure-' + boundary, 'phone': '16505551234',
                'text': 'Synthetic retry', 'sent_at': datetime.now(timezone.utc)}
            profile = await ContactMemory(self.db).ensure(echo['phone'])
            before = profile.get('automation_epoch', 0)
            await self.db.conversation_tasks.update_one({'_id': profile['_id'] + ':next'},
                {'$set': {'state': 'suppressed'}}, upsert=True)
            collection = getattr(self.db, boundary)
            update = collection.update_one
            async def fail(query, change, **kwargs):
                if boundary != 'contact_events' or change.get('$set', {}).get('app_sync_applied'):
                    raise RuntimeError('synthetic interruption')
                return await update(query, change, **kwargs)
            with patch.object(self.db, boundary, collection), patch.object(collection, 'update_one', side_effect=fail):
                with self.assertRaises(RuntimeError): await record_text_echo(self.db, echo)
            await record_text_echo(self.db, echo)
            await record_text_echo(self.db, echo)
            profile = await ContactMemory(self.db).ensure(echo['phone'])
            self.assertEqual(profile['automation_epoch'], before + 1)
            self.assertTrue((await self.db.contact_events.find_one({'_id': echo['id']}))['app_sync_applied'])
            self.assertEqual((await self.db.conversation_tasks.find_one({'_id': profile['_id'] + ':next'}))['state'], 'suppressed')

    async def test_business_pause_blocks_waiting_worker_until_explicit_resume(self):
        echo = {'id': 'pause-echo', 'phone': '16505551234',
            'text': 'Synthetic human message', 'sent_at': datetime.now(timezone.utc)}
        await record_text_echo(self.db, echo)
        memory = ContactMemory(self.db)
        await memory.record_inbound(echo['phone'], 'new-inbound', 'Hello', time.time())
        human = HumanService(self.db, AsyncMock(), lambda phone: True)
        await human.request(echo['phone'], 'new-inbound', 'human_conversation')
        profile = await memory.ensure(echo['phone'])
        compose, send = AsyncMock(), AsyncMock()
        worker = WaitingService(self.db, send, lambda phone: True,
            clock=lambda: datetime.now(timezone.utc) + timedelta(minutes=6), compose=compose)
        self.assertEqual((await worker.run_one(profile['_id']))['state'], 'human_takeover')
        send.assert_not_awaited(); compose.assert_not_awaited()
        await human.mode(profile['contact_no'], False)
        profile = await memory.ensure(echo['phone'])
        self.assertFalse(profile['human_mode'])
        self.assertEqual(profile['human_takeover_source'], 'panel')
        await record_text_echo(self.db, echo | {'id': 'delayed', 'sent_at': echo['sent_at'] - timedelta(seconds=1)})
        self.assertFalse((await memory.ensure(echo['phone']))['human_mode'])


class EchoWebhookTests(unittest.TestCase):
    def setUp(self): test_main.WebhookTests.setUp(self)
    def tearDown(self): test_main.WebhookTests.tearDown(self)
    def post(self, payload, valid=True): return test_main.WebhookTests.post(self, payload, valid)

    def payload(self, phone='test-value'):
        return {'entry': [{'changes': [{'field': 'smb_message_echoes', 'value': {
            'metadata': {'phone_number_id': phone, 'display_phone_number': '15550783881'},
            'message_echoes': [{'id': 'echo-webhook', 'from': '15550783881', 'to': '16505551234',
                'timestamp': time.time(), 'type': 'text', 'text': {'body': 'Synthetic app message'}}]}}]}]}

    def test_flag_off_and_wrong_number_have_no_effect(self):
        self.assertEqual(self.post(self.payload()).status_code, 200)
        with patch.dict(os.environ, {'WHATSAPP_APP_ECHO_SYNC': 'true'}):
            self.assertEqual(self.post(self.payload('other')).status_code, 200)
        self.assertEqual(self.inbox.database.contact_events.docs, {})
        self.generate.assert_not_called(); self.deliver.assert_not_called()

    def test_signed_text_echo_is_stored_but_never_replied_to(self):
        with patch.dict(os.environ, {'WHATSAPP_APP_ECHO_SYNC': 'true'}):
            for _ in range(2): self.assertEqual(self.post(self.payload()).status_code, 200)
            self.assertEqual(self.post(self.payload(), False).status_code, 403)
        self.assertEqual(len(self.inbox.database.contact_events.docs), 1)
        self.generate.assert_not_called(); self.deliver.assert_not_called()

    def test_bad_batch_is_rejected_before_any_storage(self):
        payload = self.payload()
        payload['entry'][0]['changes'][0]['value']['message_echoes'].append({'type': 'text'})
        with patch.dict(os.environ, {'WHATSAPP_APP_ECHO_SYNC': 'true'}):
            self.assertEqual(self.post(payload).status_code, 400)
        self.assertEqual(self.inbox.database.contact_events.docs, {})

    def test_other_fields_cannot_trigger_inbound_ai(self):
        payload = test_main.WebhookTests.payload(self)
        for field in ('history', 'smb_app_state_sync'):
            payload['entry'][0]['changes'][0]['field'] = field
            with patch.dict(os.environ, {'WHATSAPP_APP_ECHO_SYNC': 'true'}):
                self.assertEqual(self.post(payload).status_code, 200)
        self.generate.assert_not_called(); self.deliver.assert_not_called()

    def test_invalid_signature_cannot_create_contact_or_event(self):
        with patch.dict(os.environ, {'WHATSAPP_APP_ECHO_SYNC': 'true'}):
            self.assertEqual(self.post(self.payload(), False).status_code, 403)
        self.assertEqual(self.inbox.database.contacts.docs, {})
        self.assertEqual(self.inbox.database.contact_events.docs, {})
        self.generate.assert_not_called(); self.deliver.assert_not_called()

    def test_inbound_after_echo_is_held_including_direct_contact_request(self):
        with patch.dict(os.environ, {'WHATSAPP_APP_ECHO_SYNC': 'true'}):
            self.assertEqual(self.post(self.payload()).status_code, 200)
        for index, text in enumerate(('Hello', 'qual o telefone?')):
            payload = test_main.WebhookTests.payload(self)
            message = payload['entry'][0]['changes'][0]['value']['messages'][0]
            message.update({'from': '16505551234', 'id': 'held-' + str(index), 'text': {'body': text}})
            self.assertEqual(self.post(payload).status_code, 200)
            self.assertEqual(self.inbox.jobs[message['id']]['state'], 'human_waiting')
        self.generate.assert_not_called(); self.deliver.assert_not_called()

    def test_unsupported_echo_types_are_ignored_without_side_effects(self):
        for kind in ('image', 'audio', 'edit', 'revoke', 'contacts'):
            payload = self.payload()
            payload['entry'][0]['changes'][0]['value']['message_echoes'][0]['type'] = kind
            with patch.dict(os.environ, {'WHATSAPP_APP_ECHO_SYNC': 'true'}):
                self.assertEqual(self.post(payload).status_code, 200)
        self.assertEqual(self.inbox.database.contacts.docs, {})
        self.generate.assert_not_called(); self.deliver.assert_not_called()
