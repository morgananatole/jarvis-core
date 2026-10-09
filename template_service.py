"""Meta-approved re-engagement template, disabled until a send budget is configured."""
import os
from datetime import datetime, timedelta, timezone
import httpx
from contact_memory import ContactMemory


async def send_template(db, profile):
    if os.getenv('WHATSAPP_TEMPLATE_SEND_ENABLED', 'false') != 'true':
        raise ValueError('template_send_disabled')
    cap = min(1000, max(0, int(os.getenv('WHATSAPP_TEMPLATE_MAX_PER_DAY', '0'))))
    if not cap:
        raise ValueError('template_budget_required')
    name = os.getenv('WHATSAPP_FOLLOWUP_TEMPLATE', 'nova_vida_retomada_conversa')
    language = 'pt_BR'
    root = 'https://graph.facebook.com/' + os.environ['META_GRAPH_VERSION'] + '/'
    headers = {'Authorization': 'Bearer ' + os.environ['WHATSAPP_ACCESS_TOKEN']}
    async with httpx.AsyncClient(timeout=15) as client:
        check = await client.get(root + os.environ['WHATSAPP_WABA_ID'] + '/message_templates',
            headers=headers, params={'name': name, 'fields': 'name,status,language', 'limit': 100})
        check.raise_for_status()
        if not any(t.get('name') == name and t.get('status') == 'APPROVED' and
                   t.get('language') == language for t in check.json().get('data', [])):
            raise ValueError('template_not_approved')
        now = datetime.now(timezone.utc)
        key = 'meta-template:' + now.strftime('%Y-%m-%d')
        try:
            await db.ai_budgets.update_one({'_id': key}, {'$setOnInsert': {'used': 0,
                'expires_at': now + timedelta(days=2)}}, upsert=True)
        except Exception:
            if not await db.ai_budgets.find_one({'_id': key}):
                raise
        reserved = await db.ai_budgets.find_one_and_update({'_id': key, 'used': {'$lt': cap}},
            {'$inc': {'used': 1}}, return_document=True)
        if not reserved:
            raise ValueError('template_daily_cap_reached')
        address = profile.get('facts', {}).get('contact_name', {}).get('value') or 'tudo bem'
        response = await client.post(root + os.environ['WHATSAPP_PHONE_NUMBER_ID'] + '/messages',
            headers=headers, json={'messaging_product': 'whatsapp', 'to': profile['phone'],
            'type': 'template', 'template': {'name': name, 'language': {'code': language},
            'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': address[:150]}]}]}})
        response.raise_for_status()
        mid = response.json()['messages'][0]['id']
    await ContactMemory(db).record_outbound(profile['phone'], mid, '[Modelo de retomada: ' + name + ']')
    return mid
