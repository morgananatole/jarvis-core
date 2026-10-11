"""Regression tests: one utterance may contain multiple customer signals."""
import unittest
from datetime import datetime, timedelta, timezone

from relationship_memory import observe, observe_all, update_relation


class MultiSignalTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)

    def test_praise_and_preference_are_both_saved(self):
        utterance = "Gostei muito do atendimento, mas prefiro conversar por mensagens."
        signals = observe_all(utterance)
        self.assertEqual({s["kind"] for s in signals}, {"praise", "messages"})
        relation = update_relation({}, "message-1", utterance, self.now)
        self.assertEqual({s["kind"] for s in relation["moments"]}, {"praise", "messages"})
        self.assertEqual(relation["contact_preference"]["kind"], "messages")
        self.assertFalse(relation["issue_open"])

    def test_negative_praise_not_mistaken_for_positive(self):
        signals = observe_all("Não gostei muito do atendimento, prefiro mensagens.")
        self.assertNotIn("praise", [x["kind"] for x in signals])
        self.assertIn("messages", [x["kind"] for x in signals])

    def test_message_preference_variants_preserve_literal_evidence(self):
        for verb in ("conversar", "falar", "receber contato"):
            for channel in ("por", "via"):
                for noun in ("mensagem", "mensagens"):
                    preference = f"prefiro {verb} {channel} {noun}"
                    with self.subTest(preference=preference):
                        utterance = f"Gostei muito do atendimento, mas {preference}."
                        cues = observe_all(utterance)
                        self.assertEqual([cue["kind"] for cue in cues],
                                         ["praise", "messages"])
                        self.assertEqual(cues[1]["evidence"], preference)
                        relation = update_relation({}, "variant", utterance, self.now)
                        self.assertEqual(relation["contact_preference"]["evidence"],
                                         preference)
                        self.assertEqual(observe_all(f"Não {preference}."), [])

    def test_unresolved_problem_not_erased_by_praise(self):
        earlier = update_relation({}, "message-1", "Ninguém me respondeu.", self.now)
        next_ = update_relation({"relationship": earlier}, "message-2",
                               "Gostei muito do atendimento, prefiro mensagens.",
                               self.now + timedelta(hours=1))
        self.assertTrue(next_["issue_open"])
        self.assertEqual(next_["last_problem"]["source_message_id"], "message-1")

    def test_neutral_text_does_not_invent_sentiment(self):
        self.assertEqual(observe_all("Quais são os horários disponíveis?"), [])
        self.assertIsNone(observe("Quais são os horários disponíveis?"))

    def test_backward_compatible_adapter_prioritizes_complaint(self):
        message = "Gostei do atendimento, mas ninguém me respondeu ontem."
        self.assertEqual(observe(message)["kind"], "complaint")


if __name__ == "__main__":
    unittest.main()
