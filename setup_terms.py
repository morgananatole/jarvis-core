"""Versioned, private authorization for essential PULSE contact processing."""
from datetime import datetime, timezone
from fastapi import HTTPException
from business_intake import tenant
VERSION = 'pulse-contact-operations-2026-10-12-v1'
NOTICE = ('Permite o compartilhamento de seus contatos com JARVIS PULSE? '
          'O serviço armazenará nomes e telefones para organizar e operar o atendimento da sua empresa. '
          'Pessoas autorizadas no seu ambiente poderão consultar esses dados. '
          'Este aceite não autoriza repasse comercial entre empresas nem mensagens sem permissão do destinatário. '
          'Não inclui acesso automático do criador a outras instalações. Você pode retirar o aceite nesta tela; '
          'isso bloqueia novas etapas de configuração e importação, sem apagar o histórico existente.')
class SetupTerms:
    def __init__(self, db): self.db = db
    async def status(self, actor):
        item = await self.db.setup_terms.find_one({'_id': tenant()+':'+actor}) or {}
        return {'version': VERSION, 'notice': NOTICE, 'accepted': item.get('version') == VERSION and item.get('accepted') is True,
                'decided_at': item.get('decided_at')}
    async def decide(self, body, actor):
        if not isinstance(body, dict) or set(body) != {'version','accepted'} or body.get('version') != VERSION or type(body.get('accepted')) is not bool:
            raise HTTPException(400, 'invalid_terms_decision')
        await self.db.setup_terms.update_one({'_id': tenant()+':'+actor}, {'$set': {'business_id':tenant(), 'actor':actor,
            'version':VERSION,'accepted':body['accepted'],'notice':NOTICE,'decided_at':datetime.now(timezone.utc)}},upsert=True)
        return await self.status(actor)
    async def require(self, actor):
        if not (await self.status(actor))['accepted']:
            raise HTTPException(403,'É preciso aceitar os termos de operação dos contatos para continuar a configuração.')
