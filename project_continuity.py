"""Owner-only project continuity journal. Lives in MongoDB, not in a public repo."""
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError


MAX_CONTENT = 30000
MAX_HISTORY = 12


class VersionConflict(ValueError):
    pass


class ContinuityJournal:
    def __init__(self, database, business_id):
        self.collection = database.project_continuity
        self.key = business_id + ":owner"

    @staticmethod
    def _public(doc):
        return {
            "content": doc.get("content", ""),
            "revision": doc.get("revision", 0),
            "updated_at": doc.get("updated_at"),
            "history": [
                {"revision": h["revision"], "updated_at": h["updated_at"],
                 "excerpt": h.get("content", "")[:160]}
                for h in doc.get("history", [])[-MAX_HISTORY:]
            ],
        }

    async def current(self):
        saved = await self.collection.find_one({"_id": self.key})
        return self._public(saved or {})

    async def save(self, body):
        if not isinstance(body, dict):
            raise ValueError("invalid_continuity")
        content = body.get("content")
        revision = body.get("revision")
        if (not isinstance(content, str) or len(content) > MAX_CONTENT
                or not isinstance(revision, int) or isinstance(revision, bool)
                or revision < 0):
            raise ValueError("invalid_continuity")
        now = datetime.now(timezone.utc)
        existing = await self.collection.find_one({"_id": self.key})
        if existing is None:
            if revision != 0:
                raise VersionConflict("continuity_conflict")
            doc = {"_id": self.key, "content": content,
                   "revision": 1, "updated_at": now, "history": []}
            try:
                await self.collection.insert_one(doc)
            except DuplicateKeyError as exc:
                raise VersionConflict("continuity_conflict") from exc
            return self._public(doc)
        if existing["revision"] != revision:
            # An acknowledged write might have succeeded just before a network loss.
            # Reload the server copy rather than retrying and overwriting a newer edit.
            raise VersionConflict("continuity_conflict")
        snapshot = {"content": existing["content"],
                    "revision": existing["revision"],
                    "updated_at": existing["updated_at"]}
        result = await self.collection.update_one(
            {"_id": self.key, "revision": revision},
            {"$set": {"content": content, "updated_at": now},
             "$inc": {"revision": 1},
             "$push": {"history": {"$each": [snapshot], "$slice": -MAX_HISTORY}}})
        if not result.matched_count:
            raise VersionConflict("continuity_conflict")
        new_doc = {"content": content, "revision": revision + 1,
                   "updated_at": now,
                   "history": (existing.get("history", []) + [snapshot])[-MAX_HISTORY:]}
        return self._public(new_doc)
