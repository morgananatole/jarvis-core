"""One durable waiting acknowledgement, then bounded assistance until Morgan replies.

This is an answer to an open customer conversation, never a marketing follow-up.
Human queue and reviewed follow-ups remain intact. One-instance contact locks apply.
"""
import os
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from contact_memory import ContactMemory
from human_service import active_window, conversation_lock

WAIT = timedelta(minutes=5)
DIRECT_CONTACT = (
    'Para tentar falar diretamente, ligue: tel:+5581989927699\n'
    'Abrir conversa no WhatsApp: https://wa.me/5581989927699\n'
    'Número para copiar: +55 81 98992-7699'
)
SUPPORT_GUIDANCE = (
    'O atendimento humano de Morgan continua pendente. Você está apoiando a conversa '
    'enquanto o cliente aguarda, sem substituir a decisão humana. Informe isso quando '
    'relevante; esclareça dúvidas comerciais com fatos disponíveis e ofereça um próximo '
    'passo útil. Não diga que Morgan está em reunião, atendendo outra pessoa ou que '
    'responderá em determinado horário sem confirmação. Não confirme fechamento, '
    'vaga, pagamento, resgate nem conduta clínica em nome dele. Não encerre a fila humana.'
    '\nSe o cliente precisar de contato direto, ofereça estes caminhos informados pelo '
    'proprietário, sem garantir disponibilidade nem que abrir WhatsApp inicia atendimento humano: '
    + DIRECT_CONTACT
)


def utc(value):
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def can_assist(profile, queue):
    return bool(profile.get('ai_waiting_assist') and not profile.get('human_only')
                and not profile.get('do_not_contact')
                and profile.get('facts', {}).get('contact_permission', {}).get('value') != 'declined'
                and queue and queue.get('state') in {'waiting', 'active'}
                and queue.get('reason') not in {'urgent', 'reply_failed_or_uncertain'})


class WaitingService:
    def __init__(self, db, send, tester, clock=None):
        self.db, self.send, self.tester = db, send, tester
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def run_due(self):
        # Includes old waiting records on upgrade; legacy active records are skipped.
        rows = await self.db.human_requests.find({'state': {'$in': ['waiting', 'active']},
            'wait_notice_state': {'$nin': ['accepted', 'review_required', 'answered', 'cancelled']},
            '$or': [{'pending_since': {'$lte': self.clock() - WAIT}},
                    {'pending_since': {'$exists': False}}]}).sort('pending_since', 1).limit(50).to_list(50)
        for row in rows:
            await self.run_one(row['_id'])

    async def run_one(self, key):
        async with conversation_lock(key):
            queue = await self.db.human_requests.find_one({'_id': key})
            profile = await self.db.contacts.find_one({'_id': key})
            now = self.clock()
            if not queue or not profile or not profile.get('human_mode'):
                return {'state': 'not_waiting'}
            if queue.get('state') not in {'waiting', 'active'}:
                return {'state': 'not_waiting'}
            since = utc(queue.get('pending_since'))
            if 'pending_since' not in queue and queue.get('state') == 'waiting':
                since = utc(profile.get('human_since'))
            if not since or now < since + WAIT:
                return {'state': 'not_due'}
            if (profile.get('do_not_contact') or
                    profile.get('facts', {}).get('contact_permission', {}).get('value') == 'declined'):
                return {'state': 'suppressed'}
            if not active_window(profile, now):
                return {'state': 'window_expired'}
            mode = os.getenv('JARVIS_REPLY_MODE', 'openai')
            if mode == 'test' or (mode == 'hybrid' and os.getenv('AI_ALLOWED_TEST_ONLY', 'true') == 'true'):
                if not self.tester(profile['phone']):
                    return {'state': 'test_recipient_only'}
            if queue.get('reason') == 'reply_failed_or_uncertain':
                return {'state': 'review_required'}
            episode = queue.get('wait_episode') or 'legacy:' + since.isoformat()
            job_id = 'human-wait:' + key + ':' + episode
            try:
                await self.db.operator_jobs.insert_one({'_id': job_id, 'contact_no': profile['contact_no'],
                    'state': 'sending', 'created_at': now,
                    'expires_at': now + timedelta(days=90)})
            except DuplicateKeyError:
                return {'state': 'already_claimed'}
            protected = profile.get('human_only') or queue.get('reason') == 'urgent'
            text = ('Sou o JARVIS, assistente virtual. Seu pedido continua aguardando o atendimento '
                    'de Morgan; ainda não tenho confirmação de quando ele poderá responder. ')
            text += ('O encaminhamento humano continua pendente; não posso confirmar execução ou horário.'
                     if protected else
                     'Enquanto você aguarda, posso esclarecer alguma dúvida sobre nosso serviço? '
                     'Continuo por aqui para ajudar, e seu pedido de atendimento humano permanece na fila.')
            text += '\n\n' + DIRECT_CONTACT
            try:
                mid = await self.send(profile['phone'], text)
                await ContactMemory(self.db).record_outbound(profile['phone'], mid, text)
                await self.db.operator_jobs.update_one({'_id': job_id}, {'$set': {
                    'state': 'accepted', 'outbound_id': mid}})
                await self.db.human_requests.update_one({'_id': key}, {'$set': {
                    'wait_notice_state': 'accepted', 'wait_notice_at': now,
                    'wait_notice_outbound_id': mid}})
                await self.db.contacts.update_one({'_id': key}, {'$set': {
                    'ai_waiting_assist': not protected}})
                return {'state': 'accepted', 'assistance': not protected}
            except Exception:
                # A crash in sending is also non-retryable: unique job survives restart.
                await self.db.operator_jobs.update_one({'_id': job_id}, {'$set': {'state': 'review_required'}})
                await self.db.human_requests.update_one({'_id': key}, {'$set': {
                    'wait_notice_state': 'review_required', 'unread': True}})
                return {'state': 'review_required'}
