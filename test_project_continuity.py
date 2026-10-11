"""Continuity regression: preserve drafts, reject stale edits, classify decisions."""
import unittest
from copy import deepcopy
from pymongo.errors import DuplicateKeyError
from project_continuity import ContinuityJournal, VersionConflict, validate_entry
import os
from unittest.mock import patch
import httpx
from fastapi import FastAPI
from crm_admin import router


class Cursor:
    def __init__(self, rows):
        self.rows = rows

    def sort(self, field, direction):
        self.rows.sort(key=lambda row: row[field], reverse=direction < 0)
        return self

    def limit(self, count):
        self.rows = self.rows[:count]
        return self

    async def to_list(self, length):
        return deepcopy(self.rows[:length])


class Collection:
    def __init__(self, database):
        self.docs = {}
        self.database = database

    def find(self, query):
        return Cursor([deepcopy(x) for x in self.docs.values()
                       if all(x.get(k) == v for k, v in query.items())])

    async def find_one(self, query):
        for item in self.docs.values():
            if all(item.get(k) == v for k, v in query.items()):
                return deepcopy(item)
        return None

    async def insert_one(self, doc):
        if doc['_id'] in self.docs:
            raise DuplicateKeyError('already saved')
        self.docs[doc['_id']] = deepcopy(doc)
        return None

    async def update_one(self, query, update):
        existing = await self.find_one(query)
        if existing is None:
            return type('Outcome', (), {'matched_count': 0})()
        row = self.docs[existing['_id']]
        row.update(update.get('$set', {}))
        for k, v in update.get('$inc', {}).items():
            row[k] += v
        for k, v in update.get('$push', {}).items():
            values = v['$each']
            limit = v['$slice']
            row[k] = (row.get(k, []) + values)[limit:]
        return type('Outcome', (), {'matched_count': 1})()


class DB:
    def __init__(self):
        self.project_continuity = Collection(self)
        self.project_continuity_entries = Collection(self)


class ContinuityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = DB()
        self.a = ContinuityJournal(self.db, 'empresa_a')
        self.b = ContinuityJournal(self.db, 'empresa_b')

    async def test_autosave_and_twelve_versions(self):
        one = await self.a.save({'content': 'Primeira ideia', 'revision': 0})
        self.assertEqual(one['revision'], 1)
        for index in range(15):
            one = await self.a.save({'content': 'Versão ' + str(index),
                                     'revision': one['revision']})
        self.assertEqual(one['revision'], 16)
        self.assertEqual(len(one['history']), 12)
        self.assertEqual(one['history'][0]['revision'], 4)
        self.assertEqual((await self.a.current())['content'], 'Versão 14')

    async def test_stale_tabs_cannot_erase_newer_decisions(self):
        first = await self.a.save({'content': 'Uma diretriz', 'revision': 0})
        await self.a.save({'content': 'Nova anotação', 'revision': first['revision']})
        with self.assertRaises(VersionConflict):
            await self.a.save({'content': 'ABA ANTIGA', 'revision': first['revision']})
        self.assertEqual((await self.a.current())['content'], 'Nova anotação')

    async def test_different_businesses_are_isolated(self):
        await self.a.save({'content': 'Segredo empresarial A', 'revision': 0})
        self.assertEqual((await self.b.current())['content'], '')
        await self.a.record({'kind': 'idea', 'text': 'Ideia A', 'key': 'idempotency_key_0001'})
        self.assertEqual(await self.b.entries(), [])

    async def test_directive_requires_explicit_kind_and_revision_reference(self):
        original = await self.a.record({'kind': 'directive', 'text': 'Manter roteamento da IA',
                                         'key': 'idempotency_key_0001'})
        revised = await self.a.record({'kind': 'revised_directive',
                                        'text': 'Manter roteamento e limitar custos',
                                        'key': 'idempotency_key_0002',
                                        'revises': original['key']})
        entries = await self.a.entries()
        self.assertEqual(len(entries), 2)
        self.assertEqual(revised['revises'], original['key'])
        self.assertEqual(entries[1]['text'], 'Manter roteamento da IA')
        with self.assertRaisesRegex(ValueError, 'revision_reference_required'):
            validate_entry({'kind': 'revised_directive', 'text': 'Novo', 'key': 'idempotency_key_0003'})
        with self.assertRaisesRegex(ValueError, 'unknown_prior_directive'):
            await self.a.record({'kind': 'revised_directive', 'text': 'Novo',
                                 'key': 'idempotency_key_0003', 'revises': 'nonexistent_key_1234'})

    async def test_idempotent_entry_and_mismatched_retry(self):
        event = {'kind': 'idea', 'text': 'Ideia original', 'key': 'idempotency_key_0001'}
        await self.a.record(event)
        await self.a.record(event)
        self.assertEqual(len(await self.a.entries()), 1)
        with self.assertRaises(VersionConflict):
            await self.a.record({**event, 'text': 'Texto indevido'})

    async def test_api_requires_owner_token_not_public_access(self):
        app = FastAPI()
        app.include_router(router(lambda: self.db, lambda db: None))
        with patch.dict(os.environ, {'CRM_ADMIN_TOKEN': 'o' * 40}):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as c:
                rejected = await c.get('/crm/continuity')
                self.assertEqual(rejected.status_code, 401)
                owner = await c.get('/crm/continuity', headers={
                    'Authorization': 'Bearer ' + 'o' * 40})
                self.assertEqual(owner.status_code, 200)
                self.assertEqual(owner.json()['revision'], 0)
                unauthenticated_entry = await c.post('/crm/continuity/entries', json={
                    'text': 'Não expor', 'kind': 'idea', 'key': 'idempotency_key_0009'})
                self.assertEqual(unauthenticated_entry.status_code, 401)

    async def test_validation_rejects_unsafe_shapes(self):
        for body in [
            {'content': True, 'revision': 0},
            {'content': 'texto', 'revision': True},
            {'content': 'x' * 30001, 'revision': 0},
        ]:
            with self.assertRaises(ValueError):
                await self.a.save(body)
        with self.assertRaises(ValueError):
            validate_entry({'kind': 'made_up', 'text': 'x', 'key': 'idempotency_key_0001'})


if __name__ == '__main__':
    unittest.main()
