"""Private readiness classification; address-book import never grants opt-in."""
import os
from datetime import datetime, timezone
from conversation_service import gate
from contact_memory import conversation_plan
LABELS={'permission_required':'Aguardando autorização','human_takeover':'Atendimento humano',
'test_recipient_only':'Restrito ao piloto','approved_template_required':'Precisa de modelo aprovado',
'hybrid_ai_required':'Verificar IA','ready':'Pronto para revisão','declined':'Não contatar'}
def classify(profile, tester, now=None):
    if profile.get('do_not_contact') or profile.get('facts',{}).get('contact_permission',{}).get('value')=='declined': return 'declined'
    return gate(profile, now or datetime.now(timezone.utc), tester) or 'ready'
INTEREST_LABELS={'unknown':'Ainda não qualificado','exploring':'Busca informações','deciding':'Avalia contratação','customer':'Cliente / pós-atendimento','not_interested':'Sem interesse informado'}
def interest(profile):
    values={k:v.get('value') for k,v in profile.get('facts',{}).items() if isinstance(v,dict)}
    manual=profile.get('commercial_review',{}).get('interest')
    if manual in INTEREST_LABELS: level=manual
    elif profile.get('do_not_contact') or values.get('contact_permission')=='declined':level='not_interested'
    elif values.get('lifecycle') in {'enrolled','postcare'}:level='customer'
    elif profile.get('signals',{}).get('decision'):level='deciding'
    elif profile.get('signals',{}).get('price') or profile.get('signals',{}).get('availability') or values.get('lifecycle')=='considering':level='exploring'
    else:level='unknown'
    plan=conversation_plan(profile,datetime.now(timezone.utc))
    return {'interest':level,'interest_label':INTEREST_LABELS[level],'priority':plan.get('priority',0),'next_action':plan['purpose'],'suggested_at':plan.get('due_at'), 'qualification_is_permission':False}
async def overview(db,tester,offset=0):
    # This deployment has one isolated business database. No cross-installation reads.
    total=await db.contacts.count_documents({})
    counts={key:0 for key in LABELS}
    cursor=db.contacts.find({},{'facts':1,'phone':1,'contact_no':1,'signals':1,'inbound_count':1,'commercial_review':1,'human_mode':1,'do_not_contact':1,'last_inbound_at':1}).sort('_id',1)
    rows=[]
    async for p in cursor:
        state=classify(p,tester);counts[state]+=1
        if offset <= sum(counts.values())-1 < offset+100:
            rows.append({'id':p['contact_no'],'name':p.get('facts',{}).get('contact_name',{}).get('value') or '', 'phone':p.get('phone'), 'state':state,'label':LABELS[state],**interest(p)})
    return {'total':total,'counts':counts,'labels':LABELS,'rows':rows,'offset':offset,'page_size':100,
            'template_send_enabled':os.getenv('WHATSAPP_TEMPLATE_SEND_ENABLED','false')=='true',
            'template_daily_cap':os.getenv('WHATSAPP_TEMPLATE_MAX_PER_DAY','0'),
            'messages_sent_by_this_action':0,
            'notice':'Número salvo não é requisito. Importação não comprova permissão. Modelo aprovado não substitui opt-in. Ritmo baixo não garante ausência de bloqueio.'}
