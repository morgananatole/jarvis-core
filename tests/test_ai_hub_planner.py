import os
import unittest
from decimal import Decimal
from unittest.mock import patch
from ai_hub.planner import Provider, select_provider

class TestPlanner(unittest.TestCase):
    def setUp(self):
        self.providers = [
            Provider("free-low-quality", 50, Decimal("0")),
            Provider("local-good", 90, Decimal("0"), local=True),
            Provider("paid-good", 95, Decimal("0.05")),
        ]

    def test_default_disabled(self):
        with patch.dict(os.environ, {"JARVIS_AI_HUB_ENABLED": "false"}):
            self.assertEqual(select_provider(self.providers)["status"], "disabled")

    def test_choose_free_with_quality(self):
        with patch.dict(os.environ, {"JARVIS_AI_HUB_ENABLED": "true"}):
            result = select_provider(self.providers)
            self.assertEqual(result["selected"], "local-good")
            self.assertEqual(result["status"], "planned_only")

    def test_paid_requires_budget(self):
        with patch.dict(os.environ, {"JARVIS_AI_HUB_ENABLED": "true"}):
            result = select_provider([self.providers[-1]], budget=Decimal("0"))
            self.assertEqual(result["status"], "requires_approval_or_alternative")

if __name__ == "__main__":
    unittest.main()
