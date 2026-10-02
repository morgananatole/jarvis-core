import hashlib
import hmac
import json
import time
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError
import main


class Inbox:
    def __init__(self):
        self.jobs = {}

    async def insert_one(self, job):
        if job['_id'] in self.jobs:
            raise DuplicateKeyError('duplicate')
        self.jobs[job['_id']] = dict(job)

    async def update_one(self, query, update):
        self.jobs[query['_id']].update(update['$set'])


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(main.os.environ, {key: 'test-value' for key in main.REQUIRED}, clear=True)
        self.env.start()
        self.client = TestClient(main.app)
        self.inbox = Inbox()
        main.inbox = self.inbox
        self.ai = patch.object(main, 'generate_reply', new_callable=AsyncMock)
        self.send = patch.object(main, 'send_reply', new_callable=AsyncMock)
        self.generate = self.ai.start()
        self.deliver = self.send.start()
        self.generate.return_value = 'Olá, sou o assistente virtual.'
        self.deliver.return_value = 'outbound-test-id'

    def tearDown(self):
        self.ai.stop()
        self.send.stop()
        self.env.stop()
        main.inbox = None

    def post(self, payload, valid=True):
        body = json.dumps(payload).encode()
        signature = 'sha256=' + hmac.new(b'test-value', body, hashlib.sha256).hexdigest()
        return self.client.post('/webhook', content=body, headers={
            'x-hub-signature-256': signature if valid else 'bad'})

    def payload(self, phone='test-value', kind='text', timestamp=None):
        return {'entry': [{'changes': [{'value': {
            'metadata': {'phone_number_id': phone},
            'messages': [{'id': 'inbound-test-id', 'from': 'authorized-test-sender',
                          'timestamp': str(timestamp or time.time()),
                          'type': kind, 'text': {'body': 'Olá'}}]}}]}]}

    def test_challenge_and_rejection(self):
        response = self.client.get('/webhook', params={
            'hub.mode': 'subscribe', 'hub.verify_token': 'test-value', 'hub.challenge': '123'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, '123')
        self.assertEqual(self.client.get('/webhook').status_code, 403)

    def test_bad_signature_never_calls_providers(self):
        self.assertEqual(self.post(self.payload(), False).status_code, 403)
        self.generate.assert_not_called()
        self.deliver.assert_not_called()

    def test_reply_and_duplicate(self):
        for _ in range(2):
            self.assertEqual(self.post(self.payload()).status_code, 200)
        self.generate.assert_awaited_once_with('Olá')
        self.deliver.assert_awaited_once_with('authorized-test-sender', self.generate.return_value)
        self.assertEqual(self.inbox.jobs['inbound-test-id']['state'], 'sent')

    def test_ignored_events(self):
        for payload in [self.payload(phone='other'), self.payload(kind='image'),
                        self.payload(timestamp=time.time() - 86400), {'entry': []}]:
            self.assertEqual(self.post(payload).status_code, 200)
        self.generate.assert_not_called()

    def test_uncertain_send_not_repeated(self):
        self.deliver.side_effect = TimeoutError()
        for _ in range(2):
            self.assertEqual(self.post(self.payload()).status_code, 200)
        self.deliver.assert_awaited_once()
        self.assertEqual(self.inbox.jobs['inbound-test-id']['state'], 'review_required')

    def test_missing_config_does_not_acknowledge(self):
        main.os.environ.pop('OPENAI_API_KEY')
        self.assertEqual(self.post(self.payload()).status_code, 503)
        self.assertEqual(self.client.get('/health').status_code, 200)
        self.assertEqual(self.client.get('/ready').status_code, 503)

    def test_database_failure_does_not_acknowledge(self):
        self.inbox.insert_one = AsyncMock(side_effect=ConnectionError())
        self.assertEqual(self.post(self.payload()).status_code, 503)
        self.generate.assert_not_called()

    def test_malformed_json(self):
        self.assertEqual(self.post(['wrong']).status_code, 400)

    def test_invalid_database_config_keeps_health_available(self):
        with patch.object(main, 'AsyncIOMotorClient', side_effect=main.InvalidURI('redacted')):
            with TestClient(main.app) as client:
                self.assertEqual(client.get('/health').status_code, 200)
                response = client.get('/ready')
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['storage_error'], 'invalid_connection_string')
                self.assertEqual(self.post(self.payload()).status_code, 503)
