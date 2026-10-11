"""One durable waiting acknowledgement, then bounded assistance until Morgan replies.

This is an answer to an open customer conversation, never a marketing follow-up.
Human queue and reviewed follow-ups remain intact. One-instance contact locks apply.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from contact_memory import ContactMemory
from human_service import active_window, conversation_lock

WAIT = timedelta(minutes=5)
log = logging.getLogger('jarvis')
DIRECT_CONTACT = (
    'Para tentar falar diretamente, ligue: tel:+5581989927699\n'
    'Abrir conversa no WhatsApp: https://wa.me/5581989927699\n'
    'Número para copiar: +55 81 98992-7699'
)
DIRECT_CONTACT_GUIDANCE = (
    'Não comece o acompanhamento enviando telefone ou links. Primeiro escute a necessidade. '
    'Ofereça contato direto quando o cliente pedir ligação, WhatsApp ou telefone, ou quando '
    'um encaminhamento direto for necessário. Use só o canal útil, sem despejar três opções '
    'sem necessidade. Não garanta disponibilidade humana. Contatos informados: ' + DIRECT_CONTACT
)
SUPPORT_GUIDANCE = (
    'A fila registra atendimento humano pendente; isso não prova que o cliente não foi '
    'atendido por outro canal. Primeiro verifique se já recebeu atendimento, usando o '
    'histórico e a resposta atual. Se ele já informou isso, não repita a pergunta. '
    'Se foi atendido, reconheça e pergunte apenas se ficou alguma necessidade, quando '
    'relevante; não contradiga seu relato com o status da fila nem declare resolução '
    'total sem confirmação. Se ainda aguarda, reconheça a espera sem desculpas repetidas '
    'e ajude na dúvida concreta. Você está apoiando a conversa '
    'enquanto o cliente aguarda, sem substituir a decisão humana. Informe isso quando '
    'relevante; esclareça dúvidas comerciais com fatos disponíveis e ofereça um próximo '
    'passo útil. Não diga que Morgan está em reunião, atendendo outra pessoa ou que '
    'responderá em determinado horário sem confirmação. Não confirme fechamento, '
    'vaga, pagamento, resgate nem conduta clínica em nome dele. Não encerre a fila humana.'
    '\n' + DIRECT_CONTACT_GUIDANCE
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
    def __init__(self, db, send, tester, clock=None, compose=None):
        self.db, self.send, self.tester = db, send, tester
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.compose = compose

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
            text = ('Você já conseguiu receber o atendimento humano de que precisava? '
                    'Sou o JARVIS, assistente virtual, e estou acompanhando sua solicitação. ')
            text += ('Seu pedido permanece disponível para Morgan; não tenho confirmação de horário.'
                     if protected else
                     'Se ainda estiver aguardando, continuo por aqui para ajudar com suas dúvidas '
                     'enquanto Morgan não responde.')
            from business_profile import business
            if business()!='nova_vida': text=text.replace('Morgan','a equipe humana')
            if not protected and self.compose:
                try:
                    natural = await self.compose(profile)
                    if natural:
                        text = natural
                except Exception:
                    # A provider failure must not abandon the customer or retry delivery.
                    log.info('Human waiting care uses fixed fallback')
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
                log.info('Human waiting care acknowledgement accepted')
                return {'state': 'accepted', 'assistance': not protected}
            except Exception:
                # A crash in sending is also non-retryable: unique job survives restart.
                await self.db.operator_jobs.update_one({'_id': job_id}, {'$set': {'state': 'review_required'}})
                await self.db.human_requests.update_one({'_id': key}, {'$set': {
                    'wait_notice_state': 'review_required', 'unread': True}})
                log.warning('Human waiting care acknowledgement requires review')
                return {'state': 'review_required'}
