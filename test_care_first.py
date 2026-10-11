import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import os

import main
from human_waiting import DIRECT_CONTACT_GUIDANCE
from test_human_service import Store
from test_contact_memory import Database


class CareFirstTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        p = patch.dict(os.environ, {'META_APP_SECRET': 'fake', 'AI_ALLOWED_TEST_ONLY': 'false',
            'JARVIS_INSTRUCTIONS': 'Regras institucionais ' * 200, 'OPENAI_MODEL': 'fake-model'}, clear=True)
        p.start(); self.addCleanup(p.stop)

    async def test_initial_handoff_registers_request_without_contact_dump(self):
        db = Database(); inbox = Store(); inbox.database = db
        send = AsyncMock(return_value='ack')
        import time
        with patch.object(main, 'inbox', inbox), patch.object(main, 'send_reply', send):
            await main.process_message({'id': 'care-first', 'from': '5511987654321',
                'timestamp': str(time.time()), 'text': {'body': 'Quero falar com Morgan'}})
        text = send.call_args.args[1]
        self.assertIn('pedido de atendimento está registrado', text)
        self.assertNotIn('wa.me', text)
        self.assertNotIn('tel:', text)

    async def test_hybrid_support_gets_care_guidance_before_long_instructions(self):
        router = SimpleNamespace(reply=AsyncMock(return_value='Teste'))
        with patch.dict(os.environ, {'JARVIS_REPLY_MODE': 'hybrid'}), \
                patch.object(main, 'inbox', SimpleNamespace(database=Database())), \
                patch.object(main, 'ReplyRouter', return_value=router):
            await main.generate_reply('Já fui atendido, obrigado', '5511987654321', 'm1', waiting_for_human=True)
        instructions = router.reply.call_args.args[2][:2200]
        self.assertIn('Se ele já informou isso, não repita a pergunta', instructions)
        self.assertIn('Não comece o acompanhamento enviando telefone ou links', instructions)

    async def test_openai_support_and_general_sales_get_shared_mission(self):
        client = SimpleNamespace(responses=SimpleNamespace(create=AsyncMock(
            return_value=SimpleNamespace(output_text='Resposta simulada'))))
        context = AsyncMock(); context.__aenter__.return_value = client
        with patch.dict(os.environ, {'JARVIS_REPLY_MODE': 'openai'}), \
                patch.object(main, 'inbox', None), patch.object(main, 'AsyncOpenAI', return_value=context):
            for support in (False, True):
                await main.generate_reply('Pode me ajudar?', waiting_for_human=support)
                instructions = client.responses.create.call_args.kwargs['instructions']
                self.assertIn('Nossa missão é ajudar e facilitar', instructions)
                self.assertIn('Não comece o acompanhamento enviando telefone ou links', instructions)
                self.assertIn('Não afirme que somos uma empresa grande', instructions)
                if support:
                    self.assertIn('não contradiga seu relato com o status da fila', instructions)

    def test_direct_contact_remains_available_when_requested(self):
        self.assertIn('tel:+5581989927699', DIRECT_CONTACT_GUIDANCE)
        self.assertIn('https://wa.me/5581989927699', DIRECT_CONTACT_GUIDANCE)
        self.assertIn('quando o cliente pedir', DIRECT_CONTACT_GUIDANCE)


if __name__ == '__main__':
    unittest.main()
