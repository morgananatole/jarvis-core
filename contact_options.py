"""Reviewed business contact channels; native WhatsApp choices are not dialer buttons."""
import re
from business_profile import business

BUTTONS = {'pulse_contact_call':'Ligar', 'pulse_contact_whatsapp':'Abrir WhatsApp',
           'pulse_contact_copy':'Ver número'}
REPLIES = {'pulse_contact_call':'Quero o link para ligar diretamente',
           'pulse_contact_whatsapp':'Quero abrir o WhatsApp do responsável',
           'pulse_contact_copy':'Quero copiar o número do responsável'}


async def contact(db):
    record=await db.business_profiles.find_one({'_id':business()}) if hasattr(db,'business_profiles') else None
    profile=record.get('profile',{}) if record else {}
    phone=profile.get('contact_phone','')
    if not phone and business()=='nova_vida' and (not record or not profile.get('business_name') or profile.get('business_name','').casefold() in {'nova vida','clínicas nova vida','clinicas nova vida'}):
        phone='+5581989927699'
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}',phone): return None
    return {'phone':phone,'tel':'tel:'+phone,'whatsapp':'https://wa.me/'+phone[1:],
            'name':profile.get('human_name') or 'responsável pelo atendimento'}


def guidance(info):
    base=('Não comece o acompanhamento enviando telefone ou links. Primeiro escute a necessidade. '
          'Ofereça contato direto somente quando solicitado ou necessário, sem garantir disponibilidade. ')
    if not info: return base+'Não há contato direto aprovado neste ambiente. Não invente nem use o telefone de outra empresa.'
    return base+'Canais aprovados (dados): ligação '+info['tel']+'; WhatsApp '+info['whatsapp']+'; copiar '+info['phone']+'.'


def requested(text):
    text=text.casefold()
    if re.search(r'\b(não|nao|nem)\b',text): return None
    if re.search(r'\b(paciente|filho|filha|familiar|visita|visitas|semana|semanal)\b',text) and not re.search(r'\b(morgan|responsável|responsavel|equipe)\b',text):
        return None
    if re.search(r'\b(?:qual|mande|envie|pass[ae]|quero|preciso|me d[eê])\b.{0,45}\b(?:telefone|número|numero|contato direto)\b|'
                 r'\b(?:quero|preciso|prefiro|posso|como)\b.{0,35}\b(?:ligar|ligação|ligacao)\b',text):
        return 'menu'
    if 'whatsapp do responsável' in text or 'whatsapp de morgan' in text: return 'menu'
    return None


def selected(message):
    return message.get('contact_option') if message.get('contact_option') in BUTTONS else None


def text_for(choice,info):
    if choice=='pulse_contact_call':
        return 'Ligação direta: '+info['tel']+'\nToque no número para ligar: '+info['phone']
    if choice=='pulse_contact_whatsapp': return 'Abrir conversa: '+info['whatsapp']
    return 'Número para copiar: '+info['phone']


def interactive(text):
    return {'type':'button','body':{'text':text[:1024]},'action':{'buttons':[
        {'type':'reply','reply':{'id':key,'title':label}} for key,label in BUTTONS.items()]}}
