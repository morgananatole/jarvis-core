"""Recover only pre-send work; ambiguous send acceptance always needs review."""
from datetime import datetime, timedelta, timezone

async def recover(db, process):
    now = datetime.now(timezone.utc)
    # A token comparison keeps an old process from taking over a newer attempt.
    rows = await db.inbox.find({'state': {'$in': ['processing', 'sending']},
        'lease_until': {'$lt': now}}).limit(20).to_list(20)
    for row in rows:
        fresh = row.get('message') and float(row['message'].get('timestamp', 0)) > now.timestamp() - 23 * 3600
        if row['state'] == 'processing' and fresh:
            await process(row['message'])
        else:
            await db.inbox.update_one({'_id': row['_id'], 'state': row['state'], 'attempt': row.get('attempt')},
                {'$set': {'state': 'review_required', 'reason': 'interrupted_send_acceptance_unknown' if row['state'] == 'sending' else 'recovery_window_expired'}})
    tasks = await db.conversation_tasks.find({'state': {'$in': ['checking', 'sending']},
        'claimed_at': {'$lt': now - timedelta(minutes=3)}}).limit(20).to_list(20)
    for task in tasks:
        state = 'approved' if task['state'] == 'checking' else 'review_required'
        await db.conversation_tasks.update_one({'_id': task['_id'], 'state': task['state'], 'attempt': task.get('attempt')},
            {'$set': {'state': state, 'reason': 'recovered_before_send' if state == 'approved' else 'interrupted_send_acceptance_unknown'}})
