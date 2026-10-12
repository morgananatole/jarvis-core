import copy
import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse
from fastapi import FastAPI
import httpx
from test_business_intake import Collection, matches
from assisted_outreach import AssistedOutreach, chat_link
from crm_admin import router


class Cursor:
    def __init__(self, rows): self.rows = rows
    def sort(self, key, direction):
        self.rows.sort(key=lambda r: r[key], reverse=direction < 0)
        return self
    def skip(self, offset): self.rows = self.rows[offset:]; return self
    def limit(self, limit): self.rows = self.rows[:limit]; return self
    async def to_list(self, count): return copy.deepcopy(self.rows[:count])


class Rows(Collection):
    def find(self, query, projection=None): return Cursor([copy.deepcopy(r) for r in self.docs.values() if matches(r, query)])
    async def count_documents(self, query): return len([r for r in self.docs.values() if matches(r, query)])


class AssistedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'BUSINESS_ID': 'synthetic', 'CRM_ADMIN_TOKEN': 'x'*32}, clear=True)
        self.env.start(); self.addCleanup(self.env.stop)
        self.now = datetime.now(timezone.utc)
        self.db = SimpleNamespace(contacts=Rows(), assisted_outreach=Rows(), human_requests=Rows())
        self.db.contacts.docs['synthetic-contact'] = {'_id': 'synthetic-contact', 'contact_no': 1,
            'phone': '5581999999999', 'facts': {'contact_permission': {'value': 'allowed'}}}
        self.service = AssistedOutreach(self.db, lambda: self.now)
        self.body = {'contact_no': 1, 'text': 'Olá! Podemos conversar? & mais', 'due_at': self.now.isoformat()}
        self.key = 'synthetic-draft-123456'

    async def draft(self): return (await self.service.prepare(self.body, self.key))['id']

    async def test_drafting_is_idempotent_and_never_pauses_or_sends(self):
        first, again = await self.service.prepare(self.body, self.key), await self.service.prepare(self.body, self.key)
        self.assertEqual(first['id'], again['id'])
        self.assertTrue(again['duplicate'])
        self.assertEqual(len(self.db.assisted_outreach.docs), 1)
        self.assertFalse(self.db.contacts.docs['synthetic-contact'].get('human_mode'))
        self.assertEqual(first['messages_sent'], 0)
        with self.assertRaisesRegex(ValueError, 'idempotency_conflict'):
            await self.service.prepare({**self.body, 'text': 'changed'}, self.key)

    async def test_open_pauses_and_only_returns_official_link(self):
        ident = await self.draft()
        result = await self.service.open(ident)
        self.assertEqual(self.db.contacts.docs['synthetic-contact']['human_takeover_source'], 'panel')
        self.assertTrue(self.db.contacts.docs['synthetic-contact']['human_mode'])
        parsed = urlparse(result['url'])
        self.assertEqual(parsed.netloc, 'wa.me')
        self.assertEqual(parse_qs(parsed.query)['text'], [self.body['text']])
        self.assertEqual(result['messages_sent'], 0)
        self.assertFalse(result['delivery_verified'])
        self.assertEqual((await self.service.open(ident))['url'], result['url'])

    async def test_unknown_permission_draft_allowed_but_open_blocked(self):
        self.db.contacts.docs['synthetic-contact']['facts'] = {}
        ident = await self.draft()
        with self.assertRaisesRegex(ValueError, 'permission_required'): await self.service.open(ident)
        self.assertFalse(self.db.contacts.docs['synthetic-contact'].get('human_mode'))

    async def test_refusal_blocks_prepare_and_permission_override(self):
        ident = await self.draft()
        self.db.contacts.docs['synthetic-contact']['do_not_contact'] = True
        with self.assertRaisesRegex(ValueError, 'do_not_contact'): await self.service.open(ident)
        with self.assertRaisesRegex(ValueError, 'do_not_contact'):
            await self.service.permission(ident, 'existing customer authorization')
        with self.assertRaisesRegex(ValueError, 'do_not_contact'):
            await self.service.prepare(self.body, 'another-key-12345678')

    async def test_future_schedule_does_not_start_or_open_app(self):
        self.body['due_at'] = (self.now + timedelta(days=1)).isoformat()
        ident = await self.draft()
        with self.assertRaisesRegex(ValueError, 'draft_not_due'): await self.service.open(ident)
        self.assertFalse(self.db.contacts.docs['synthetic-contact'].get('human_mode'))

    async def test_naive_date_placeholder_and_boolean_contact_rejected(self):
        for body, reason in [({**self.body, 'due_at': '2026-10-12T12:00:00'}, 'due_at_requires_timezone'),
                             ({**self.body, 'text': 'Olá, (nome)'}, 'unresolved_placeholder'),
                             ({**self.body, 'contact_no': True}, 'invalid_contact')]:
            with self.assertRaisesRegex(ValueError, reason): await self.service.prepare(body, self.key)
        self.assertFalse(self.db.assisted_outreach.docs)

    async def test_manual_outcome_never_claims_delivery_and_does_not_resume_ai(self):
        ident = await self.draft()
        with self.assertRaisesRegex(ValueError, 'open_first'): await self.service.report(ident, 'sent_reported')
        await self.service.open(ident)
        for state in ['sent_reported', 'reply_reported']:
            result = await self.service.report(ident, state)
            self.assertFalse(result['delivery_verified']); self.assertEqual(result['messages_sent'], 0)
        self.assertTrue(self.db.contacts.docs['synthetic-contact']['human_mode'])
        self.assertEqual(self.db.assisted_outreach.docs[ident]['source'], 'operator_report')

    async def test_decline_suppresses_future_open_and_drafts(self):
        ident = await self.draft(); await self.service.open(ident)
        await self.service.report(ident, 'declined_reported')
        self.assertTrue(self.db.contacts.docs['synthetic-contact']['do_not_contact'])
        with self.assertRaisesRegex(ValueError, 'draft_already_finished'): await self.service.open(ident)

    async def test_refusal_during_pause_is_rechecked(self):
        ident = await self.draft()
        async def pause(number, enabled):
            self.db.contacts.docs['synthetic-contact'].update(human_mode=True, do_not_contact=True)
        with patch('assisted_outreach.HumanService.mode', AsyncMock(side_effect=pause)):
            with self.assertRaisesRegex(ValueError, 'contact_changed'): await self.service.open(ident)
        self.assertEqual(self.db.assisted_outreach.docs[ident]['state'], 'prepared')

    async def test_permission_needs_evidence_and_is_never_inferred(self):
        self.db.contacts.docs['synthetic-contact']['facts'] = {}
        ident = await self.draft()
        with self.assertRaisesRegex(ValueError, 'permission_evidence_required'):
            await self.service.permission(ident, '')
        await self.service.permission(ident, 'Existing explicit request recorded in synthetic pilot')
        self.assertEqual(self.db.contacts.docs['synthetic-contact']['facts']['contact_permission']['status'], 'operator_reviewed')

    async def test_business_scope_and_paginated_list(self):
        ident = await self.draft()
        result = await self.service.list()
        self.assertEqual(result['total'], 1)
        self.assertFalse(result['automatic_app_sync'])
        self.assertFalse(result['automatic_whatsapp_send'])
        self.assertEqual((await self.service.list(1))['rows'], [])
        with patch.dict(os.environ, {'BUSINESS_ID': 'other'}):
            with self.assertRaisesRegex(ValueError, 'draft_not_found'): await self.service.open(ident)
            self.assertEqual((await self.service.list())['total'], 0)

    async def test_owner_only_http_and_invalid_report(self):
        app = FastAPI(); app.include_router(router(lambda:self.db, lambda _:None))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='https://synthetic') as c:
            self.assertEqual((await c.get('/crm/assisted-outreach')).status_code, 401)
            headers={'Authorization': 'Bearer '+'x'*32, 'Idempotency-Key': self.key}
            r=await c.post('/crm/assisted-outreach',headers=headers,json=self.body)
            self.assertEqual(r.status_code,200)
            ident=r.json()['id']
            r=await c.post('/crm/assisted-outreach/'+ident+'/report',headers=headers,json=[])
            self.assertEqual(r.status_code,409)
            self.assertEqual((await c.get('/crm/assisted-outreach?offset=-1',headers=headers)).status_code,400)

    def test_phone_cannot_inject_url_destination(self):
        for phone in ['https://evil.test', '5581999999999?text=bad', '+5581999999999']:
            with self.assertRaisesRegex(ValueError, 'invalid_phone'): chat_link(phone, 'hello')


if __name__ == '__main__': unittest.main()
