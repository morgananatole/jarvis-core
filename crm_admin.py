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
from import_google_contacts import rows_to_contacts


def authorize(request: Request):
    secret = os.getenv('CRM_ADMIN_TOKEN', '')
    if len(secret) < 32:
        raise HTTPException(503, 'Private CRM credential not configured')
    token = request.headers.get('authorization', '')
    if not hmac.compare_digest(token, 'Bearer ' + secret):
        raise HTTPException(401, 'Authentication required')


def router(database, conversation):
    api = APIRouter(prefix='/crm', dependencies=[Depends(authorize)])

    def db():
        value = database()
        if value is None:
            raise HTTPException(503, 'Database unavailable')
        return value

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
    # Credential is kept only in JavaScript memory, never in URLs or browser storage.
    return HTMLResponse('''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>JARVIS · Conversas</title><style>body{font:16px system-ui;max-width:1000px;margin:32px auto;padding:16px;background:#f4f7f8;color:#182d35}button,input{padding:10px;margin:5px}article{background:white;padding:16px;margin:12px 0;border-radius:12px}pre{white-space:pre-wrap}h1{color:#14665d}</style><h1>JARVIS · Conversas futuras</h1><p>Retome cada vínculo com objetivo e contexto. Aprovar não dispensa autorização do contato nem as regras do WhatsApp.</p><input id="credential" type="password" autocomplete="off" placeholder="Credencial privada do CRM"><button id="connect">Entrar</button><button id="exit">Sair</button><p id="status"></p><section id="workspace" hidden><button id="refresh">Atualizar</button><label>Importar Google CSV <input id="csv" type="file" accept=".csv"></label><h2>Conversas</h2><div id="tasks"></div><h2>Fotos autorizadas</h2><input id="photoKey" placeholder="Identificador: estrutura_natal"><input id="photoTheme" placeholder="O que esta foto mostra"><input id="photoCaption" placeholder="Legenda"><input id="photoFile" type="file" accept="image/jpeg,image/png"><label><input id="photoApproved" type="checkbox">Foto autorizada para atendimento</label><button id="uploadPhoto">Cadastrar foto</button><h2>Contatos</h2><button id="previous">Anterior</button><button id="next">Próxima página</button><div id="contacts"></div></section><script>
let token='',page=0;const el=id=>document.getElementById(id);async function api(path,method='GET',body){let r=await fetch('/crm/'+path,{method,headers:{Authorization:'Bearer '+token,...(body&&typeof body==='string'?{'Content-Type':'application/json'}:{})},body});if(!r.ok)throw Error('Não foi possível concluir ('+r.status+').');return r.json()};function text(parent,s){let p=document.createElement('p');p.textContent=s;parent.append(p)}function button(parent,s,action){let b=document.createElement('button');b.textContent=s;b.onclick=()=>action().catch(e=>el('status').textContent=e.message);parent.append(b)}async function load(){let [contacts,tasks]=await Promise.all([api('contacts?page='+page),api('tasks')]);el('contacts').replaceChildren();el('tasks').replaceChildren();for(let c of contacts){let a=document.createElement('article');text(a,'#'+c.contact_no+' · '+(c.facts?.contact_name?.value||'Nome ainda não informado'));button(a,'Ver histórico',async()=>{let d=await api('contacts/'+c.contact_no);let p=document.createElement('pre');p.textContent=JSON.stringify(d,null,2);a.append(p)});el('contacts').append(a)}for(let t of tasks){let a=document.createElement('article');text(a,'#'+t.contact_no+' · '+t.state+' · '+t.purpose);text(a,t.due_at?new Date(t.due_at).toLocaleString('pt-BR'):'Sem data');button(a,'Aprovar',async()=>{await api('tasks/'+t.contact_no+'/review','POST',JSON.stringify({state:'approved'}));await load()});button(a,'Remarcar',async()=>{let purpose=prompt('Objetivo da conversa',t.purpose);let due=prompt('Data e hora com fuso (ex.: 2026-10-12T10:00:00-03:00)',t.due_at||'');if(purpose&&due){await api('tasks/'+t.contact_no+'/review','POST',JSON.stringify({state:'held',purpose,due_at:due}));await load()}});button(a,'Suspender',async()=>{await api('tasks/'+t.contact_no+'/review','POST',JSON.stringify({state:'held'}));await load()});button(a,'Executar retorno aprovado',async()=>{let r=await api('tasks/'+t.contact_no+'/run','POST');el('status').textContent=JSON.stringify(r);await load()});el('tasks').append(a)}el('workspace').hidden=false}el('connect').onclick=async()=>{token=el('credential').value;el('credential').value='';try{await load();el('status').textContent='Acesso privado ativo';}catch(e){token='';el('status').textContent=e.message}};el('exit').onclick=()=>{token='';el('workspace').hidden=true;el('contacts').replaceChildren();el('tasks').replaceChildren();el('status').textContent='Sessão encerrada'};el('refresh').onclick=()=>load().catch(e=>el('status').textContent=e.message);el('previous').onclick=()=>{page=Math.max(0,page-1);load().catch(e=>el('status').textContent=e.message)};el('next').onclick=()=>{page++;load().catch(e=>el('status').textContent=e.message)};el('uploadPhoto').onclick=async()=>{try{let f=el('photoFile').files[0];if(!f||f.size>5242880)throw Error('Escolha JPEG ou PNG até 5 MB');let image=await new Promise((resolve,reject)=>{let r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=reject;r.readAsDataURL(f)});await api('media/'+encodeURIComponent(el('photoKey').value)+'/upload','POST',JSON.stringify({image,theme:el('photoTheme').value,caption:el('photoCaption').value,approved:el('photoApproved').checked}));el('status').textContent='Foto cadastrada no catálogo privado';el('photoFile').value=''}catch(e){el('status').textContent=e.message}};el('csv').onchange=async()=>{try{let f=el('csv').files[0];if(f.size>8388608)throw Error('CSV excede 8 MB');let r=await api('import/google','POST',await f.arrayBuffer());el('status').textContent=JSON.stringify(r);await load()}catch(e){el('status').textContent=e.message}finally{el('csv').value=''}};
</script></html>''', headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer', 'Content-Security-Policy': "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"})
