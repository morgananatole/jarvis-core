"""Private scheduled drafts opened by a human in WhatsApp. Never sends messages."""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from pymongo.errors import DuplicateKeyError
from human_service import HumanService


def business():
    return os.getenv('BUSINESS_ID', 'nova_vida')


def utc(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError('invalid_due_at')
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError('due_at_requires_timezone')
    return value.astimezone(timezone.utc)


def can_contact(profile):
    if profile.get('do_not_contact') or profile.get('facts', {}).get('contact_permission', {}).get('value') == 'declined':
        return 'do_not_contact'
    if profile.get('facts', {}).get('contact_permission', {}).get('value') != 'allowed':
        return 'permission_required'
    return None


def chat_link(phone, text):
    if not isinstance(phone, str) or not re.fullmatch(r'[1-9][0-9]{7,14}', phone):
        raise ValueError('invalid_phone')
    return 'https://wa.me/' + phone + '?' + urlencode({'text': text})


class AssistedOutreach:
    def __init__(self, db, clock=None):
        self.db = db
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def prepare(self, body, key):
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', key):
            raise ValueError('idempotency_key_required')
        if not isinstance(body, dict) or set(body) - {'contact_no', 'text', 'due_at'}:
            raise ValueError('invalid_draft')
        number, text = body.get('contact_no'), body.get('text')
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ValueError('invalid_contact')
        if not isinstance(text, str) or not text.strip() or len(text) > 1500:
            raise ValueError('invalid_text')
        text = text.strip()
        if re.search(r'\{[^}]+\}|\(nome\)|\[nome\]', text, re.I):
            raise ValueError('unresolved_placeholder')
        due = utc(body.get('due_at'))
        profile = await self.db.contacts.find_one({'contact_no': number})
        if not profile:
            raise ValueError('contact_not_found')
        if can_contact(profile) == 'do_not_contact':
            raise ValueError('do_not_contact')
        payload = {'contact_no': number, 'text': text, 'due_at': due.isoformat()}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        ident = hashlib.sha256((business() + ':' + key).encode()).hexdigest()
        draft = {'_id': ident, 'business_id': business(), 'digest': digest,
                 **payload, 'due_at': due, 'state': 'prepared', 'created_at': self.clock()}
        try:
            await self.db.assisted_outreach.insert_one(draft)
        except DuplicateKeyError:
            old = await self.db.assisted_outreach.find_one({'_id': ident, 'business_id': business()})
            if not old or old.get('digest') != digest:
                raise ValueError('idempotency_conflict')
            return {'id': ident, 'state': old['state'], 'duplicate': True, 'messages_sent': 0}
        return {'id': ident, 'state': 'prepared', 'messages_sent': 0}

    async def get(self, ident):
        draft = await self.db.assisted_outreach.find_one({'_id': ident, 'business_id': business()})
        if not draft:
            raise ValueError('draft_not_found')
        return draft

    async def open(self, ident):
        draft = await self.get(ident)
        if draft['state'] not in {'prepared', 'opened'}:
            raise ValueError('draft_already_finished')
        if utc(draft['due_at']) > self.clock():
            raise ValueError('draft_not_due')
        profile = await self.db.contacts.find_one({'contact_no': draft['contact_no']})
        if not profile:
            raise ValueError('contact_not_found')
        reason = can_contact(profile)
        if reason:
            raise ValueError(reason)
        # Pause is persisted before returning a destination. No send callback.
        await HumanService(self.db, None, None).mode(draft['contact_no'], True)
        profile = await self.db.contacts.find_one({'contact_no': draft['contact_no']})
        if not profile or can_contact(profile):
            raise ValueError('contact_changed')
        if not profile.get('human_mode'):
            raise ValueError('human_pause_not_confirmed')
        url = chat_link(profile['phone'], draft['text'])
        result = await self.db.assisted_outreach.update_one(
            {'_id': ident, 'business_id': business(), 'state': {'$in': ['prepared', 'opened']}},
            {'$set': {'state': 'opened', 'opened_at': self.clock()}})
        if not result.matched_count:
            raise ValueError('draft_already_finished')
        return {'state': 'opened', 'url': url, 'messages_sent': 0,
                'human_mode': True, 'delivery_verified': False,
                'notice': 'Conversa preparada. Você confirma o envio no WhatsApp. Abrir não comprova envio.'}

    async def report(self, ident, state):
        if state not in {'sent_reported', 'reply_reported', 'declined_reported', 'cancelled'}:
            raise ValueError('invalid_report')
        draft = await self.get(ident)
        if state != 'cancelled' and draft['state'] not in {'opened', 'sent_reported', 'reply_reported'}:
            raise ValueError('open_first')
        allowed = {'prepared', 'opened', 'sent_reported', 'reply_reported'}
        if draft['state'] not in allowed:
            raise ValueError('draft_already_finished')
        if state == 'declined_reported':
            await self.db.contacts.update_one({'contact_no': draft['contact_no']},
                {'$set': {'do_not_contact': True}})
        updated = await self.db.assisted_outreach.update_one(
            {'_id': ident, 'business_id': business(), 'state': draft['state']},
            {'$set': {'state': state, 'reported_at': self.clock(), 'source': 'operator_report'}})
        if not updated.matched_count:
            raise ValueError('draft_changed')
        # Never claim a Meta delivery receipt, record an outbound event, or resume AI.
        return {'state': state, 'delivery_verified': False, 'messages_sent': 0}

    async def permission(self, ident, reference):
        draft = await self.get(ident)
        if draft['state'] not in {'prepared', 'opened'}:
            raise ValueError('draft_already_finished')
        if not isinstance(reference, str) or not 8 <= len(reference.strip()) <= 300:
            raise ValueError('permission_evidence_required')
        profile = await self.db.contacts.find_one({'contact_no': draft['contact_no']})
        if not profile or can_contact(profile) == 'do_not_contact':
            raise ValueError('do_not_contact')
        await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
            'facts.contact_permission': {'value': 'allowed', 'status': 'operator_reviewed',
                'source': 'owner_permission_reference', 'reported_at': self.clock(),
                'evidence': reference.strip()}}})
        return {'recorded': True, 'messages_sent': 0}

    async def list(self, offset=0):
        if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 100000:
            raise ValueError('invalid_offset')
        query = {'business_id': business()}
        total = await self.db.assisted_outreach.count_documents(query)
        rows = await self.db.assisted_outreach.find(query).sort('due_at', 1).skip(offset).limit(100).to_list(100)
        numbers = list({row['contact_no'] for row in rows})
        contacts = await self.db.contacts.find({'contact_no': {'$in': numbers}},
            {'contact_no': 1, 'facts.contact_permission': 1, 'do_not_contact': 1}).to_list(100) if numbers else []
        profiles = {p['contact_no']: p for p in contacts}
        result = []
        for row in rows:
            p = profiles.get(row['contact_no'])
            reason = can_contact(p) if p else 'contact_not_found'
            result.append({'id': row['_id'], 'contact_no': row['contact_no'],
                'text': row['text'], 'due_at': row['due_at'], 'state': row['state'],
                'blocked_reason': reason, 'due': utc(row['due_at']) <= self.clock(),
                'delivery_verified': False})
        return {'rows': result, 'total': total, 'offset': offset, 'limit': 100, 'messages_sent': 0,
                'automatic_whatsapp_send': False, 'automatic_app_sync': False}
