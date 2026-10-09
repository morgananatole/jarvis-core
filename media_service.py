"""Only approved Meta media IDs can be sent; never fetch model-supplied URLs."""
import os
from datetime import datetime, timedelta, timezone
import httpx


def image_payload(phone, asset):
    if not asset or asset.get('approved') is not True or not str(asset.get('media_id', '')).isdigit():
        raise ValueError('approved_photo_required')
    return {'messaging_product': 'whatsapp', 'to': phone, 'type': 'image',
            'image': {'id': asset['media_id'], 'caption': asset.get('caption', '')[:1000]}}


async def send_photo(db, phone, key):
    from contact_memory import contact_key, ContactMemory
    profile = await db.contacts.find_one({'_id': contact_key(phone)})
    last = profile.get('last_inbound_at') if profile else None
    if last and last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    if not last or datetime.now(timezone.utc) - last > timedelta(hours=23):
        raise ValueError('active_customer_window_required')
    if os.getenv('JARVIS_REPLY_MODE') == 'test' or os.getenv('AI_ALLOWED_TEST_ONLY', 'true') == 'true':
        from main import authorized_test_sender
        if not authorized_test_sender(phone):
            raise ValueError('test_recipient_only')
    asset = await db.media_catalog.find_one({'_id': key})
    payload = image_payload(phone, asset)
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post('https://graph.facebook.com/' + os.environ['META_GRAPH_VERSION'] + '/' +
            os.environ['WHATSAPP_PHONE_NUMBER_ID'] + '/messages', headers={
            'Authorization': 'Bearer ' + os.environ['WHATSAPP_ACCESS_TOKEN']}, json=payload)
        response.raise_for_status()
        mid = response.json()['messages'][0]['id']
    await ContactMemory(db).record_outbound(phone, mid, '[Foto: ' + key + '] ' + asset.get('caption', ''))
    return mid
