import asyncio
import copy
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from ai_router import ReplyRouter, ProviderFailure, UNAVAILABLE, wait_seconds, reset_seconds, provider_call, settings


class Collection:
    def __init__(self):
        self.docs = {}
    async def create_index(self, *args, **kwargs):
        pass
    async def find_one(self, query):
        return copy.deepcopy(self.docs.get(query['_id']))
    async def update_one(self, query, update, upsert=False):
        key = query['_id']
        new = key not in self.docs
        if new and not upsert:
            return
        doc = self.docs.setdefault(key, {'_id': key})
        if new:
            doc.update(update.get('$setOnInsert', {}))
        doc.update(update.get('$set', {}))
        for k, v in update.get('$max', {}).items():
            doc[k] = max(doc.get(k, 0), v)
    async def find_one_and_update(self, query, update, **kwargs):
        doc = self.docs.get(query['_id'])
        if not doc or doc['used'] >= query['used']['$lt']:
            return None
        doc['used'] += update['$inc']['used']
        return copy.deepcopy(doc)


class Database:
    def __init__(self):
        self.ai_history, self.ai_policy, self.ai_budgets = (Collection() for _ in range(3))


class RouterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            'GROQ_API_KEY': 'fake-free', 'OPENAI_API_KEY': 'fake-paid',
            'AI_PAID_FALLBACK_ENABLED': 'true', 'AI_PAID_MAX_CALLS_PER_DAY': '2',
            'META_APP_SECRET': 'fake-session-key'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.db, self.now, self.calls = Database(), 1000000, []
    def router(self, call):
        return ReplyRouter(self.db, call=call, clock=lambda: self.now)

    async def test_free_success_never_spends_and_shares_context(self):
        async def call(provider, messages, config):
            self.calls.append((provider, messages))
            return 'resposta contextual', 0
        r = self.router(call)
        await r.reply('551234567890', 'meu nome é Morgan', 'instruções')
        await r.reply('551234567890', 'qual meu nome?', 'instruções')
        self.assertEqual([x[0] for x in self.calls], ['free', 'free'])
        self.assertIn('meu nome é Morgan', str(self.calls[-1][1]))
        self.assertFalse(self.db.ai_budgets.docs)
        self.assertNotIn('551234567890', str(list(self.db.ai_history.docs)))

    async def test_429_paid_cooldown_restart_then_free_recovery(self):
        async def call(provider, messages, config):
            self.calls.append(provider)
            if len(self.calls) == 1:
                raise ProviderFailure(True, 120)
            return 'ok ' + provider, 0
        await self.router(call).reply('a', 'primeira', 'regras')
        self.now += 30
        await self.router(call).reply('a', 'segunda', 'regras')
        self.now += 91
        await self.router(call).reply('a', 'terceira', 'regras')
        self.assertEqual(self.calls, ['free', 'paid', 'paid', 'free'])

    async def test_configuration_error_does_not_spend(self):
        async def call(provider, messages, config):
            self.calls.append(provider)
            raise ProviderFailure(False)
        self.assertEqual(await self.router(call).reply('a', 'oi', 'regras'), UNAVAILABLE)
        self.assertEqual(self.calls, ['free'])
        self.assertFalse(self.db.ai_budgets.docs)

    async def test_budget_counts_failed_paid_attempts_and_stops(self):
        self.db.ai_policy.docs['groq'] = {'retry_at': self.now + 500}
        async def call(provider, messages, config):
            self.calls.append(provider)
            raise ProviderFailure(False)
        for _ in range(3):
            self.assertEqual(await self.router(call).reply('a', 'oi', 'r'), UNAVAILABLE)
        self.assertEqual(self.calls, ['paid', 'paid'])

    async def test_default_zero_budget_and_disabled_do_not_call_paid(self):
        self.db.ai_policy.docs['groq'] = {'retry_at': self.now + 500}
        async def call(*args):
            self.fail('paid must not run')
        for env in ({'AI_PAID_MAX_CALLS_PER_DAY': '0'},
                    {'AI_PAID_FALLBACK_ENABLED': 'false'}):
            with patch.dict(os.environ, env):
                self.assertEqual(await self.router(call).reply('a', 'oi', 'r'), UNAVAILABLE)

    async def test_expired_context_is_not_sent(self):
        async def call(provider, messages, config):
            self.calls.append(messages)
            return 'ok', 0
        r = self.router(call)
        await r.reply('a', 'mensagem antiga', 'r')
        self.now += 8 * 86400
        await r.reply('a', 'mensagem nova', 'r')
        self.assertNotIn('mensagem antiga', str(self.calls[-1]))

    async def test_atomic_reservations_and_next_day_budget(self):
        results = await asyncio.gather(*(self.router(None).reserve_paid(2) for _ in range(10)))
        self.assertEqual(sum(results), 2)
        self.now += 86400
        self.assertTrue(await self.router(None).reserve_paid(2))

    async def test_missing_free_key_never_routes_directly_to_paid(self):
        async def call(*args):
            self.fail('provider must not run')
        with patch.dict(os.environ, {'GROQ_API_KEY': ''}):
            self.assertEqual(await self.router(call).reply('a', 'oi', 'r'), UNAVAILABLE)

    def test_retry_after_seconds_http_date_and_invalid(self):
        self.assertEqual(wait_seconds('86400'), 86400)
        self.assertEqual(wait_seconds('Thu, 01 Jan 1970 00:02:00 GMT', now=60), 60)
        self.assertEqual(wait_seconds('bad'), 60)
        self.assertEqual(reset_seconds('2m59s'), 179)
        self.assertEqual(reset_seconds('500ms'), 1)

    async def test_real_http_adapter_success_and_zero_quota(self):
        import httpx
        original = httpx.AsyncClient
        def handle(request):
            import json
            payload = json.loads(request.content)
            self.assertEqual(payload['reasoning_effort'], 'low')
            self.assertFalse(payload['include_reasoning'])
            return httpx.Response(200, json={'choices': [{'message': {'content': 'entendi'}}]},
                headers={'x-ratelimit-remaining-tokens': '0', 'x-ratelimit-reset-tokens': '2m59s'})
        with patch('httpx.AsyncClient', side_effect=lambda **kw: original(
                transport=httpx.MockTransport(handle), **kw)):
            self.assertEqual(await provider_call('free', [], settings()), ('entendi', 179))

    async def test_real_http_adapter_429_and_401(self):
        import httpx
        original = httpx.AsyncClient
        for status, transient in ((429, True), (401, False)):
            with patch('httpx.AsyncClient', side_effect=lambda **kw: original(
                    transport=httpx.MockTransport(lambda r: httpx.Response(
                        status, headers={'retry-after': '3600'})), **kw)):
                with self.assertRaises(ProviderFailure) as ctx:
                    await provider_call('free', [], settings())
                self.assertEqual(ctx.exception.transient, transient)
                self.assertEqual(ctx.exception.retry_after, 3600)


if __name__ == '__main__':
    unittest.main()
