import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from relationship_memory import observe, update_relation, context
from contact_memory import ContactMemory, conversation_plan
from test_contact_memory import Database


class RelationshipSignalsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 10, 17, 0, tzinfo=timezone.utc)

    def test_explicit_problem_with_literal_evidence(self):
        cue = observe("Olá, ninguém me respondeu ontem. Podem conferir?")
        self.assertEqual(cue["kind"], "complaint")
        self.assertEqual(cue["evidence"], "ninguém me respondeu")
        self.assertNotIn("Podem conferir", cue["evidence"])

    def test_explicit_praise_not_invented_from_neutral_words(self):
        self.assertIsNone(observe("Oi. Quanto custa?"))
        self.assertIsNone(observe("Obrigado, vou verificar."))
        self.assertEqual(observe("Gostei muito do atendimento")["kind"], "praise")

    def test_problem_remains_open_after_praise_but_resolution_closes(self):
        problem = update_relation({}, "msg1", "Fui mal atendido.", self.now)
        self.assertTrue(problem["issue_open"])
        thanks = update_relation({"relationship": problem}, "msg2",
                                 "Gostei do atendimento hoje.", self.now + timedelta(days=1))
        self.assertTrue(thanks["issue_open"])  # gratitude is not proof of resolution
        self.assertEqual(len(thanks["moments"]), 2)
        resolved = update_relation({"relationship": thanks}, "msg3",
                                   "Agora está resolvido.", self.now + timedelta(days=2))
        self.assertFalse(resolved["issue_open"])
        self.assertEqual(len(resolved["moments"]), 3)

    def test_contact_preferences_are_respected_as_reported(self):
        self.assertEqual(observe("Não quero ligações")["kind"], "no_calls")
        self.assertEqual(observe("Prefiro falar por mensagem")["kind"], "messages")
        self.assertEqual(observe("Prefiro falar por telefone")["kind"], "calls")

    def test_only_recent_grounded_moments_enter_context(self):
        old = update_relation({}, "old", "Fui mal atendido.", self.now)
        stale = context({"relationship": old}, self.now + timedelta(days=366))
        self.assertFalse(stale["unresolved_difficulty_reported"])
        self.assertEqual(stale["reported_moments"], [])
        current = context({"relationship": old}, self.now + timedelta(days=1))
        self.assertTrue(current["unresolved_difficulty_reported"])
        self.assertEqual(current["reported_moments"][0]["customer_words"], "Fui mal atendido")

    def test_bounded_history_and_no_deductions(self):
        relation = {}
        for i in range(15):
            at = self.now + timedelta(minutes=i)
            relation = update_relation({"relationship": relation}, str(i),
                                       "Gostei do atendimento", at)
        self.assertEqual(len(relation["moments"]), 10)
        self.assertEqual(relation["moments"][-1]["source_message_id"], "14")
        self.assertIsNone(update_relation({"relationship": relation}, "neutral",
                                           "Quero saber os horários", self.now))


class RelationshipIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.patch = patch.dict(os.environ, {"META_APP_SECRET": "test-relationship-secret"})
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.db = Database()
        self.memory = ContactMemory(self.db)
        self.now = datetime.now(timezone.utc)
        self.phone = "5584981584252"

    async def test_followup_and_ai_context_remember_reported_problem(self):
        await self.memory.record_inbound(self.phone, "m1", "Não recebi resposta.",
                                         self.now.timestamp())
        profile = await self.memory.ensure(self.phone)
        self.assertTrue(profile["relationship"]["issue_open"])
        self.assertEqual(profile["relationship"]["moments"][0]["source_message_id"], "m1")
        ready = json.loads(await self.memory.context(self.phone))
        self.assertTrue(ready["relationship"]["unresolved_difficulty_reported"])
        plan = conversation_plan(profile, self.now)
        self.assertIn("dificuldade relatada", plan["purpose"])
        self.assertTrue(self.db.conversation_tasks.docs[profile["_id"] + ":next"]
                        ["requires_review"])

    async def test_duplicate_message_does_not_duplicate_memory(self):
        for _ in range(2):
            await self.memory.record_inbound(self.phone, "m1",
                                             "Fui mal atendida", self.now.timestamp())
        profile = await self.memory.ensure(self.phone)
        self.assertEqual(len(profile["relationship"]["moments"]), 1)

    async def test_resolution_removes_open_issue_without_erasing_history(self):
        await self.memory.record_inbound(self.phone, "m1", "Não recebi resposta",
                                         self.now.timestamp())
        await self.memory.record_inbound(self.phone, "m2", "Agora está resolvido",
                                         (self.now + timedelta(seconds=1)).timestamp())
        profile = await self.memory.ensure(self.phone)
        self.assertFalse(profile["relationship"]["issue_open"])
        self.assertEqual(len(profile["relationship"]["moments"]), 2)


if __name__ == "__main__":
    unittest.main()
