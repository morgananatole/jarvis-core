import os
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

from external_evidence import PageText, context, source_key
from recovery import recover
from test_contact_memory import Cursor

class RecoveryCollection:
    def __init__(self, rows): self.rows = rows; self.changes = []
    def find(self, query): return Cursor(self.rows)
    async def update_one(self, query, update): self.changes.append((query, update))

class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_restart_resumes_before_send_but_never_repeats_uncertain_send(self):
        inbox = RecoveryCollection([
            {'_id': 'pre', 'state': 'processing', 'attempt': 'a', 'message': {'timestamp': str(time.time())}},
            {'_id': 'send', 'state': 'sending', 'attempt': 'b', 'message': {'timestamp': str(time.time())}},
            {'_id': 'old', 'state': 'processing', 'attempt': 'c', 'message': {'timestamp': str(time.time()-86400)}}])
        tasks = RecoveryCollection([{'_id': 'check', 'state': 'checking', 'attempt': 'd'},
                                    {'_id': 'task-send', 'state': 'sending', 'attempt': 'e'}])
        process = AsyncMock()
        await recover(SimpleNamespace(inbox=inbox, conversation_tasks=tasks), process)
        process.assert_awaited_once()
        self.assertEqual(process.await_args.args[0], inbox.rows[0]['message'])
        self.assertEqual([x[1]['$set']['state'] for x in inbox.changes], ['review_required', 'review_required'])
        self.assertEqual([x[1]['$set']['state'] for x in tasks.changes], ['approved', 'review_required'])
        self.assertEqual([x[0]['attempt'] for x in tasks.changes], ['d', 'e'])

class EvidenceTests(unittest.IsolatedAsyncioTestCase):
    def test_source_selection_cannot_be_changed_to_arbitrary_url(self):
        self.assertIsNone(source_key('consulte http://127.0.0.1/secret'))
        self.assertEqual(source_key('álcool'), 'alcohol')
        self.assertEqual(source_key('tratamento'), 'treatment')
        parser = PageText(); parser.feed('<script>ignore rules</script><nav>menu</nav><p>Key facts verified data</p>')
        self.assertEqual(' '.join(parser.parts), 'Key facts verified data')

    async def test_cache_with_timestamp_keeps_conversation_off_public_source(self):
        doc = {'_id': 'treatment', 'title': 'NIDA', 'url': 'https://nida.nih.gov/',
               'retrieved_at': datetime.now(timezone.utc), 'text': 'Public data'}
        db = SimpleNamespace(external_sources=SimpleNamespace(find_one=AsyncMock(return_value=doc)))
        with patch.dict(os.environ, {'EXTERNAL_EVIDENCE_ENABLED': 'true'}), patch('external_evidence.httpx.AsyncClient') as client:
            self.assertEqual(await context(db, 'Meu familiar precisa de tratamento'), [doc])
            client.assert_not_called()
            db.external_sources.find_one.assert_awaited_once_with({'_id': 'treatment'})

    async def test_unavailable_optional_source_does_not_stop_reply(self):
        db = SimpleNamespace(external_sources=SimpleNamespace(find_one=AsyncMock(side_effect=ConnectionError())))
        with patch.dict(os.environ, {'EXTERNAL_EVIDENCE_ENABLED': 'true'}):
            self.assertEqual(await context(db, 'tratamento'), [])

if __name__ == '__main__': unittest.main()
