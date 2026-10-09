import copy
import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from pymongo.errors import DuplicateKeyError
from contact_memory import (ContactMemory, canonical_phone, contact_key,
                            unpack_reply, conversation_plan)
from import_google_contacts import rows_to_contacts
from ai_router import ReplyRouter


def set_field(doc, key, value):
    parts = key.split('.')
    for p in parts[:-1]:
        doc = doc.setdefault(p, {})
    doc[parts[-1]] = copy.deepcopy(value)


class Collection:
    def __init__(self):
        self.docs = {}
    async def create_index(self, *args, **kwargs):
        pass
    async def find_one(self, query):
        return copy.deepcopy(self.docs.get(query['_id']))
    async def insert_one(self, doc):
        if doc['_id'] in self.docs:
            raise DuplicateKeyError('duplicate')
        self.docs[doc['_id']] = copy.deepcopy(doc)
    async def update_one(self, query, update, upsert=False):
        key = query['_id']
        new = key not in self.docs
        if new and not upsert:
            return
        doc = self.docs.setdefault(key, {'_id': key})
        if new:
            for k, v in update.get('$setOnInsert', {}).items():
                set_field(doc, k, v)
        for k, v in update.get('$set', {}).items():
            set_field(doc, k, v)
        for k, v in update.get('$inc', {}).items():
            doc[k] = doc.get(k, 0) + v
    async def find_one_and_update(self, query, update, **kwargs):
        await self.update_one(query, update, kwargs.get('upsert', False))
        return await self.find_one(query)


class Database:
    def __init__(self):
        self.delivery_receipts = Collection()
        self.contacts = Collection()
        self.contact_events = Collection()
        self.conversation_tasks = Collection()
        self.crm_counters = Collection()


class ContactTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        env = patch.dict(os.environ, {'META_APP_SECRET': 'fake-test'}, clear=True)
        env.start()
        self.addCleanup(env.stop)
        self.db = Database()
        self.memory = ContactMemory(self.db)
        self.now = datetime.now(timezone.utc)

    async def test_phone_alias_deduplicates_and_assigns_numeric_id(self):
        first = await self.memory.ensure('5584981584252')
        second = await self.memory.ensure('558481584252')
        self.assertEqual(first['contact_no'], 1)
        self.assertEqual(first['_id'], second['_id'])
        self.assertEqual(len(self.db.contacts.docs), 1)

    async def test_message_deduplication_and_single_next_conversation(self):
        for mid in ('m1', 'm1', 'm2'):
            await self.memory.record_inbound('5584981584252', mid, 'qual o valor?', self.now.timestamp())
        profile = await self.memory.ensure('5584981584252')
        self.assertEqual(profile['inbound_count'], 2)
        self.assertEqual(len(self.db.conversation_tasks.docs), 1)
        task = next(iter(self.db.conversation_tasks.docs.values()))
        self.assertFalse(task['automatic_send_enabled'])
        self.assertTrue(task['requires_window_or_template'])

    async def test_profile_survives_thirty_days_and_keeps_provenance(self):
        await self.memory.record_inbound('5584981584252', 'm1', 'Sou Maria', self.now.timestamp())
        _, facts = unpack_reply(json.dumps({'reply': 'Olá Maria', 'facts': {
            'contact_name': {'value': 'Maria', 'evidence': 'Sou Maria'}}}), 'Sou Maria')
        await self.memory.apply_facts('5584981584252', 'm1', facts)
        profile = await self.memory.ensure('5584981584252')
        self.assertNotIn('expires_at', profile)
        self.assertEqual(profile['facts']['contact_name']['source_message_id'], 'm1')
        self.assertIn('Maria', await self.memory.context('558481584252'))
        event = self.db.contact_events.docs['m1']
        self.assertGreater(event['expires_at'], self.now + timedelta(days=30))

    async def test_opt_out_suppresses_task_even_without_ai(self):
        await self.memory.record_inbound('5584981584252', 'm1', 'Não me envie mais mensagens', self.now.timestamp())
        self.assertEqual(next(iter(self.db.conversation_tasks.docs.values()))['state'], 'suppressed')

    def test_no_invented_name_permission_or_modality_from_refusal(self):
        text = 'Ele não quer tratamento'
        raw = json.dumps({'reply': 'Entendi', 'facts': {
            'contact_name': {'value': 'Maria', 'evidence': text},
            'contact_permission': {'value': 'allowed', 'evidence': text},
            'requested_modality': {'value': 'involuntary', 'evidence': text},
            'treatment_willingness': {'value': 'refuses', 'evidence': text}}})
        reply, facts = unpack_reply(raw, text)
        self.assertEqual(reply, 'Entendi')
        self.assertEqual(set(facts), {'treatment_willingness'})

    def test_long_conversation_alone_does_not_make_hot_lead(self):
        plan = conversation_plan({'inbound_count': 500}, self.now)
        self.assertEqual(plan['priority'], 20)
        self.assertGreater(plan['due_at'] - self.now, timedelta(hours=6))

    def test_postcare_thirty_day_conversation_and_requested_time(self):
        profile = {'facts': {'lifecycle': {'value': 'postcare'}}}
        self.assertEqual(conversation_plan(profile, self.now)['due_at'], self.now + timedelta(days=30))
        due = self.now + timedelta(days=2)
        profile['facts']['next_contact_at'] = {'value': due.isoformat()}
        self.assertEqual(conversation_plan(profile, self.now)['due_at'], due)

    def test_google_import_requires_country_code_and_does_not_infer_consent(self):
        rows = [{'Name': 'Maria', 'Phone 1 - Value': '+55 84 98158-4252'},
                {'Name': 'Sem DDI', 'Phone 1 - Value': '81989927699'}]
        self.assertEqual(list(rows_to_contacts(rows)), [('5584981584252', 'Maria')])

    async def test_outbound_record_acceptance_is_not_delivery(self):
        await self.memory.record_outbound('5584981584252', 'out1', 'Olá')
        self.assertEqual(self.db.contact_events.docs['out1']['delivery'], 'accepted')

    async def test_hybrid_extracts_once_and_remembers_name_after_thirty_days(self):
        self.db.ai_history, self.db.ai_policy, self.db.ai_budgets = Collection(), Collection(), Collection()
        calls = []
        async def call(provider, messages, config):
            calls.append(messages)
            return json.dumps({'reply': 'Olá Maria', 'facts': {
                'contact_name': {'value': 'Maria', 'evidence': 'Sou Maria'}}}), 0
        phone = '5584981584252'
        await self.memory.record_inbound(phone, 'm1', 'Sou Maria', self.now.timestamp())
        with patch.dict(os.environ, {'GROQ_API_KEY': 'fake-free'}):
            router = ReplyRouter(self.db, call=call, clock=lambda: self.now.timestamp())
            self.assertEqual(await router.reply(phone, 'Sou Maria', 'Regras', source_message_id='m1'), 'Olá Maria')
            later = ReplyRouter(self.db, call=call, clock=lambda: (self.now + timedelta(days=31)).timestamp())
            await later.reply(phone, 'voltei', 'Regras', source_message_id='m2')
        self.assertEqual(len(calls), 2)  # No separate extraction API call.
        self.assertIn('Cadastro anterior', str(calls[-1]))
        self.assertIn('Maria', str(calls[-1]))
        self.assertEqual((await self.memory.ensure(phone))['facts']['contact_name']['source_message_id'], 'm1')


if __name__ == '__main__':
    unittest.main()
