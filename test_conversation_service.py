import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, AsyncMock
from starlette.requests import Request
from fastapi import HTTPException
from crm_admin import authorize
from conversation_service import gate, ConversationService, delivery_status
from media_service import image_payload
from contact_memory import unpack_reply


class QueryCollection:
    def __init__(self, doc):
        self.doc = doc
    def matches(self, query):
        for k, v in query.items():
            if isinstance(v, dict):
                if '$lte' in v and self.doc.get(k) > v['$lte']: return False
                if '$in' in v and self.doc.get(k) not in v['$in']: return False
            elif self.doc.get(k) != v: return False
        return True
    async def find_one(self, query):
        return dict(self.doc) if self.matches(query) else None
    async def find_one_and_update(self, query, update, **kw):
        if not self.matches(query): return None
        self.doc.update(update['$set'])
        return dict(self.doc)
    async def update_one(self, query, update, **kw):
        if self.matches(query): self.doc.update(update['$set'])


class Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.profile = {'_id': 'contact', 'phone': '5584981584252',
            'last_inbound_at': self.now - timedelta(hours=1),
            'facts': {'contact_permission': {'value': 'allowed'}}}
        p = patch.dict(os.environ, {'JARVIS_REPLY_MODE': 'hybrid', 'GROQ_API_KEY': 'fake',
            'AI_ALLOWED_TEST_ONLY': 'true'}, clear=True)
        p.start(); self.addCleanup(p.stop)

    def test_permission_and_window_and_test_scope(self):
        self.assertIsNone(gate(self.profile, self.now, lambda _: True))
        self.assertEqual(gate(self.profile, self.now, lambda _: False), 'test_recipient_only')
        self.profile['last_inbound_at'] -= timedelta(days=2)
        self.assertEqual(gate(self.profile, self.now, lambda _: True), 'approved_template_required')
        self.profile['do_not_contact'] = True
        self.assertEqual(gate(self.profile, self.now, lambda _: True), 'permission_required')

    def test_admin_api_is_closed_without_valid_bearer(self):
        for value, expected in [('', 503), ('a'*40, 401)]:
            with patch.dict(os.environ, {'CRM_ADMIN_TOKEN': value}):
                with self.assertRaises(HTTPException) as err:
                    authorize(Request({'type': 'http', 'headers': []}))
                self.assertEqual(err.exception.status_code, expected)
        with patch.dict(os.environ, {'CRM_ADMIN_TOKEN': 'a'*40}):
            authorize(Request({'type': 'http', 'headers': [(b'authorization', b'Bearer '+b'a'*40)]}))

    def test_unapproved_photos_and_raw_json_cannot_escape(self):
        for asset in [None, {'approved': False, 'media_id': '12345'}, {'approved': True, 'media_id': 'https://evil'}]:
            with self.assertRaises(ValueError): image_payload('55', asset)
        self.assertEqual(image_payload('55', {'approved': True, 'media_id': '12345'})['image']['id'], '12345')
        with self.assertRaises(ValueError): unpack_reply('{"facts":{}}', 'oi')

    async def test_approved_task_cannot_be_claimed_twice_or_auto_retried(self):
        db = type('DB', (), {})()
        db.contacts = QueryCollection(self.profile)
        db.conversation_tasks = QueryCollection({'_id': 'task', 'state': 'approved',
            'due_at': self.now - timedelta(seconds=1), 'contact_key': 'contact', 'purpose': 'retomar'})
        sent = []
        async def send(phone, text): sent.append(text); return 'out1'
        service = ConversationService(db, send, lambda _: True)
        # Opt-out must block before any AI/WhatsApp call.
        self.profile['do_not_contact'] = True
        self.assertEqual((await service.run_one('task'))['state'], 'blocked')
        self.assertEqual((await service.run_one('task'))['state'], 'not_claimed')
        self.assertEqual(sent, [])
        db.conversation_tasks.doc['state'] = 'review_required'
        self.assertEqual((await service.run_one('task'))['state'], 'not_claimed')

    async def test_success_and_uncertain_send_never_retry(self):
        for fail in (False, True):
            db = type('DB', (), {})()
            db.contacts = QueryCollection(self.profile)
            db.conversation_tasks = QueryCollection({'_id': 'task', 'state': 'approved',
                'due_at': self.now - timedelta(seconds=1), 'contact_key': 'contact',
                'source_message_id': 'in1', 'purpose': 'retomar'})
            sent = []
            async def send(phone, text):
                sent.append(text)
                if fail: raise TimeoutError('uncertain')
                return 'out1'
            with patch('conversation_service.ContactMemory') as memory, patch('conversation_service.ReplyRouter') as router:
                memory.return_value.context = AsyncMock(return_value='{"contact_name":"Maria"}')
                memory.return_value.record_outbound = AsyncMock()
                router.return_value.reply = AsyncMock(return_value='Olá Maria, podemos retomar?')
                service = ConversationService(db, send, lambda _: True)
                result = await service.run_one('task')
                self.assertEqual(result['state'], 'review_required' if fail else 'accepted')
                self.assertEqual((await service.run_one('task'))['state'], 'not_claimed')
                self.assertEqual(len(sent), 1)

    async def test_delivery_can_arrive_out_of_order_without_losing_read(self):
        db = type('DB', (), {})()
        db.contact_events = QueryCollection({'_id': 'out1'})
        db.conversation_tasks = QueryCollection({'outbound_id': 'out1'})
        for state in ['read', 'delivered', 'sent']:
            await delivery_status(db, {'id': 'out1', 'status': state, 'timestamp': str(self.now.timestamp())})
        self.assertIn('delivery_read_at', db.contact_events.doc)
        self.assertIn('delivery_delivered_at', db.contact_events.doc)

if __name__ == '__main__': unittest.main()
