"""Read-only WhatsApp diagnostics protect credentials and avoid destructive calls."""
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI

from crm_admin import router
from whatsapp_operations import mode_status, operations


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, field, direction):
        self.rows = sorted(self.rows, key=lambda r: r.get(field, 0), reverse=direction < 0)
        return self

    def limit(self, n):
        self.rows = self.rows[:n]
        return self

    async def to_list(self, n):
        return self.rows[:n]


class Collection:
    def __init__(self, rows):
        self.rows = rows
        self.projection = None

    def find(self, filt, projection):
        self.projection = projection
        return Cursor(self.rows)


class DB:
    def __init__(self, rows):
        self.inbox = Collection(rows)


class Tests(unittest.IsolatedAsyncioTestCase):
    async def test_summary_never_contains_sender_or_message_text(self):
        db = DB([{'state': 'sent', 'received_at': 1791720000,
                  'outbound_id': 'message_x', 'message': {'from': 'secret-phone', 'text': {'body': 'secret'}}},
                 {'state': 'review_required', 'received_at': 1791720040,
                  'message': {'from': 'secret-phone2'}}])
        result = await operations(db)
        self.assertEqual(result['review_required_in_last_40'], 1)
        self.assertEqual(result['recent_jobs_checked'], 2)
        self.assertFalse(result['message_delivery_verified'])
        self.assertFalse(result['registration_changed'])
        self.assertNotIn('secret-phone', str(result))
        self.assertNotIn('secret-phone2', str(result))
        self.assertEqual(db.inbox.projection['message'], 0) if 'message' in db.inbox.projection else self.assertNotIn('message', db.inbox.projection)

    async def test_no_history_is_not_claimed_as_disconnection(self):
        result = await operations(DB([]))
        self.assertIsNone(result['most_recent_inbound_at'])
        self.assertIsNone(result['recent_message_state'])
        self.assertIn('nao prova', result['note'])

    async def test_hybrid_mode_safely_marks_test_restriction_and_paid_fallback(self):
        with patch.dict(os.environ, {'JARVIS_REPLY_MODE': 'hybrid',
                'AI_ALLOWED_TEST_ONLY': 'true','AI_PAID_FALLBACK_ENABLED':'false'}):
            result = mode_status()
        self.assertTrue(result['test_only'])
        self.assertFalse(result['paid_fallback_configured'])
        with patch.dict(os.environ, {'JARVIS_REPLY_MODE': 'hybrid',
                'AI_ALLOWED_TEST_ONLY': 'false','AI_PAID_FALLBACK_ENABLED':'true'}):
            result = mode_status()
        self.assertFalse(result['test_only'])
        self.assertTrue(result['paid_fallback_configured'])

    async def test_endpoint_requires_owner_auth_not_device(self):
        app = FastAPI()
        app.include_router(router(lambda: DB([]), lambda db: None))
        with patch.dict(os.environ, {'CRM_ADMIN_TOKEN': 'x' * 48}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as c:
                public = await c.get('/crm/whatsapp/operations')
                self.assertEqual(public.status_code, 401)
                owner = await c.get('/crm/whatsapp/operations',
                                    headers={'Authorization': 'Bearer ' + 'x' * 48})
                self.assertEqual(owner.status_code, 200)
                self.assertFalse(owner.json()['registration_changed'])


if __name__ == '__main__':
    unittest.main()
