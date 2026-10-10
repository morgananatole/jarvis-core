"""Pix renewal: server-priced orders, provider verification and atomic license grants."""
import hashlib
import hmac
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from pymongo.errors import DuplicateKeyError
from commercial_licenses import business


def now(): return datetime.now(timezone.utc)


def configured():
    return all(os.getenv(k) for k in ('MP_ACCESS_TOKEN','MP_WEBHOOK_SECRET','MP_COLLECTOR_ID','BILLING_PUBLIC_BASE_URL')) and os.getenv('BILLING_MP_LIVE_MODE','true') in ('true','false') and os.getenv('BILLING_PUBLIC_BASE_URL','').startswith('https://')


def require_config():
    if not configured(): raise HTTPException(503,'pix_provider_not_connected')


def signature(request):
    require_config()
    payment=request.query_params.get('data.id','')
    request_id=request.headers.get('x-request-id','')
    header=request.headers.get('x-signature','')
    if len(header)>256 or not re.fullmatch(r'[0-9]{1,30}',payment) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',request_id):
        raise HTTPException(401,'invalid_payment_signature')
    try:
        parts=dict(p.strip().split('=',1) for p in header.split(','))
        stamp,digest=parts['ts'],parts['v1']
        if not re.fullmatch(r'[0-9]{10}|[0-9]{13}',stamp) or not re.fullmatch(r'[0-9a-f]{64}',digest):raise ValueError()
        seconds=int(stamp)/(1000 if len(stamp)==13 else 1)
        if abs(time.time()-seconds)>300:raise ValueError()
        manifest=f'id:{payment};request-id:{request_id};ts:{stamp};'
        expected=hmac.new(os.environ['MP_WEBHOOK_SECRET'].encode(),manifest.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,digest):raise ValueError()
    except (ValueError,KeyError):raise HTTPException(401,'invalid_payment_signature') from None
    return payment


class MercadoPago:
    async def call(self,method,path,body=None,key=None):
        require_config()
        headers={'Authorization':'Bearer '+os.environ['MP_ACCESS_TOKEN']}
        if key:headers['X-Idempotency-Key']=key
        try:
            async with httpx.AsyncClient(timeout=15,follow_redirects=False) as client:
                response=await client.request(method,'https://api.mercadopago.com'+path,headers=headers,json=body)
                if response.is_error or response.is_redirect:raise ValueError()
                return response.json()
        except (httpx.HTTPError,ValueError):raise HTTPException(502,'pix_provider_unavailable') from None
    async def create(self,body,key):return await self.call('POST','/v1/payments',body,key)
    async def get(self,identity):
        if not re.fullmatch(r'[0-9]{1,30}',str(identity)):raise HTTPException(400,'invalid_payment_id')
        return await self.call('GET','/v1/payments/'+str(identity))


