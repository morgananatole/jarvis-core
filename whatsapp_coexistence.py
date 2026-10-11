"""Text echoes from the Business app; never calls an AI or sends a message.

Opt-in only. Requires official Meta coexistence and smb_message_echoes delivery.
Uses the existing single-instance conversation lock and private event retention.
"""
import math
import re
from datetime import datetime, timedelta, timezone
from contact_memory import ContactMemory, canonical_phone, contact_key
from human_service import conversation_lock


def text_echo(message, metadata):
    if not isinstance(message, dict): raise ValueError('invalid_app_echo')
    # Media, edits, revokes and history require their own synchronization rules.
    if message.get('type') != 'text': return None
    identity, recipient, sender = message.get('id'), message.get('to'), message.get('from')
    if not isinstance(identity, str) or not 1 <= len(identity) <= 512:
        raise ValueError('invalid_app_echo_id')
    if not isinstance(recipient, str) or not re.fullmatch(r'\+?[0-9]{8,15}', recipient):
        raise ValueError('invalid_app_echo_destination')
    if not isinstance(sender, str) or canonical_phone(sender) != canonical_phone(metadata.get('display_phone_number', '')):
        raise ValueError('invalid_app_echo_sender')
    text = message.get('text')
    if not isinstance(text, dict) or not isinstance(text.get('body'), str) or not text['body'] or len(text['body']) > 4000:
        raise ValueError('invalid_app_echo_text')
    stamp = float(message['timestamp'])
    if not math.isfinite(stamp): raise ValueError('invalid_app_echo_time')
    sent_at = datetime.fromtimestamp(stamp, timezone.utc)
    if sent_at > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise ValueError('invalid_app_echo_time')
    return {'id': identity, 'phone': canonical_phone(recipient), 'text': text['body'], 'sent_at': sent_at}


async def record_text_echo(db, echo):
    now = datetime.now(timezone.utc)
    async with conversation_lock(contact_key(echo['phone'])):
        profile = await ContactMemory(db).ensure(echo['phone'])
        event = await db.contact_events.find_one({'_id': echo['id']})
        if event:
            if event.get('contact_key') != profile['_id'] or event.get('source') != 'whatsapp_business_app':
                raise ValueError('app_echo_id_collision')
            if event.get('app_sync_applied'): return
        await db.contact_events.update_one({'_id': echo['id']}, {'$setOnInsert': {
            'contact_key': profile['_id'], 'contact_no': profile['contact_no'],
            'direction': 'outbound', 'source': 'whatsapp_business_app', 'operator': True,
            'text': echo['text'], 'created_at': echo['sent_at'],
            'expires_at': now + timedelta(days=90)}}, upsert=True)
        # Delayed or old deliveries must not undo an explicit owner resumption.
        control = profile.get('human_control_at')
        if control and control.tzinfo is None: control = control.replace(tzinfo=timezone.utc)
        last_app = profile.get('last_app_reply_at')
        if last_app and last_app.tzinfo is None: last_app = last_app.replace(tzinfo=timezone.utc)
        current = (echo['sent_at'] >= now - timedelta(hours=24)
            and (not control or echo['sent_at'] > control)
            and (not last_app or echo['sent_at'] >= last_app))
        if current:
            await db.contacts.update_one({'_id': profile['_id']}, {'$set': {
                'human_mode': True, 'human_since': profile.get('human_since') or echo['sent_at'],
                'last_app_reply_at': echo['sent_at'], 'ai_waiting_assist': False},
                '$inc': {'automation_epoch': 1}})
            await db.human_requests.update_one({'_id': profile['_id']}, {'$set': {
                'contact_no': profile['contact_no'], 'state': 'active', 'unread': False,
                'pending_since': None, 'wait_notice_state': 'answered',
                'last_operator_reply_at': echo['sent_at'], 'updated_at': now},
                '$setOnInsert': {'created_at': now, 'reason': 'business_app_reply'}}, upsert=True)
            await db.conversation_tasks.update_one({'_id': profile['_id'] + ':next',
                'state': {'$in': ['approved', 'planned', 'blocked']}}, {'$set': {
                    'state': 'held', 'reason': 'human_takeover'}})
        # Mark only after all effects succeed, so failed deliveries can be retried.
        await db.contact_events.update_one({'_id': echo['id']}, {'$set': {'app_sync_applied': True}})
