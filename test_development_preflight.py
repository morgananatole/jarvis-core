import unittest
from dataclasses import replace
from development_preflight import IntegrationEvidence, assess, read_ready


class PreflightTests(unittest.TestCase):
    def test_ready_does_not_prove_official_transport(self):
        result = assess(IntegrationEvidence(configured=True, storage_available=True, reply_mode="test"))
        self.assertTrue(result["configuration_ready"])
        self.assertFalse(result["official_transport_verified"])
        self.assertFalse(result["intelligent_service_verified"])
        self.assertIn("delivery", [p["check"] for p in result["pending"]])

    def test_partial_transport_never_promoted(self):
        evidence = IntegrationEvidence(configured=True, storage_available=True,
            official_phone_configured=True, webhook_subscription_confirmed=True,
            inbound_confirmed=True, delivery_confirmed=True, reply_mode="test")
        self.assertTrue(assess(evidence)["official_transport_verified"])
        self.assertFalse(assess(evidence)["intelligent_service_verified"])
        for key in ("configured", "storage_available", "official_phone_configured",
                    "webhook_subscription_confirmed", "inbound_confirmed", "delivery_confirmed"):
            with self.subTest(key=key):
                self.assertFalse(assess(replace(evidence, **{key: False}))["official_transport_verified"])

    def test_ai_requires_observed_ai_reply(self):
        evidence = IntegrationEvidence(configured=True, storage_available=True,
            official_phone_configured=True, webhook_subscription_confirmed=True,
            inbound_confirmed=True, delivery_confirmed=True, reply_mode="openai")
        self.assertFalse(assess(evidence)["intelligent_service_verified"])
        self.assertTrue(assess(replace(evidence, ai_reply_confirmed=True))["intelligent_service_verified"])

    def test_urls_cannot_contain_secrets(self):
        for url in ("http://example.com/ready", "https://user:secret@example.com/ready",
                    "https://example.com/ready?token=secret", "https://example.com/ready#secret",
                    "https://example.com/other"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                read_ready(url)


if __name__ == "__main__":
    unittest.main()
