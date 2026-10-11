"""Durable human takeover and idempotent operator replies for the single-instance service."""
import asyncio
import os
import re
import unicodedata
import weakref
import uuid
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from contact_memory import ContactMemory, contact_key

_locks = weakref.WeakValueDictionary()


def conversation_lock(key):
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


def takeover_reason(text):
    value = ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                    if unicodedata.category(c) != 'Mn')
    value = re.sub(r'\bnao\s+(?:e\s+)?(?:urgente|urgencia)\b', '', value)
    if re.search(r'\b(urgente|urgencia|resgate)\b', value):
        return 'urgent'
    if re.search(r'\b(nao|nunca)\s+(quero|preciso)\s+(falar|um atendente)', value):
        return None
    if re.search(r'\b(atendente|humano|pessoa real|pessoa de verdade|falar com (o )?morgan)\b', value):
        return 'customer_request'
    return None


def active_window(profile, now=None):
    last = profile.get('last_inbound_at')
    now = now or datetime.now(timezone.utc)
    if last and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return bool(last and now - timedelta(hours=23) < last <= now)


def exclusive_human(text):
    value = ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                    if unicodedata.category(c) != 'Mn')
    return bool(re.search(r'\b(?:so|somente|apenas)\s+(?:um\s+)?(?:humano|atendente|morgan)\b|'
                          r'\bnao quero (?:falar|conversar) com (?:a )?(?:ia|robo|assistente virtual)\b', value))


class HumanService:
    def __init__(self, db, send, tester):
        self.db, self.send, self.tester = db, send, tester

    async def request(self, phone, source_id, reason):
        profile = await ContactMemory(self.db).ensure(phone)
        now = datetime.now(timezone.utc)
        # Called inside the contact lock by the webhook/operator.
        new = not profile.get('human_mode')
        prior = await self.db.human_requests.find_one({'_id': profile['_id']}) or {}
        waiting = {}
        if new or not prior.get('pending_since') or (profile.get('ai_waiting_assist') and reason != 'human_conversation'):
            since = (profile.get('human_since') or now) if (
                not new and 'pending_since' not in prior and prior.get('state') == 'waiting') else now
            waiting = {'pending_since': since, 'wait_episode': source_id,
                       'wait_notice_state': 'pending'}
        if reason != 'human_conversation':
            await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                'ai_waiting_assist': False}})
        # New messages must not restart the five-minute clock or erase urgency.
        queue_reason = prior.get('reason', reason) if reason == 'human_conversation' else reason
        if prior.get('reason') == 'urgent' and not new:
            queue_reason = 'urgent'
        if new:
            await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                'human_mode': True, 'human_since': now}, '$inc': {'automation_epoch': 1}})
        await self.db.human_requests.update_one({'_id': profile['_id']}, {'$set': {
            'contact_no': profile['contact_no'], 'reason': queue_reason,
            'source_message_id': source_id, 'updated_at': now, 'unread': True, **waiting},
            '$max': {'priority': 90 if reason == 'urgent' else 40},
            '$setOnInsert': {'created_at': now, 'state': 'waiting'}}, upsert=True)
        # A resolved queue item can be reused by a new customer request.
        if new:
            await self.db.human_requests.update_one({'_id': profile['_id']}, {'$set': {'state': 'waiting'}})
        await self.db.conversation_tasks.update_one({'_id': profile['_id'] + ':next',
            'state': {'$in': ['approved', 'planned', 'blocked']}}, {'$set': {
                'state': 'held', 'reason': 'human_takeover'}})
        return new

    async def mode(self, number, human):
        profile = await self.db.contacts.find_one({'contact_no': number})
        if not profile:
            raise ValueError('contact_not_found')
        async with conversation_lock(profile['_id']):
            await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                'human_mode': human, 'human_since': datetime.now(timezone.utc) if human else None},
                '$inc': {'automation_epoch': 1}})
            await self.db.human_requests.update_one({'_id': profile['_id']}, {'$set': {
                'state': 'active' if human else 'resolved', 'contact_no': number,
                'unread': False, 'updated_at': datetime.now(timezone.utc),
                'pending_since': datetime.now(timezone.utc) if human else None,
                'wait_episode': uuid.uuid4().hex, 'wait_notice_state': 'pending' if human else 'cancelled'}}, upsert=True)
            await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                'ai_waiting_assist': False}})
        return {'mode': 'human' if human else 'jarvis'}

    async def reply(self, number, text, nonce):
        if not isinstance(text, str) or not text.strip() or len(text) > 4000:
            raise ValueError('invalid_text')
        if not isinstance(nonce, str) or not re.fullmatch(r'[A-Za-z0-9_-]{16,80}', nonce):
            raise ValueError('idempotency_key_required')
        profile = await self.db.contacts.find_one({'contact_no': number})
        if not profile:
            raise ValueError('contact_not_found')
        async with conversation_lock(profile['_id']):
            profile = await self.db.contacts.find_one({'_id': profile['_id']})
            if not profile.get('human_mode'):
                raise ValueError('take_over_first')
            if not active_window(profile):
                raise ValueError('approved_template_required')
            if os.getenv('AI_ALLOWED_TEST_ONLY', 'true') == 'true' and not self.tester(profile['phone']):
                raise ValueError('test_recipient_only')
            job_id = 'operator:' + str(number) + ':' + nonce
            try:
                await self.db.operator_jobs.insert_one({'_id': job_id, 'contact_no': number,
                    'state': 'sending', 'created_at': datetime.now(timezone.utc),
                    'expires_at': datetime.now(timezone.utc) + timedelta(days=90)})
            except DuplicateKeyError:
                prior = await self.db.operator_jobs.find_one({'_id': job_id})
                return {'state': prior['state'], 'duplicate': True}
            await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                'ai_waiting_assist': False}})
            try:
                mid = await self.send(profile['phone'], text.strip())
                await ContactMemory(self.db).record_outbound(profile['phone'], mid, text.strip())
                await self.db.contact_events.update_one({'_id': mid}, {'$set': {'operator': True}})
                await self.db.operator_jobs.update_one({'_id': job_id}, {'$set': {'state': 'accepted', 'outbound_id': mid}})
                await self.db.human_requests.update_one({'_id': profile['_id']}, {'$set': {'unread': False}})
                await self.db.human_requests.update_one({'_id': profile['_id']}, {'$set': {
                    'pending_since': None, 'wait_notice_state': 'answered',
                    'last_operator_reply_at': datetime.now(timezone.utc)}})
                await self.db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                    'ai_waiting_assist': False}})
                return {'state': 'accepted'}
            except Exception:
                await self.db.operator_jobs.update_one({'_id': job_id}, {'$set': {'state': 'review_required'}})
                await self.db.human_requests.update_one({'_id': profile['_id']}, {'$set': {
                    'pending_since': None, 'wait_notice_state': 'review_required',
                    'reason': 'reply_failed_or_uncertain', 'unread': True}})
                return {'state': 'review_required'}
