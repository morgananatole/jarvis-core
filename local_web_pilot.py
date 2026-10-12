"""Private stdio bridge for a local, isolated WhatsApp Web pilot.

Never starts the production lifespan, Meta transport or scheduled workers.
"""
import asyncio
import json
import os
import re
import sys
import time


def configuration():
    database = os.getenv('PULSE_PILOT_DATABASE', '')
    if not re.fullmatch(r'pulse_web_pilot_[a-z0-9_]{1,40}', database):
        raise ValueError('pilot_database_required')
    uri = os.getenv('PULSE_PILOT_MONGODB_URI', '')
    secret = os.getenv('PULSE_PILOT_ID_SECRET', '')
    mode = os.getenv('PULSE_PILOT_REPLY_MODE', 'test')
    if not uri or len(secret) < 32 or mode not in {'test', 'hybrid'}:
        raise ValueError('pilot_configuration_required')
    # These changes affect this child process only, never the Render environment.
    os.environ['CRM_ID_SECRET'] = secret
    os.environ['META_APP_SECRET'] = secret
    os.environ['JARVIS_REPLY_MODE'] = mode
    os.environ['AI_PAID_FALLBACK_ENABLED'] = 'false'
    os.environ['AI_PAID_MAX_CALLS_PER_DAY'] = '0'
    os.environ['MEDIA_AI_ENABLED'] = 'false'
    if mode == 'hybrid' and not os.getenv('GROQ_API_KEY'):
        raise ValueError('free_provider_required')
    if mode == 'hybrid' and not os.getenv('JARVIS_INSTRUCTIONS'):
        raise ValueError('reviewed_instructions_required')
    return uri, database


async def prepare(db, event, memory, generate, takeover):
    phone, identity, text = event['phone'], event['id'], event['text']
    if (not isinstance(phone, str) or not re.fullmatch(r'[0-9]{8,15}', phone)
            or not isinstance(identity, str) or not re.fullmatch(r'web:[a-f0-9]{64}', identity)
            or not isinstance(text, str) or not 0 < len(text) <= 6000):
        raise ValueError('invalid_event')
    profile = await memory.record_inbound(phone, identity, text, time.time())
    reason = takeover(text)
    if reason:
        await db.contacts.update_one({'_id': profile['_id']}, {'$set': {'human_mode': True}})
    if reason or any(profile.get(k) for k in ('human_mode', 'human_only', 'do_not_contact')):
        return {'state': 'human_or_suppressed', 'reply': None}
    reply = await generate(text, phone, identity)
    if not isinstance(reply, str) or not reply.strip():
        raise ValueError('empty_reply')
    return {'state': 'prepared', 'reply': reply[:4000]}


async def run():
    uri, name = configuration()
    from motor.motor_asyncio import AsyncIOMotorClient
    from contact_memory import ContactMemory
    from human_service import takeover_reason
    from ai_router import ReplyRouter
    import main
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000, tz_aware=True)
    try:
        db = client[name]
        await db.command('ping')
        memory = ContactMemory(db)
        await memory.initialize()
        if os.environ['JARVIS_REPLY_MODE'] == 'hybrid':
            await ReplyRouter(db).initialize()
        main.inbox = db.inbox
        print(json.dumps({'state': 'ready'}), flush=True)
        while line := await asyncio.to_thread(sys.stdin.readline):
            try:
                event = json.loads(line)
                if event.get('action') == 'prepare':
                    result = await prepare(db, event, memory, main.generate_reply, takeover_reason)
                elif event.get('action') == 'receipt':
                    await memory.record_outbound(event['phone'], event['id'], event['text'])
                    result = {'state': 'recorded'}
                else:
                    raise ValueError('invalid_action')
                print(json.dumps(result, ensure_ascii=False), flush=True)
            except Exception:
                # No customer text, token, URI or exception payload in diagnostics.
                print(json.dumps({'state': 'review_required', 'reply': None}), flush=True)
    finally:
        client.close()


if __name__ == '__main__':
    try:
        asyncio.run(run())
    except Exception:
        print(json.dumps({'state': 'configuration_or_storage_unavailable'}), flush=True)
        sys.exit(1)