class PixBilling:
    def __init__(self,db,provider=None):self.db,self.provider=db,provider or MercadoPago()
    async def license(self,identity):
        if not isinstance(identity,str) or not re.fullmatch(r'[0-9a-f]{32}',identity):raise HTTPException(400,'invalid_license_id')
        record=await self.db.commercial_licenses.find_one({'_id':identity,'business_id':business(),'revoked':False})
        if not record:raise HTTPException(403,'license_revoked_or_missing')
        return record
    async def price(self,identity,body):
        record=await self.license(identity)
        if record['kind']!='subscription':raise HTTPException(409,'permanent_license_has_no_charge')
        if not isinstance(body,dict):raise HTTPException(400,'invalid_billing_price')
        cents,days=body.get('amount_cents'),body.get('period_days')
        if type(cents) is not int or not 100<=cents<=10000000 or type(days) is not int or not 1<=days<=366:
            raise HTTPException(400,'invalid_billing_price')
        await self.db.commercial_licenses.update_one({'_id':identity,'business_id':business()},
            {'$set':{'billing_price':{'amount_cents':cents,'period_days':days},'billing_price_updated_at':now()}})
        return {'saved':True}
    def public(self,order):
        return {k:order.get(k) for k in ('_id','status','amount_cents','period_days','expires_at','qr_code','qr_code_base64','granted_until')}
    async def account(self,identity):
        lic=await self.license(identity)
        order=await self.db.billing_orders.find_one({'_id':lic.get('billing_open_order'),'business_id':business()}) if lic.get('billing_open_order') else None
        return {'configured':configured(),'kind':lic['kind'],'expires_at':lic['expires_at'],
            'price':lic.get('billing_price'),'order':self.public(order) if order else None}
    async def checkout(self,identity,body):
        require_config()
        if not isinstance(body,dict) or set(body)-{'email','cpf'}:raise HTTPException(400,'invalid_payer')
        email,cpf=body.get('email',''),body.get('cpf','')
        if not isinstance(email,str) or not re.fullmatch(r'[^\s@]{1,100}@[^\s@]{1,100}\.[^\s@]{2,30}',email):raise HTTPException(400,'invalid_payer')
        if not isinstance(cpf,str) or not re.fullmatch(r'[0-9]{11}',cpf):raise HTTPException(400,'invalid_payer')
        # Payer details travel to the provider; the app retains no CPF/email in orders.
        for _ in range(3):
            lic=await self.license(identity)
            if lic['kind']!='subscription':raise HTTPException(409,'permanent_license_has_no_charge')
            price=lic.get('billing_price')
            if not price:raise HTTPException(409,'subscription_price_not_defined')
            old=lic.get('billing_open_order')
            order=await self.db.billing_orders.find_one({'_id':old,'business_id':business()}) if old else None
            if order and order['status'] in ('created','creating','create_failed','pending','in_process') and order['expires_at']>now():break
            order={'_id':secrets.token_hex(16),'business_id':business(),'license_id':identity,'status':'created',
                **price,'created_at':now(),'expires_at':now()+timedelta(hours=1)}
            await self.db.billing_orders.insert_one(order)
            query={'_id':identity,'business_id':business(),'revoked':False,'billing_open_order':old} if old else {
                '_id':identity,'business_id':business(),'revoked':False,'billing_open_order':{'$exists':False}}
            result=await self.db.commercial_licenses.update_one(query,{'$set':{'billing_open_order':order['_id']}})
            if result.matched_count:break
        else:raise HTTPException(409,'billing_busy')
        if order.get('payment_id'):return self.public(order)
        payer_hash=hashlib.sha256((email+'\n'+cpf).encode()).hexdigest()
        if order.get('payer_hash') and order['payer_hash']!=payer_hash:
            raise HTTPException(409,'retry_with_original_payer')
        clock=now()
        claim=await self.db.billing_orders.find_one_and_update({'_id':order['_id'],'$or':[
            {'status':{'$in':['created','create_failed']}},{'status':'creating','lease_until':{'$lt':clock}}]},
            {'$set':{'status':'creating','lease_until':clock+timedelta(seconds=45),'payer_hash':payer_hash}},return_document=True)
        if not claim:raise HTTPException(409,'billing_busy')
        provider_body={'transaction_amount':claim['amount_cents']/100,'description':'Renovação JARVIS PULSE',
            'payment_method_id':'pix','external_reference':claim['_id'],
            'date_of_expiration':claim['expires_at'].isoformat(timespec='milliseconds'),
            'notification_url':os.environ['BILLING_PUBLIC_BASE_URL'].rstrip('/')+'/billing/webhook/mercadopago',
            'payer':{'email':email,'identification':{'type':'CPF','number':cpf}}}
        try:
            data=await self.provider.create(provider_body,claim['_id'])
            payment=str(data['id'])
            if not re.fullmatch(r'[0-9]{1,30}',payment):raise ValueError()
            qr=data.get('point_of_interaction',{}).get('transaction_data',{})
            image=qr.get('qr_code_base64','');code=qr.get('qr_code','')
            if not isinstance(code,str) or len(code)>4000 or not isinstance(image,str) or len(image)>200000 or (image and not re.fullmatch(r'[A-Za-z0-9+/=]+',image)):raise ValueError()
            await self.db.billing_orders.update_one({'_id':claim['_id']},{'$set':{
                'payment_id':payment,'status':'pending','qr_code':code,'qr_code_base64':image}})
        except Exception:
            await self.db.billing_orders.update_one({'_id':claim['_id'],'status':'creating'},{'$set':{'status':'create_failed'}})
            raise HTTPException(502,'pix_creation_uncertain_retry_same_order') from None
        return self.public(await self.db.billing_orders.find_one({'_id':claim['_id']}))
    async def reconcile(self,order_id):
        order=await self.db.billing_orders.find_one({'_id':order_id,'business_id':business()})
        if not order or not order.get('payment_id'):raise HTTPException(404,'payment_not_available')
        data=await self.provider.get(order['payment_id'])
        try:
            amount=Decimal(str(data['transaction_amount']))*100
            if (str(data['id'])!=order['payment_id'] or data.get('external_reference')!=order['_id'] or
                str(data.get('collector_id'))!=os.environ['MP_COLLECTOR_ID'] or data.get('currency_id')!='BRL' or
                data.get('payment_method_id')!='pix' or amount!=order['amount_cents'] or
                data.get('live_mode') is not (os.getenv('BILLING_MP_LIVE_MODE','true')=='true')):raise ValueError()
        except (ValueError,KeyError,InvalidOperation):raise HTTPException(409,'payment_verification_mismatch') from None
        status=data.get('status')
        if status!='approved':
            # Refunds and disputes remain visible for owner review, never disguised as paid.
            await self.db.billing_orders.update_one({'_id':order_id},{'$set':{'provider_status':status,'checked_at':now(),
                'status':status if order.get('status')!='granted' else 'review_required' if status in ('refunded','charged_back') else 'granted'}})
            return self.public(await self.db.billing_orders.find_one({'_id':order_id}))
        if Decimal(str(data.get('transaction_amount_refunded',0)))!=0:raise HTTPException(409,'payment_refunded_review_required')
        for _ in range(5):
            lic=await self.license(order['license_id'])
            if lic['kind']!='subscription':raise HTTPException(409,'permanent_license_has_no_charge')
            if order_id in lic.get('billing_applied_orders',[]):
                until=lic['expires_at'];break
            until=max(lic['expires_at'],now())+timedelta(days=order['period_days'])
            result=await self.db.commercial_licenses.update_one({'_id':lic['_id'],'business_id':business(),'revoked':False,
                'expires_at':lic['expires_at'],'billing_applied_orders':{'$ne':order_id}},
                {'$set':{'expires_at':until},'$addToSet':{'billing_applied_orders':order_id}})
            if result.matched_count:break
        else:raise HTTPException(409,'license_changed_retry')
        await self.db.billing_orders.update_one({'_id':order_id},{'$set':{'status':'granted','provider_status':'approved',
            'granted_until':until,'checked_at':now(),'next_check_at':now()+timedelta(days=1)}})
        return self.public(await self.db.billing_orders.find_one({'_id':order_id}))

    async def recover(self):
        if not configured():return
        clock=now()
        rows=await self.db.billing_orders.find({'business_id':business(),'status':{'$in':['pending','in_process']},
            'payment_id':{'$exists':True},'$or':[{'next_check_at':{'$exists':False}},{'next_check_at':{'$lt':clock}}]}).limit(5).to_list(5)
        for row in rows:
            claim=await self.db.billing_orders.find_one_and_update({'_id':row['_id'],'$or':[
                {'next_check_at':{'$exists':False}},{'next_check_at':{'$lt':clock}}]},
                {'$set':{'next_check_at':clock+timedelta(minutes=5)}},return_document=True)
            if claim:
                try:await self.reconcile(row['_id'])
                except Exception:pass  # Retry later; never grant on a network/error status.


