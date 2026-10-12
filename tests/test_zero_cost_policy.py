import unittest
from zero_cost_policy import evaluate_outbound


class ZeroCostPolicyTests(unittest.TestCase):
    def test_blocks_unverified_free(self):
        result = evaluate_outbound(transport="official_cloud_api", category="service",
                                   verified_free=False, customer_opt_in=True)
        self.assertFalse(result.allowed)
        self.assertTrue(result.requires_human)

    def test_blocks_unofficial_automation(self):
        result = evaluate_outbound(transport="whatsapp_web_unofficial", category="service",
                                   verified_free=True, customer_opt_in=True)
        self.assertFalse(result.allowed)

    def test_blocks_without_consent(self):
        result = evaluate_outbound(transport="official_cloud_api", category="service",
                                   verified_free=True, customer_opt_in=False)
        self.assertFalse(result.allowed)

    def test_allows_verified_free_service(self):
        result = evaluate_outbound(transport="official_cloud_api", category="service",
                                   verified_free=True, customer_opt_in=True)
        self.assertTrue(result.allowed)

    def test_requires_review_for_marketing(self):
        result = evaluate_outbound(transport="official_cloud_api", category="marketing",
                                   verified_free=True, customer_opt_in=True)
        self.assertFalse(result.allowed)
        self.assertTrue(result.requires_human)
