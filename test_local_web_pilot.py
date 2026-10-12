import os
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from local_web_pilot import configuration, prepare


class PilotTests(unittest.IsolatedAsyncioTestCase):
    def test_requires_separate_database_and_disables_paid(self):
        env = {'PULSE_PILOT_DATABASE': 'jarvis', 'PULSE_PILOT_MONGODB_URI': 'mongodb://localhost',
               'PULSE_PILOT_ID_SECRET': 'x'*32}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError): configuration()
            os.environ['PULSE_PILOT_DATABASE'] = 'pulse_web_pilot_test'
            configuration()
            self.assertEqual(os.environ['AI_PAID_FALLBACK_ENABLED'], 'false')
            self.assertEqual(os.environ['JARVIS_REPLY_MODE'], 'test')

    async def test_reuses_memory_and_reply(self):
        mem = SimpleNamespace(record_inbound=AsyncMock(return_value={'_id':'test'}))
        generate=AsyncMock(return_value='resposta')
        result=await prepare(None,{'phone':'5511999999999','id':'web:'+'a'*64,'text':'oi'},mem,generate,lambda _:None)
        self.assertEqual(result,{'state':'prepared','reply':'resposta'})
        mem.record_inbound.assert_awaited_once()
        generate.assert_awaited_once()

    async def test_human_optout_and_urgency_stop_ai(self):
        db=SimpleNamespace(contacts=SimpleNamespace(update_one=AsyncMock()))
        generate=AsyncMock()
        for flags,reason in [({'human_mode':True},None),({'do_not_contact':True},None),({},'urgent')]:
            mem=SimpleNamespace(record_inbound=AsyncMock(return_value={'_id':'test',**flags}))
            result=await prepare(db,{'phone':'5511999999999','id':'web:'+'a'*64,'text':'oi'},mem,generate,lambda _:reason)
            self.assertIsNone(result['reply'])
        generate.assert_not_awaited()

    async def test_invalid_event_never_reaches_memory(self):
        mem=SimpleNamespace(record_inbound=AsyncMock())
        with self.assertRaises(ValueError):
            await prepare(None,{'phone':'group@g.us','id':'bad','text':'oi'},mem,AsyncMock(),lambda _:None)
        mem.record_inbound.assert_not_awaited()
