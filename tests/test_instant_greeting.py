import unittest
from instant_greeting import GREETING, greeting_for_first_contact

class InstantGreetingTests(unittest.TestCase):
    def test_first_greeting(self):
        self.assertEqual(greeting_for_first_contact(business="nova_vida", inbound_text="Bom dia",
            prior_inbound_count=0), GREETING)
    def test_not_repeat(self):
        self.assertIsNone(greeting_for_first_contact(business="nova_vida", inbound_text="Oi",
            prior_inbound_count=1))
    def test_human_mode(self):
        self.assertIsNone(greeting_for_first_contact(business="nova_vida", inbound_text="Oi",
            prior_inbound_count=0, human_mode=True))
    def test_other_business(self):
        self.assertIsNone(greeting_for_first_contact(business="outra", inbound_text="Oi",
            prior_inbound_count=0))
    def test_urgent_or_human_request(self):
        for text in ("Socorro", "Quero atendente", "Emergência"):
            self.assertIsNone(greeting_for_first_contact(business="nova_vida",
                inbound_text=text, prior_inbound_count=0))
