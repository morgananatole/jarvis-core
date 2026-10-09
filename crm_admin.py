"""Private CRM API. All customer data requires a bearer credential."""
import base64
import csv
import httpx
import hmac
import io
import os
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse
from contact_memory import ContactMemory
from human_service import HumanService
from device_access import DeviceAccess
from import_google_contacts import rows_to_contacts


def authorize(request: Request):
    secret = os.getenv('CRM_ADMIN_TOKEN', '')
    if len(secret) < 32:
        raise HTTPException(503, 'Private CRM credential not configured')
    token = request.headers.get('authorization', '')
    if not hmac.compare_digest(token, 'Bearer ' + secret):
        raise HTTPException(401, 'Authentication required')


def router(database, conversation):
    async def access(request: Request):
        if request.headers.get('x-jarvis-device'):
            await DeviceAccess(db()).verify(request)
        else:
            authorize(request)
    api = APIRouter(prefix='/crm', dependencies=[Depends(access)])

    def db():
        value = database()
        if value is None:
            raise HTTPException(503, 'Database unavailable')
        return value

    @api.post('/devices/code', dependencies=[Depends(authorize)])
    async def device_code(request: Request):
        return await DeviceAccess(db()).issue((await request.json()).get('label'))

    @api.get('/devices', dependencies=[Depends(authorize)])
    async def devices():
        return jsonable_encoder(await db().authorized_devices.find({}, {'public_key': 0}).limit(200).to_list(200))

    @api.post('/devices/{identity}/revoke', dependencies=[Depends(authorize)])
    async def revoke(identity: str):
        result = await db().authorized_devices.update_one({'_id': identity}, {'$set': {'revoked': True}})
        if not result.matched_count: raise HTTPException(404, 'device_not_found')
        return {'revoked': True}

    @api.get('/institution')
    async def institution():
        return jsonable_encoder(await db().institutional_knowledge.find_one({'_id': 'nova_vida'}))

    @api.get('/contacts')
    async def contacts(page: int = 0):
        rows = await db().contacts.find({}, {'phone': 0}).sort('contact_no', 1).skip(max(0, min(page, 10000)) * 200).limit(200).to_list(200)
        return jsonable_encoder(rows)

    @api.get('/tasks')
    async def tasks():
        return jsonable_encoder(await db().conversation_tasks.find({}).sort('due_at', 1).limit(200).to_list(200))

    @api.get('/contacts/{number}')
    async def detail(number: int):
        profile = await db().contacts.find_one({'contact_no': number})
        if not profile:
            raise HTTPException(404, 'Contact not found')
        events = await db().contact_events.find({'contact_key': profile['_id']}).sort('created_at', -1).limit(30).to_list(30)
        return jsonable_encoder({'profile': profile, 'events': events})

    @api.post('/tasks/{number}/review')
    async def review(number: int, request: Request):
        body = await request.json()
        if body.get('state') not in {'approved', 'held'}:
            raise HTTPException(400, 'Choose approved or held')
        profile = await db().contacts.find_one({'contact_no': number})
        if not profile:
            raise HTTPException(404, 'Contact not found')
        changes = {'state': body['state'], 'reviewed_at': datetime.now(timezone.utc)}
        if body.get('due_at'):
            try:
                due = datetime.fromisoformat(body['due_at'])
                if due.tzinfo is None:
                    raise ValueError()
                changes['due_at'] = due
            except (ValueError, TypeError):
                raise HTTPException(400, 'due_at requires ISO 8601 timezone')
        if body.get('purpose'):
            changes['purpose'] = str(body['purpose'])[:500]
        result = await db().conversation_tasks.update_one(
            {'_id': profile['_id'] + ':next', 'state': {'$in': ['planned', 'blocked', 'held', 'approved']}}, {'$set': changes})
        if not result.matched_count:
            raise HTTPException(409, 'Task unavailable or already processing')
        return {'reviewed': True}

    @api.post('/tasks/{number}/run')
    async def run(number: int):
        profile = await db().contacts.find_one({'contact_no': number})
        if not profile:
            raise HTTPException(404, 'Contact not found')
        return await conversation(db()).run_one(profile['_id'] + ':next')

    @api.get('/human')
    async def human_queue():
        rows = await db().human_requests.find({'state': {'$in': ['waiting', 'active']}}).sort(
            [('priority', -1), ('updated_at', -1)]).limit(200).to_list(200)
        result = []
        for row in rows:
            profile = await db().contacts.find_one({'_id': row['_id']})
            row['contact_name'] = (profile or {}).get('facts', {}).get('contact_name', {}).get('value', '')
            result.append(row)
        return jsonable_encoder(result)

    @api.post('/contacts/{number}/mode')
    async def mode(number: int, request: Request):
        body = await request.json()
        if body.get('mode') not in {'human', 'jarvis'}:
            raise HTTPException(400, 'Choose human or jarvis')
        service = conversation(db())
        try:
            return await HumanService(db(), service.send, service.tester).mode(number, body['mode'] == 'human')
        except ValueError as error:
            raise HTTPException(404, str(error))

    @api.post('/contacts/{number}/reply')
    async def operator_reply(number: int, request: Request):
        body = await request.json()
        service = conversation(db())
        try:
            return await HumanService(db(), service.send, service.tester).reply(
                number, body.get('text'), request.headers.get('idempotency-key'))
        except ValueError as error:
            raise HTTPException(409, str(error))

    @api.post('/import/google')
    async def import_google(request: Request):
        raw = await request.body()
        if len(raw) > 8 * 1024 * 1024:
            raise HTTPException(413, 'CSV too large')
        try:
            rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        except (UnicodeError, csv.Error):
            raise HTTPException(400, 'Invalid Google CSV')
        memory, count, seen = ContactMemory(db()), 0, set()
        for phone, name in rows_to_contacts(rows):
            if phone in seen:
                continue
            seen.add(phone)
            profile = await memory.ensure(phone)
            if name and not profile.get('facts', {}).get('contact_name'):
                await db().contacts.update_one({'_id': profile['_id']}, {'$set': {
                    'facts.contact_name': {'value': name, 'status': 'address_book',
                    'source': 'google_contacts_csv', 'reported_at': datetime.now(timezone.utc)}}})
            await memory.plan(profile['_id'], 'google_contacts_import')
            count += 1
        return {'rows': len(rows), 'unique_phone_entries': count, 'messages_sent': 0}

    @api.post('/media/{key}/upload')
    async def upload(key: str, request: Request):
        if not re.fullmatch(r'[a-z0-9_]{1,60}', key):
            raise HTTPException(400, 'Invalid catalog key')
        raw = await request.body()
        if len(raw) > 8 * 1024 * 1024:
            raise HTTPException(413, 'Photo too large')
        import json
        try:
            body = json.loads(raw)
            image = base64.b64decode(body['image'], validate=True)
        except (ValueError, KeyError, TypeError):
            raise HTTPException(400, 'Invalid photo')
        mime = 'image/jpeg' if image.startswith(b'\xff\xd8\xff') else 'image/png' if image.startswith(b'\x89PNG\r\n\x1a\n') else None
        if not mime or len(image) > 5 * 1024 * 1024:
            raise HTTPException(400, 'Use JPEG or PNG up to 5 MB')
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post('https://graph.facebook.com/' + os.environ['META_GRAPH_VERSION'] + '/' +
                os.environ['WHATSAPP_PHONE_NUMBER_ID'] + '/media', headers={
                'Authorization': 'Bearer ' + os.environ['WHATSAPP_ACCESS_TOKEN']},
                data={'messaging_product': 'whatsapp'}, files={'file': ('photo.jpg' if mime == 'image/jpeg' else 'photo.png', image, mime)})
            if response.is_error:
                raise HTTPException(502, 'Meta photo upload rejected')
            media_id = response.json()['id']
        await db().media_catalog.update_one({'_id': key}, {'$set': {'media_id': media_id,
            'caption': str(body.get('caption', ''))[:1000], 'theme': str(body.get('theme', ''))[:120],
            'approved': body.get('approved') is True, 'updated_at': datetime.now(timezone.utc)}}, upsert=True)
        return {'saved': True}

    @api.post('/media/{key}/send/{number}')
    async def photo(key: str, number: int):
        from media_service import send_photo
        profile = await db().contacts.find_one({'contact_no': number})
        if not profile:
            raise HTTPException(404, 'Contact not found')
        try:
            return {'state': 'accepted', 'id': await send_photo(db(), profile['phone'], key)}
        except ValueError as error:
            raise HTTPException(409, str(error))
        except Exception:
            raise HTTPException(502, 'Photo acceptance uncertain; inspect delivery before retrying')

    @api.get('/media')
    async def media():
        return jsonable_encoder(await db().media_catalog.find({}).limit(200).to_list(200))

    @api.put('/media/{key}')
    async def catalog(key: str, request: Request):
        body = await request.json()
        if not re.fullmatch(r'[a-z0-9_]{1,60}', key) or not re.fullmatch(r'[0-9]{5,30}', str(body.get('media_id', ''))):
            raise HTTPException(400, 'Use catalog key and a Meta-uploaded media ID')
        asset = {'media_id': str(body['media_id']), 'caption': str(body.get('caption', ''))[:1000],
                 'theme': str(body.get('theme', ''))[:120], 'approved': body.get('approved') is True,
                 'updated_at': datetime.now(timezone.utc)}
        await db().media_catalog.update_one({'_id': key}, {'$set': asset}, upsert=True)
        return {'saved': True}

    return api


def panel():
    from pathlib import Path
    return HTMLResponse(Path(__file__).with_name('panel.html').read_text(encoding='utf-8'), headers={
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer',
        'Content-Security-Policy': "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"})


def enrollment_router(database):
    api = APIRouter()
    @api.post('/device/enroll')
    async def enroll(request: Request):
        raw = await request.body()
        if len(raw) > 2048: raise HTTPException(413, 'Payload too large')
        value = database()
        if value is None: raise HTTPException(503, 'Database unavailable')
        body = await request.json()
        if not isinstance(body, dict): raise HTTPException(400, 'Invalid enrollment')
        return await DeviceAccess(value).enroll(body.get('code'), body.get('public_key'))
    return api
