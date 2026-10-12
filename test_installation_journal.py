import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from installation_journal import plan, base_url, append, audit, probe


class InstallationJournalTests(unittest.TestCase):
    def test_second_device_never_restarts_meta(self):
        for state in ('new', 'business_app', 'cloud_api', 'unknown'):
            result = plan('new_device', state, 'coexistence')
            self.assertFalse(result['meta_setup_required'])
            self.assertNotIn('meta_signup', result['steps'])
            self.assertIn('device', result['steps'])

    def test_cloud_api_reset_is_blocked_until_migration_plan(self):
        result = plan('current_number', 'cloud_api', 'coexistence')
        self.assertEqual(result['blocker'], 'api_only_to_business_app_path_not_verified')
        self.assertIn('migration_plan', result['steps'])
        self.assertEqual(plan('new_company', 'business_app', 'coexistence')['path'], 'business_app_eligibility_first')

    def test_secret_urls_and_free_text_are_rejected(self):
        for value in ('https://user:secret@example.com', 'https://example.com/?token=secret',
                      'https://example.com/#secret', 'http://example.com', 'https://example.com/secret'):
            with self.assertRaises(ValueError):
                base_url(value)
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'journal.jsonl'
            for values in ({'token': 'SECRET'}, {'verified': 'SECRET'}, {'http_status': True}):
                with self.assertRaises(ValueError):
                    append(target, 'a' * 32, 'delivery', 'passed', values)
            self.assertFalse(target.exists())

    def test_private_append_preserves_steps_and_never_promotes_report_to_probe(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'journal.jsonl'
            append(target, 'a' * 32, 'meta_signup', 'blocked', {'meta_error_code': 2655122})
            append(target, 'a' * 32, 'delivery', 'passed', {'verified': True}, 3)
            rows = [json.loads(line) for line in target.read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]['evidence']['meta_error_code'], 2655122)
            self.assertEqual(rows[1]['source'], 'operator_report')
            self.assertEqual(os.stat(target).st_mode & 0o777, 0o600)
            link = Path(root) / 'link.jsonl'
            link.symlink_to(target)
            with self.assertRaises(OSError):
                append(link, 'a' * 32, 'delivery', 'passed')
            self.assertEqual(len(target.read_text().splitlines()), 2)

    def test_http_passes_do_not_claim_sale_or_sdk_or_message_delivery(self):
        with tempfile.TemporaryDirectory() as root, patch('installation_journal.probe', return_value=('passed', {'http_status': 200})):
            result = audit('https://example.com', 'new_company', 'business_app', 'coexistence',
                           Path(root) / 'journal.jsonl')
        self.assertFalse(result['ready_to_sell_verified'])
        self.assertFalse(result['registration_changed'])
        for step in ('delivery', 'inbound', 'sdk_preview', 'isolation'):
            self.assertIn(step, result['still_requires_real_evidence'])

    def test_network_failure_never_logs_remote_error_body(self):
        with patch('installation_journal.build_opener', side_effect=RuntimeError('SECRET_REMOTE_VALUE')):
            self.assertEqual(probe('https://example.com', '/ready'), ('failed', {}))
        result = subprocess.run([sys.executable, 'scripts/installation_check.py', 'plan',
            '--case', 'SECRET_CUSTOMER_VALUE'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('SECRET_CUSTOMER_VALUE', result.stderr)
