import base64
import copy
import io
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from PIL import Image
from pymongo.errors import DuplicateKeyError
from business_intake import BusinessIntake, prepare, validate
from test_contact_memory import Database, Cursor, set_field
import main
from fastapi.testclient import TestClient

def matches(doc, query):
    for key, expected in query.items():
        if key == '$or':
            if not any(matches(doc, q) for q in expected): return False
            continue
        value = doc
        for part in key.split('.'):
            value = value.get(part) if isinstance(value, dict) else None
        if isinstance(expected, dict):
            for op, x in expected.items():
                if op == '$in' and value not in x: return False
                if op == '$exists' and (value is not None) != x: return False
                if op == '$lt' and (value is None or not value < x): return False
        elif value != expected: return False
    return True

class Collection:
    def __init__(self): self.docs = {}
    async def insert_one(self, doc):
        if doc['_id'] in self.docs: raise DuplicateKeyError('duplicate')
        self.docs[doc['_id']] = copy.deepcopy(doc)
    async def find_one(self, query):
        return next((copy.deepcopy(d) for d in self.docs.values() if matches(d, query)), None)
    async def update_one(self, query, update, upsert=False):
        doc = next((d for d in self.docs.values() if matches(d, query)), None)
        new = doc is None
        if new and not upsert: return SimpleNamespace(matched_count=0)
        if new: doc = self.docs.setdefault(query['_id'], {'_id': query['_id']})
        for k, v in (update.get('$setOnInsert', {}) if new else {}).items(): set_field(doc, k, v)
        for k, v in update.get('$set', {}).items(): set_field(doc, k, v)
        return SimpleNamespace(matched_count=1)
    async def find_one_and_update(self, query, update, **kwargs):
        doc = await self.find_one(query)
        if not doc: return None
        await self.update_one(query, update)
        return await self.find_one({'_id': doc['_id']})

class IntakeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'META_APP_SECRET': 'test', 'GROQ_API_KEY': 'test', 'BUSINESS_ID': 'nova_vida'}, clear=True)
        env.start(); self.addCleanup(env.stop)
        self.db = Database()
        self.db.business_documents = Collection()
        self.db.business_entities = Collection()
        self.service = BusinessIntake(self.db)
        self.key = 'idempotency-test-1234'
        due = datetime.now(timezone.utc) + timedelta(days=2)
        self.dates = [due.isoformat(), (due + timedelta(days=7)).isoformat()]
        self.source = 'Ana +5581989927699. ' + ' '.join('Retorno Ana +5581989927699 ' + d for d in self.dates)
        self.analysis = {'summary': 'Ana e dois retornos', 'items': [
            {'kind': 'person', 'name': 'Ana', 'phone': '+5581989927699', 'evidence': 'Ana +5581989927699.'},
            *[{'kind': 'event', 'name': 'Retorno Ana', 'phone': '+5581989927699', 'due_at': d,
               'evidence': 'Retorno Ana +5581989927699 ' + d} for d in self.dates]]}

    async def analyze(self):
        return await self.service.analyze({'text': self.source}, self.key, 'owner')

    async def test_preview_preserves_original_without_creating_contacts_and_idempotency(self):
        with patch('business_intake.provider_call', AsyncMock(return_value=(json.dumps(self.analysis), 0))) as provider:
            first, second = await self.analyze(), await self.analyze()
            self.assertEqual(first['_id'], second['_id']); provider.assert_awaited_once()
        self.assertEqual(len(self.db.contacts.docs), 0)
        original = self.db.business_documents.docs[first['_id']]
        self.assertEqual(original['text'], self.source)
        self.assertNotIn('text', first); self.assertNotIn('original', first)
        with self.assertRaisesRegex(ValueError, 'idempotency_conflict'):
            await self.service.analyze({'text': 'Outro texto'}, self.key, 'owner')

    async def test_two_dates_survive_apply_retry_and_remain_unsent_and_unapproved(self):
        with patch('business_intake.provider_call', AsyncMock(return_value=(json.dumps(self.analysis), 0))): doc = await self.analyze()
        for _ in range(2): result = await self.service.apply(doc['_id'], 'owner')
        self.assertEqual(len(self.db.contacts.docs), 1)
        self.assertEqual(len(self.db.conversation_tasks.docs), 2)
        self.assertEqual(len(self.db.business_entities.docs), 3)
        self.assertEqual(result['result']['messages_sent'], 0)
        self.assertTrue(all(t['state'] == 'planned' for t in self.db.conversation_tasks.docs.values()))
        profile = next(iter(self.db.contacts.docs.values()))
        self.assertNotIn('contact_permission', profile['facts'])
        self.assertEqual(profile['facts']['contact_name']['value'], 'Ana')

    async def test_partial_apply_can_resume_without_duplicate_events(self):
        with patch('business_intake.provider_call', AsyncMock(return_value=(json.dumps(self.analysis), 0))): doc = await self.analyze()
        real = self.db.business_entities.update_one
        calls = 0
        async def interrupted(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2: raise ConnectionError()
            return await real(*args, **kwargs)
        with patch.object(self.db.business_entities, 'update_one', interrupted):
            with self.assertRaisesRegex(ValueError, 'partial_application_retry_safe'): await self.service.apply(doc['_id'], 'owner')
        await self.service.apply(doc['_id'], 'owner')
        self.assertEqual(len(self.db.business_entities.docs), 3)
        self.assertEqual(len(self.db.conversation_tasks.docs), 2)
        self.assertEqual(len(self.db.contact_events.docs), 3)

    async def test_busy_claim_does_not_call_provider_and_expired_claim_recovers(self):
        text, name, mime, raw, digest = prepare({'text': self.source})
        identity = 'nova_vida:' + self.key
        await self.db.business_documents.insert_one({'_id': identity, 'business_id': 'nova_vida', 'state': 'analyzing',
            'sha256': digest, 'lease_until': datetime.now(timezone.utc) + timedelta(minutes=1)})
        with patch('business_intake.provider_call', AsyncMock(return_value=(json.dumps(self.analysis), 0))) as provider:
            with self.assertRaisesRegex(ValueError, 'intake_busy'): await self.analyze()
            provider.assert_not_awaited()
            self.db.business_documents.docs[identity]['lease_until'] -= timedelta(minutes=2)
            self.assertEqual((await self.analyze())['state'], 'preview')
            provider.assert_awaited_once()

    def test_hallucinated_name_phone_and_date_cannot_be_materialized(self):
        bad = {'summary': 'Teste', 'items': [
            {'kind': 'person', 'name': 'João', 'phone': '+5581989927699', 'evidence': 'Ana +5581989927699.'},
            {'kind': 'person', 'name': 'Ana', 'phone': '+5584999999999', 'evidence': 'Ana +5581989927699.'},
            {'kind': 'event', 'name': 'Retorno Ana', 'due_at': self.dates[0], 'evidence': 'Retorno Ana amanhã'}]}
        result = validate(json.dumps(bad), self.source + ' Retorno Ana amanhã')
        self.assertEqual(result['rejected_items'], 2)
        self.assertIsNone(result['items'][0]['due_at'])
        self.assertIsNotNone(result['items'][0]['warning'])

    def test_fake_image_or_oversized_input_rejected_before_provider(self):
        with self.assertRaisesRegex(ValueError, 'invalid_intake_image'):
            prepare({'file': {'name': 'a.png', 'mime': 'image/png', 'data': base64.b64encode(b'not an image').decode()}})
        image = Image.new('RGB', (30, 30)); buffer = io.BytesIO(); image.save(buffer, 'PNG')
        self.assertEqual(prepare({'file': {'name': 'a.png', 'mime': 'image/png', 'data': base64.b64encode(buffer.getvalue()).decode()}})[3], buffer.getvalue())

    async def test_another_deployment_cannot_apply_document(self):
        with patch('business_intake.provider_call', AsyncMock(return_value=(json.dumps(self.analysis), 0))): doc = await self.analyze()
        with patch.dict(os.environ, {'BUSINESS_ID': 'other'}):
            with self.assertRaisesRegex(ValueError, 'intake_not_found'): await self.service.apply(doc['_id'], 'owner')

class AccessTests(unittest.TestCase):
    def test_private_intake_rejects_unauthenticated_request(self):
        with patch.dict(os.environ, {'CRM_ADMIN_TOKEN': 'a' * 40}), TestClient(main.app) as client:
            response = client.post('/crm/intake', json={'text': 'private'})
            self.assertEqual(response.status_code, 401)
    def test_installation_assets_do_not_expose_private_data(self):
        with TestClient(main.app) as client:
            self.assertEqual(client.get('/app.webmanifest').json()['start_url'], '/painel')
            self.assertEqual(client.get('/app-icon/192').status_code, 200)
            self.assertNotIn('fetch', client.get('/app-sw.js').text)

if __name__ == '__main__': unittest.main()
