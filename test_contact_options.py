import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock,patch
from contact_options import contact,interactive,text_for,requested
from test_business_intake import Collection
from test_main import WebhookTests


class Channels(unittest.IsolatedAsyncioTestCase):
    async def test_other_business_never_inherits_morgan_number(self):
        db=SimpleNamespace(business_profiles=Collection())
        with patch.dict(os.environ,{'BUSINESS_ID':'other_business'}):
            self.assertIsNone(await contact(db))
            await db.business_profiles.insert_one({'_id':'other_business','profile':{
                'business_name':'Aurora','contact_phone':'+5511999999999'}})
            info=await contact(db)
            self.assertEqual(info['tel'],'tel:+5511999999999')

    def test_separate_buttons_and_single_selected_channel(self):
        options=interactive('Como prefere falar?')['action']['buttons']
        self.assertEqual([b['reply']['title'] for b in options],['Ligar','Abrir WhatsApp','Ver número'])
        info={'tel':'tel:+5581989927699','phone':'+5581989927699','whatsapp':'https://wa.me/5581989927699'}
        self.assertNotIn('wa.me',text_for('pulse_contact_call',info))
        self.assertNotIn('tel:',text_for('pulse_contact_whatsapp',info))
        self.assertIsNone(requested('Não quero ligar'))
        self.assertIsNone(requested('Posso ligar para meu filho durante o tratamento?'))
        self.assertIsNone(requested('Quantas ligações por semana o paciente recebe?'))


class ButtonsWebhook(WebhookTests):
    # Only new integration checks here; inherited tests are excluded by loader.
    def test_native_contact_menu_and_selected_button_use_existing_deduplication(self):
        payload=self.payload();message=payload['entry'][0]['changes'][0]['value']['messages'][0]
        message['text']['body']='Qual telefone para ligar?'
        self.assertEqual(self.post(payload).status_code,200)
        self.generate.assert_not_called()
        self.assertTrue(self.deliver.call_args.kwargs['contact_menu'])
        self.deliver.reset_mock()
        message['id']='contact-button-event';message['type']='interactive'
        message.pop('text');message['interactive']={'type':'button_reply','button_reply':{'id':'pulse_contact_whatsapp','title':'Abrir WhatsApp'}}
        for _ in range(2):self.assertEqual(self.post(payload).status_code,200)
        self.deliver.assert_awaited_once()
        self.assertIn('https://wa.me/5581989927699',self.deliver.call_args.args[1])
        self.assertNotIn('tel:',self.deliver.call_args.args[1])


def load_tests(loader,tests,pattern):
    suite=loader.loadTestsFromTestCase(Channels)
    suite.addTest(ButtonsWebhook('test_native_contact_menu_and_selected_button_use_existing_deduplication'))
    return suite
