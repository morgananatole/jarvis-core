import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from outreach_overview import contact_path
from template_service import send_template


class OutreachPaths(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.profile = {'phone': '5581999999999', 'facts': {
            'contact_permission': {'value': 'allowed'}}, 'last_inbound_at': self.now}
        self.env = patch.dict(os.environ, {
            'JARVIS_REPLY_MODE': 'hybrid', 'GROQ_API_KEY': 'synthetic',
            'AI_ALLOWED_TEST_ONLY': 'false'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_address_book_does_not_authorize_contact(self):
        self.profile['facts'] = {'contact_name': {'value': 'Synthetic'}}
        result = contact_path(self.profile, lambda _: True, self.now)
        self.assertEqual(result['contact_path'], 'obtain_opt_in')
        self.assertFalse(result['automatic_campaign_enabled_by_this_action'])

    def test_no_saved_number_requirement(self):
        result = contact_path(self.profile, lambda _: True, self.now)
        self.assertFalse(result['saved_number_required'])
        self.assertEqual(result['contact_path'], 'review_service_reply')

    def test_closed_window_waits_for_inbound_in_free_mode(self):
        self.profile['last_inbound_at'] = self.now - timedelta(days=3)
        self.assertEqual(contact_path(self.profile, lambda _: True, self.now)['contact_path'], 'await_inbound')

    def test_human_pause_and_opt_out_take_priority(self):
        self.profile['human_mode'] = True
        self.assertEqual(contact_path(self.profile, lambda _: True, self.now)['contact_path'], 'human_only')
        self.profile['do_not_contact'] = True
        self.assertEqual(contact_path(self.profile, lambda _: True, self.now)['contact_path'], 'do_not_contact')


class TemplateCostGate(unittest.IsolatedAsyncioTestCase):
    async def test_default_blocks_before_any_database_or_http(self):
        with patch.dict(os.environ, {'WHATSAPP_TEMPLATE_SEND_ENABLED': 'true',
                                     'WHATSAPP_TEMPLATE_MAX_PER_DAY': '100'}, clear=True):
            with patch('template_service.httpx.AsyncClient') as client:
                with self.assertRaisesRegex(ValueError, 'zero_cost_blocks_unverified_template'):
                    await send_template(None, {})
                client.assert_not_called()

    async def test_unknown_zero_cost_setting_fails_closed(self):
        with patch.dict(os.environ, {'WHATSAPP_ZERO_COST_ONLY': 'unknown'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'zero_cost_blocks_unverified_template'):
                await send_template(None, {})

    async def test_template_sender_independently_rejects_opt_out_and_pause(self):
        with patch.dict(os.environ, {'WHATSAPP_ZERO_COST_ONLY': 'false'}, clear=True):
            for profile in [{'human_mode': True}, {'do_not_contact': True}]:
                with self.assertRaisesRegex(ValueError, 'contact_not_available'):
                    await send_template(None, profile)
            with self.assertRaisesRegex(ValueError, 'contact_permission_required'):
                await send_template(None, {'facts': {}})

    async def test_explicit_paid_setting_does_not_enable_templates_by_itself(self):
        with patch.dict(os.environ, {'WHATSAPP_ZERO_COST_ONLY': 'false'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'template_send_disabled'):
                await send_template(None, {'facts': {'contact_permission': {'value': 'allowed'}}})


if __name__ == '__main__':
    unittest.main()
