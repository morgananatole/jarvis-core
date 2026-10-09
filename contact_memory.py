"""Private contact profiles and purposeful conversation tasks; never sends messages."""
import hashlib
import hmac
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone

from pymongo.errors import DuplicateKeyError

FIELDS = {'contact_name', 'preferred_address', 'patient_name', 'relationship',
          'patient_age', 'city', 'substances', 'treatment_willingness',
          'requested_modality', 'main_concern', 'lifecycle', 'contact_permission'}
FIELDS.update({'next_contact_at', 'followup_purpose'})
ENUMS = {'treatment_willingness': {'wants', 'refuses', 'undecided'},
         'requested_modality': {'voluntary', 'involuntary'},
         'lifecycle': {'lead', 'considering', 'enrolled', 'postcare', 'closed'},
         'contact_permission': {'allowed', 'declined'}}


def canonical_phone(phone):
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 12 and digits.startswith('55') and digits[4] in '6789':
        digits = digits[:4] + '9' + digits[4:]
    if not digits.isascii() or not 8 <= len(digits) <= 15:
        raise ValueError('invalid_phone')
    return digits


def contact_key(phone):
    secret = os.getenv('CRM_ID_SECRET') or os.getenv('META_APP_SECRET')
    if not secret:
        raise ValueError('contact_identity_secret_missing')
    return hmac.new(secret.encode(), canonical_phone(phone).encode(), hashlib.sha256).hexdigest()


