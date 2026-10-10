"""Parallel, rules-based dry-run planning. This module never executes integrations."""
import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from fastapi import HTTPException
from business_intake import tenant

VERSION = 'peripheral-2026-10-10-v1'
DECISION = {
    'version': VERSION, 'decided_at': '2026-10-10T13:01:45-03:00',
    'decision': 'Registrar integrações, caminhos e acessos como pré-habilidades; analisar melhorias em paralelo com o uso do app, primeiro em simulação.',
    'priority': 'Primeiro o app comercial e WhatsApp; evoluir paulatinamente.',
    'execution_mode': 'simulation_only',
    'limits': ['Não guardar valores de credenciais.', 'Não enviar mensagens, cobrar, alterar infraestrutura ou executar código.',
        'Propostas precisam de implementação e validação antes de executar.'],
}
CAPABILITIES = [
    {'id':'whatsapp', 'name':'Atendimento WhatsApp', 'status':'implemented_needs_e2e', 'paths':['/webhook'],
     'variables':['META_APP_SECRET','WHATSAPP_ACCESS_TOKEN','WHATSAPP_PHONE_NUMBER_ID'],
     'next':'Confirmar mensagem recebida, resposta e recibo de entrega no número oficial.'},
    {'id':'intake', 'name':'Organizar fotos, áudio e documentos', 'status':'implemented_needs_e2e', 'paths':['/crm/intake','/crm/intake/{id}/apply'],
     'variables':['GROQ_API_KEY','GROQ_VISION_MODEL','GROQ_AUDIO_MODEL'],
     'next':'Testar um arquivo real no painel e conferir evidências, cadastro e retornos.'},
    {'id':'followup', 'name':'Contato e retorno', 'status':'implemented_gated', 'paths':['/crm/task-actions/{id}/review','/crm/task-actions/{id}/run'],
     'variables':['CONVERSATION_EXECUTOR_ENABLED'],
     'next':'Conferir consentimento, data, pausa humana e janela/template antes de aprovar.'},
    {'id':'licenses', 'name':'Acesso comercial por dispositivo', 'status':'implemented_needs_owner_activation', 'paths':['/crm/licenses','/device/enroll'],
     'variables':['BUSINESS_ID','CRM_ADMIN_TOKEN'],
     'next':'Criar licença de teste e conferir instalação, vencimento e revogação.'},
    {'id':'external_evidence', 'name':'Evidência externa revisada', 'status':'implemented_allowlist', 'paths':[],
     'variables':['EXTERNAL_EVIDENCE_ENABLED'],
     'next':'Conferir fonte, data e pertinência da evidência na resposta comercial.'},
    {'id':'billing', 'name':'Pagamento recorrente automático', 'status':'planned', 'paths':[], 'variables':[],
     'next':'Conectar gateway com webhook autenticado e proteção contra repetição; não existe cobrança automática nesta versão.'},
]


def inventory():
    # Only presence is disclosed; values and customer data never enter this layer.
    return [{**c, 'configuration_present': {k:bool(os.getenv(k)) for k in c['variables']}} for c in CAPABILITIES]


def proposals(signals):
    if not isinstance(signals, dict) or set(signals) - {'media','goal'}:
        raise HTTPException(400, 'invalid_peripheral_signals')
    media, goal = signals.get('media','text'), signals.get('goal','organize')
    if media not in ('text','image','audio','pdf','other') or goal not in ('organize','sell','followup','access'):
        raise HTTPException(400, 'invalid_peripheral_signals')
    selected = ['intake','followup'] if goal == 'organize' else {
        'sell':['whatsapp','external_evidence'], 'followup':['followup','whatsapp'], 'access':['licenses','billing']}[goal]
    steps = [{ 'capability_id': c['id'], 'reason':c['next'], 'state':'proposed',
        'simulated_steps':['Conferir pré-requisitos e acesso.', 'Executar teste isolado e observar resultado.', 'Revisar antes de promover para uso real.'],
        'executed': False} for c in CAPABILITIES if c['id'] in selected]
    if media == 'pdf':
        steps.append({'capability_id':'ocr','reason':'PDF escaneado ainda exige OCR ou envio da página como imagem.',
            'state':'proposed','simulated_steps':['Identificar PDF sem texto.','Comparar opções de OCR.','Validar extração em arquivo de teste.'], 'executed':False})
    return steps


class Peripheral:
    def __init__(self, db): self.db = db
    async def decision(self):
        await self.db.peripheral_decisions.update_one({'_id':tenant()+':'+VERSION},
            {'$setOnInsert':{**DECISION,'business_id':tenant(),'recorded_at':datetime.now(timezone.utc)}},upsert=True)
    async def simulate(self, signals, identity=None):
        steps=proposals(signals)
        await self.decision()
        import secrets
        identity = identity or secrets.token_hex(16)
        identity=tenant()+':'+VERSION+':'+identity
        now=datetime.now(timezone.utc)
        record={'_id':identity,'business_id':tenant(),'version':VERSION,'created_at':now,
            'mode':'simulation_only','planner':'rules_v1','signals':signals,'proposals':steps,
            'events':['observation_received','simulation_created'],'executed':False}
        await self.db.peripheral_runs.update_one({'_id':identity},{'$setOnInsert':record},upsert=True)
        return record
    async def observe(self, body, key):
        """Best-effort side analysis; failure cannot block the customer's main work."""
        try:
            file=body.get('file') if isinstance(body,dict) else None
            mime=file.get('mime','') if isinstance(file,dict) else ''
            media='image' if isinstance(mime,str) and mime.startswith('image/') else 'audio' if isinstance(mime,str) and mime.startswith('audio/') else 'pdf' if mime=='application/pdf' else 'text'
            identity=hashlib.sha256(key.encode()).hexdigest() if isinstance(key,str) else None
            await asyncio.wait_for(self.simulate({'media':media,'goal':'organize'},identity),timeout=2)
        except Exception:
            logging.getLogger(__name__).warning('Peripheral simulation unavailable; main intake preserved')
