"""Contrato de integração: saudação não pode ser habilitada por padrão."""
import unittest
from pathlib import Path

class InstantGreetingIntegrationTests(unittest.TestCase):
    def test_feature_flag_fail_closed(self):
        main = Path(__file__).with_name("main.py").read_text()
        self.assertIn("os.getenv('NOVA_VIDA_INSTANT_GREETING', 'false')", main)
        self.assertIn("prior_inbound_count=profile.get('inbound_count', 0)-1", main)
        self.assertIn("not profile.get('human_mode')", main)
        self.assertIn("not profile.get('do_not_contact')", main)
        self.assertIn("not reason", main)