def unpack_reply(raw, source_text):
    """Plain replies remain compatible. Ground profile updates in latest user text."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return raw, {}
    if not isinstance(data, dict) or not isinstance(data.get('reply'), str):
        raise ValueError('invalid_structured_reply')
    facts = {}
    for field, item in (data.get('facts') or {}).items() if isinstance(data.get('facts'), dict) else []:
        if field not in FIELDS or not isinstance(item, dict):
            continue
        value, evidence = item.get('value'), item.get('evidence')
        if (not isinstance(value, str) or not value.strip() or len(value) > 300
                or not isinstance(evidence, str) or len(evidence) < 3
                or evidence not in source_text):
            continue
        if field == 'next_contact_at':
            try:
                due = datetime.fromisoformat(value)
                now = datetime.now(timezone.utc)
                if due.tzinfo is None or not now < due <= now + timedelta(days=90):
                    continue
            except ValueError:
                continue
        elif field in ENUMS:
            if value not in ENUMS[field]:
                continue
            normalized = ''.join(c for c in unicodedata.normalize('NFD', evidence.casefold())
                                 if unicodedata.category(c) != 'Mn')
            if field == 'requested_modality':
                word = 'involuntar' if value == 'involuntary' else 'voluntar'
                if not re.search(r'\b' + word, normalized):
                    continue
            if field == 'contact_permission' and value == 'allowed':
                if (re.search(r'\b(nao|nunca)\b', normalized) or not re.search(
                        r'autorizo|aceito receber|pode me chamar|pode entrar em contato|pode me contatar', normalized)):
                    continue
        elif value.casefold() not in evidence.casefold():
            continue
        facts[field] = {'value': value, 'evidence': evidence[:500]}
    return data['reply'], facts


def conversation_plan(profile, now):
    values = {k: v.get('value') for k, v in profile.get('facts', {}).items()}
    if values.get('contact_permission') == 'declined' or profile.get('do_not_contact'):
        return {'state': 'suppressed', 'purpose': 'Respeitar pedido de não contato', 'priority': 0}
    signals = profile.get('signals', {})
    count = profile.get('inbound_count', 0)
    priority = min(20, count * 2)  # Conversation length alone cannot make a hot lead.
    reasons = []
    for signal, points in [('availability', 20), ('price', 15), ('decision', 30)]:
        if signals.get(signal):
            priority += points
            reasons.append(signal)
    if values.get('lifecycle') in ('enrolled', 'postcare'):
        delay, purpose = 30 * 86400, 'Retomar vínculo e verificar como está o acompanhamento'
    elif priority >= 50:
        delay, purpose = 6 * 3600, 'Retomar decisão e esclarecer a pendência de atendimento'
    elif priority >= 20:
        delay, purpose = 86400, 'Retomar dúvida concreta e verificar próximo passo'
    else:
        delay, purpose = 7 * 86400, 'Verificar se ainda deseja continuar a conversa'
    due_at = now + timedelta(seconds=delay)
    if values.get('next_contact_at'):
        requested = datetime.fromisoformat(values['next_contact_at'])
        if requested > now:
            due_at = requested
            purpose = values.get('followup_purpose') or 'Retomar conversa no horário solicitado'
    return {'state': 'planned', 'due_at': due_at,
            'purpose': purpose, 'priority': min(100, priority), 'signals': reasons,
            'contact_permission': values.get('contact_permission', 'unknown')}


class ContactMemory:
    def __init__(self, database):
        self.db = database

    async def initialize(self):
        await self.db.contacts.create_index('contact_no', unique=True)
        await self.db.contact_events.create_index([('contact_key', 1), ('created_at', -1)])
        await self.db.contact_events.create_index('expires_at', expireAfterSeconds=0)
        await self.db.conversation_tasks.create_index([('state', 1), ('due_at', 1)])

    async def ensure(self, phone):
        key = contact_key(phone)
        current = await self.db.contacts.find_one({'_id': key})
        if current:
            return current
        counter = await self.db.crm_counters.find_one_and_update(
            {'_id': 'contacts'}, {'$inc': {'value': 1}}, upsert=True, return_document=True)
        now = datetime.now(timezone.utc)
        try:
            await self.db.contacts.update_one({'_id': key}, {'$setOnInsert': {
                'contact_no': counter['value'], 'phone': canonical_phone(phone),
                'created_at': now, 'facts': {}, 'inbound_count': 0}}, upsert=True)
        except DuplicateKeyError:
            pass
        return await self.db.contacts.find_one({'_id': key})

    async def record_inbound(self, phone, message_id, text, timestamp):
        profile = await self.ensure(phone)
        key = profile['_id']
        now = datetime.now(timezone.utc)
        try:
            await self.db.contact_events.insert_one({'_id': message_id, 'contact_key': key,
                'contact_no': profile['contact_no'], 'direction': 'inbound', 'text': text[:6000],
                'created_at': datetime.fromtimestamp(timestamp, timezone.utc),
                'expires_at': now + timedelta(days=90)})
        except DuplicateKeyError:
            return profile
        lower = text.casefold()
        signals = {}
        for kind, pattern in [('availability', r'\b(vaga|vagas|resgate)\b'),
                              ('price', r'\b(preço|preco|valor|custa|pagamento)\b'),
                              ('decision', r'\b(quero contratar|vamos fechar|quero internar)\b')]:
            if re.search(pattern, lower):
                if kind == 'decision' and re.search(r'\b(não|nao|nunca)\s+(quero|vamos)\b', lower):
                    continue
                signals['signals.' + kind] = True
        # Immediate opt-out suppression, including while AI is unavailable.
        if lower.strip() == 'parar' or re.search(r'\b(não me mande|nao me mande|não me envie|nao me envie|não quero receber|nao quero receber|pare de enviar|remova meu contato)\b', lower):
            signals['do_not_contact'] = True
        await self.db.contacts.update_one({'_id': key}, {
            '$set': {'last_inbound_at': datetime.fromtimestamp(timestamp, timezone.utc), **signals},
            '$inc': {'inbound_count': 1}})
        await self.plan(key, message_id)
        return await self.db.contacts.find_one({'_id': key})

    async def apply_facts(self, phone, message_id, facts):
        key = contact_key(phone)
        now = datetime.now(timezone.utc)
        changes = {'facts.' + name: {**item, 'source_message_id': message_id,
                   'reported_at': now, 'status': 'reported'} for name, item in facts.items()}
        if changes:
            await self.db.contacts.update_one({'_id': key}, {'$set': changes})
            await self.db.contact_events.update_one({'_id': message_id}, {'$set': {'extracted_facts': facts}})
        await self.plan(key, message_id)

    async def plan(self, key, message_id):
        profile = await self.db.contacts.find_one({'_id': key})
        if not profile:
            return
        now = datetime.now(timezone.utc)
        plan = conversation_plan(profile, now)
        task = {**plan, 'contact_key': key, 'contact_no': profile['contact_no'],
                'updated_at': now, 'source_message_id': message_id,
                'requires_permission_check': True, 'requires_window_or_template': True,
                'requires_review': True,
                'automatic_send_enabled': False}
        active = await self.db.conversation_tasks.find_one({'_id': key + ':next'})
        if active and active.get('state') == 'sending':
            # A claimed send is never made retryable by an incoming message.
            await self.db.conversation_tasks.update_one({'_id': key + ':next'}, {'$set': {'next_plan': task}})
            return
        # A new inbound cancels previous approval; one pending conversation per contact.
        await self.db.conversation_tasks.update_one({'_id': key + ':next'}, {'$set': task}, upsert=True)

    async def context(self, phone):
        profile = await self.db.contacts.find_one({'_id': contact_key(phone)})
        if not profile:
            return ''
        facts = {k: v['value'] for k, v in profile.get('facts', {}).items()}
        return json.dumps({'contact_no': profile['contact_no'], 'reported_facts': facts},
                          ensure_ascii=False)[:2200]

    async def record_outbound(self, phone, outbound_id, text):
        profile = await self.ensure(phone)
        now = datetime.now(timezone.utc)
        await self.db.contact_events.update_one({'_id': outbound_id}, {'$setOnInsert': {
            'contact_key': profile['_id'], 'contact_no': profile['contact_no'],
            'direction': 'outbound', 'text': text[:4000], 'created_at': now,
            'expires_at': now + timedelta(days=90), 'delivery': 'accepted'}}, upsert=True)
