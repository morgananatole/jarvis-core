import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from relationship_memory import review


class RelationReviewTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SimpleNamespace()
        self.db.contacts = SimpleNamespace(
            find_one=AsyncMock(return_value={"_id": "private-key",
                "relationship": {"issue_open": True}}),
            update_one=AsyncMock(return_value=SimpleNamespace(matched_count=1)),
        )

    async def test_real_operator_can_confirm_resolution_once(self):
        result = await review(self.db, 3, "resolve", "device:operator")
        self.assertEqual(result["action"], "resolved")
        filter_, changes = self.db.contacts.update_one.call_args.args
        self.assertEqual(filter_["relationship.issue_open"], True)
        self.assertFalse(changes["$set"]["relationship.issue_open"])
        self.assertEqual(changes["$set"]["relationship.reviewed_by"], "device:operator")
        self.assertNotIn("$push", changes)  # Do not fabricate customer's own words.

    async def test_non_owner_cannot_erase_memory(self):
        with self.assertRaisesRegex(ValueError, "owner_only"):
            await review(self.db, 3, "clear", "device:operator")
        self.db.contacts.update_one.assert_not_awaited()

    async def test_owner_can_erase_notes_not_message_history(self):
        result = await review(self.db, 3, "clear", "owner")
        self.assertEqual(result["action"], "cleared")
        self.assertEqual(self.db.contacts.update_one.call_args.args[1],
                         {"$unset": {"relationship": ""}})

    async def test_duplicate_resolution_is_not_registered(self):
        self.db.contacts.update_one.return_value = SimpleNamespace(matched_count=0)
        with self.assertRaisesRegex(ValueError, "relationship_changed_reload"):
            await review(self.db, 3, "resolve", "owner")

    async def test_no_issue_cannot_be_marked_resolved(self):
        self.db.contacts.find_one.return_value = {"_id": "key", "relationship": {}}
        with self.assertRaisesRegex(ValueError, "no_open_relationship_issue"):
            await review(self.db, 3, "resolve", "owner")

    async def test_missing_client_is_not_created(self):
        self.db.contacts.find_one.return_value = None
        with self.assertRaisesRegex(ValueError, "contact_not_found"):
            await review(self.db, 3, "resolve", "owner")

    async def test_invalid_action_never_touches_data(self):
        with self.assertRaisesRegex(ValueError, "invalid_relationship_action"):
            await review(self.db, 3, "send_marketing", "owner")
        self.db.contacts.find_one.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