def billing_router(database):
    from crm_admin import authorize
    from device_access import DeviceAccess
    api=APIRouter(prefix='/billing')
    def db():
        value=database()
        if value is None:raise HTTPException(503,'Database unavailable')
        return value
    async def identity(request):
        if request.headers.get('x-jarvis-device'):
            device=await DeviceAccess(db()).verify(request,allow_expired=True)
            record=await db().authorized_devices.find_one({'_id':device,'revoked':False})
            if not record.get('license_id'):raise HTTPException(409,'internal_access_has_no_charge')
            return record['license_id']
        authorize(request)
        return request.query_params.get('license_id')
    @api.get('/account')
    async def account(request:Request):return jsonable_encoder(await PixBilling(db()).account(await identity(request)))
    @api.post('/checkout')
    async def checkout(request:Request):
        lic=await identity(request)
        if len(await request.body())>2048:raise HTTPException(413,'Payload too large')
        return jsonable_encoder(await PixBilling(db()).checkout(lic,await request.json()))
    @api.post('/check')
    async def check(request:Request):
        lic=await identity(request)
        record=await PixBilling(db()).license(lic)
        return jsonable_encoder(await PixBilling(db()).reconcile(record.get('billing_open_order')))
    @api.post('/webhook/mercadopago')
    async def webhook(request:Request):
        payment=signature(request)
        if len(await request.body())>8192:raise HTTPException(413,'Payload too large')
        body=await request.json()
        if not isinstance(body,dict) or body.get('type')!='payment' or not isinstance(body.get('data'),dict) or str(body['data'].get('id'))!=payment:
            raise HTTPException(400,'invalid_payment_notification')
        order=await db().billing_orders.find_one({'payment_id':payment,'business_id':business()})
        if not order:return {'received':True,'matched':False}
        await PixBilling(db()).reconcile(order['_id'])
        return {'received':True,'matched':True}
    return api
