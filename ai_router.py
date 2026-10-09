"""Free-first replies; persistent cooldown, bounded paid usage and shared context."""
import asyncio
import hashlib
import hmac
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

log = logging.getLogger('jarvis.ai')
UNAVAILABLE = ('Sou o JARVIS, assistente virtual da Nova Vida. Minha interpretação '
               'automática está temporariamente indisponível. Por favor, aguarde '
               'o atendimento humano; não consigo confirmar informações agora.')


class ProviderFailure(Exception):
    def __init__(self, transient=False, retry_after=60):
        super().__init__('provider_unavailable')
        self.transient = transient
        self.retry_after = retry_after


def wait_seconds(value, now=None):
    """Respect Retry-After seconds or HTTP date, including daily quota resets."""
    now = time.time() if now is None else now
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        try:
            seconds = parsedate_to_datetime(value).timestamp() - now
        except (TypeError, ValueError, OverflowError):
            seconds = 60
    if not 0 <= seconds <= 7 * 86400:
        seconds = 60
    return max(1, seconds)


def settings():
    def number(name, default, maximum):
        try:
            return max(0, min(maximum, int(os.getenv(name, str(default)))))
        except ValueError:
            return 0
    return {
        'free_key': os.getenv('GROQ_API_KEY', '').strip(),
        'free_model': os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'),
        'paid_key': os.getenv('OPENAI_API_KEY', '').strip(),
        'paid_model': os.getenv('OPENAI_MODEL', 'gpt-4.1-mini'),
        'paid_enabled': os.getenv('AI_PAID_FALLBACK_ENABLED') == 'true',
        'paid_cap': number('AI_PAID_MAX_CALLS_PER_DAY', 0, 1000),
        'output': max(1, number('AI_MAX_OUTPUT_TOKENS', 300, 500)),
    }


def reset_seconds(value):
    parts = re.findall(r'(\d+(?:\.\d+)?)(ms|h|m|s)', value or '')
    if not parts:
        return wait_seconds(value)
    return max(1, sum(float(n) * {'h': 3600, 'm': 60, 's': 1, 'ms': .001}[u]
                      for n, u in parts))


async def provider_call(provider, messages, config):
    # No automatic SDK retries: reserve/count every possible paid request.
    if provider == 'free':
        import httpx
        try:
            async with httpx.AsyncClient(timeout=12) as client:
                response = await client.post(
                    'https://api.groq.com/openai/v1/chat/completions',
                    headers={'Authorization': 'Bearer ' + config['free_key']},
                    json={'model': config['free_model'], 'messages': messages,
                          'max_completion_tokens': config['output']})
            if response.is_error:
                raise ProviderFailure(
                    response.status_code in (408, 429) or response.status_code >= 500,
                    wait_seconds(response.headers.get('retry-after')))
            data = response.json()
            text = data['choices'][0]['message']['content']
            # Successful final request can already exhaust the free request quota.
            pause = 0
            for quota in ('requests', 'tokens'):
                if response.headers.get('x-ratelimit-remaining-' + quota) == '0':
                    pause = max(pause, reset_seconds(response.headers.get(
                        'x-ratelimit-reset-' + quota)))
            return text, pause
        except (httpx.TimeoutException, httpx.NetworkError):
            raise ProviderFailure(True, 30) from None
        except (ValueError, KeyError, IndexError, TypeError):
            raise ProviderFailure(True, 60) from None
    from openai import AsyncOpenAI
    try:
        async with AsyncOpenAI(api_key=config['paid_key'], timeout=15, max_retries=0) as client:
            result = await client.responses.create(
                model=config['paid_model'], store=False,
                instructions=messages[0]['content'], input=messages[1:],
                max_output_tokens=config['output'])
            return result.output_text, 0
    except Exception:
        # Do not log provider response bodies or credentials.
        raise ProviderFailure(False) from None


class ReplyRouter:
    def __init__(self, database, call=provider_call, clock=time.time):
        self.db, self.call, self.clock = database, call, clock

    async def initialize(self):
        await self.db.ai_history.create_index('expires_at', expireAfterSeconds=0)
        await self.db.ai_budgets.create_index('expires_at', expireAfterSeconds=0)

    async def reserve_paid(self, cap):
        if cap <= 0:
            return False
        now = datetime.fromtimestamp(self.clock(), timezone.utc)
        key = 'openai:' + now.strftime('%Y-%m-%d')
        try:
            await self.db.ai_budgets.update_one(
                {'_id': key}, {'$setOnInsert': {'used': 0,
                 'expires_at': now + timedelta(days=2)}}, upsert=True)
        except Exception:
            # Concurrent initialization may hit the unique _id; never reset usage.
            if not await self.db.ai_budgets.find_one({'_id': key}):
                raise
        doc = await self.db.ai_budgets.find_one_and_update(
            {'_id': key, 'used': {'$lt': cap}}, {'$inc': {'used': 1}},
            return_document=True)
        return doc is not None

    async def reply(self, sender, text, instructions):
        config = settings()
        if not config['free_key']:
            log.warning('AI free provider not configured; paid fallback not used')
            return UNAVAILABLE
        identity_secret = os.getenv('META_APP_SECRET', '')
        if not identity_secret:
            return UNAVAILABLE
        session = hmac.new(identity_secret.encode(), sender.encode(), hashlib.sha256).hexdigest()
        now = self.clock()
        history = await self.db.ai_history.find_one({'_id': session})
        turns = history.get('turns', []) if history else []
        if history and history.get('expires_at').timestamp() <= now:
            turns = []
        messages = [{'role': 'system', 'content': instructions[:4000]}]
        messages.extend({'role': x['role'], 'content': x['content'][:1000]}
                        for x in turns[-6:])
        messages.append({'role': 'user', 'content': text[:3000]})
        policy = await self.db.ai_policy.find_one({'_id': 'groq'}) or {}
        blocked = policy.get('retry_at', 0) > now
        reply, provider = None, None
        if not blocked:
            try:
                reply, pause = await self.call('free', messages, config)
                if not isinstance(reply, str) or not reply.strip():
                    raise ProviderFailure(True, 60)
                provider = 'free'
                if pause:
                    await self.db.ai_policy.update_one({'_id': 'groq'},
                        {'$max': {'retry_at': self.clock() + pause}}, upsert=True)
            except ProviderFailure as failure:
                if not failure.transient:
                    log.warning('AI free provider configuration rejected; paid fallback not used')
                    return UNAVAILABLE
                await self.db.ai_policy.update_one({'_id': 'groq'},
                    {'$max': {'retry_at': self.clock() + failure.retry_after}}, upsert=True)
                blocked = True
        if reply is None and blocked:
            if (not config['paid_enabled'] or not config['paid_key']
                    or not await self.reserve_paid(config['paid_cap'])):
                log.warning('AI paid fallback disabled or daily cap reached')
                return UNAVAILABLE
            try:
                reply, _ = await self.call('paid', messages, config)
                if not isinstance(reply, str) or not reply.strip():
                    raise ProviderFailure()
                provider = 'paid'
            except ProviderFailure:
                log.warning('AI paid fallback unavailable; human handoff required')
                return UNAVAILABLE
        reply = reply.strip()[:4000]
        expiry = datetime.fromtimestamp(self.clock(), timezone.utc) + timedelta(days=7)
        await self.db.ai_history.update_one({'_id': session}, {'$set': {
            'turns': (turns + [{'role': 'user', 'content': text[:1000]},
                               {'role': 'assistant', 'content': reply[:1000]}])[-6:],
            'expires_at': expiry}}, upsert=True)
        log.warning('AI reply generated: provider=%s', provider)
        return reply
