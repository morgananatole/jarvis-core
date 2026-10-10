"""Owner-triggered, read-only Meta connectivity probe; never changes number registration."""
import os
import httpx
from fastapi import HTTPException

async def diagnostic():
    required=['WHATSAPP_ACCESS_TOKEN','WHATSAPP_PHONE_NUMBER_ID','META_GRAPH_VERSION']
    if not all(os.getenv(k) for k in required):raise HTTPException(503,'whatsapp_connection_not_configured')
    url='https://graph.facebook.com/'+os.environ['META_GRAPH_VERSION']+'/'+os.environ['WHATSAPP_PHONE_NUMBER_ID']
    try:
        async with httpx.AsyncClient(timeout=10,follow_redirects=False) as client:
            headers={'Authorization':'Bearer '+os.environ['WHATSAPP_ACCESS_TOKEN']}
            result=await client.get(url,params={'fields':'display_phone_number,platform_type,is_on_biz_app'},headers=headers)
            extended=result.is_success
            if result.status_code==400:
                result=await client.get(url,params={'fields':'display_phone_number'},headers=headers)
            if not result.is_success:raise HTTPException(502,'meta_connection_check_failed')
            data=result.json()
    except (httpx.HTTPError,ValueError):raise HTTPException(502,'meta_connection_check_failed') from None
    on_app=data.get('is_on_biz_app') if extended else None
    return {'api_read_access':True,'phone_ending':str(data.get('display_phone_number',''))[-4:],
        'platform':data.get('platform_type') if extended else None,'business_app_connected':on_app,
        'coexistence_status':'reported_connected' if on_app is True else 'reported_not_connected' if on_app is False else 'not_confirmed',
        'registration_changed':False,'note':'Leitura da API não comprova entrega de mensagens nem elegibilidade para migrar. Confirme o fluxo de coexistência antes de reinstalar ou registrar o número.'}
