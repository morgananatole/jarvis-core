"""Owner-only project continuity journal. Lives in MongoDB, not in a public repo."""
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
import re


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


    async def record(self, payload):
        """Append immutable classified entry; revisions refer to the previous directive."""
        data = validate_entry(payload)
        events = self.collection.database.project_continuity_entries
        item = {
            '_id': self.key + ':' + data['key'], 'owner': self.key,
            'kind': data['kind'], 'text': data['text'],
            'key': data['key'], 'revises': data['revises'],
            'created_at': datetime.now(timezone.utc),
        }
        if data['kind'] == 'revised_directive':
            previous = await events.find_one({'_id': self.key + ':' + data['revises'],
                                              'owner': self.key})
            if not previous or previous['kind'] not in ('directive', 'revised_directive'):
                raise ValueError('unknown_prior_directive')
        # Claim this predecessor atomically by MongoDB _id. Two competing revisions
        # cannot both replace the same directive, even across devices.
        if data['kind'] == 'revised_directive':
            links = self.collection.database.project_continuity_links
            link = {'_id': self.key + ':' + data['revises'],
                    'owner': self.key, 'next_key': data['key']}
            try:
                await links.insert_one(link)
            except DuplicateKeyError:
                previous_link = await links.find_one({'_id': link['_id'], 'owner': self.key})
                if not previous_link or previous_link['next_key'] != data['key']:
                    raise VersionConflict('directive_already_revised') from None
        try:
            await events.insert_one(item)
        except DuplicateKeyError:
            previous = await events.find_one({'_id': item['_id'], 'owner': self.key})
            if not previous or any(previous[k] != item[k] for k in ('kind', 'text', 'revises')):
                raise VersionConflict('continuity_entry_conflict')
            item = previous
        return self._event_public(item)

    @staticmethod
    def _event_public(item):
        return {k: item.get(k) for k in ('key', 'kind', 'text', 'revises', 'created_at')}

    async def entries(self):
        cursor = (self.collection.database.project_continuity_entries
                  .find({'owner': self.key}).sort('created_at', -1).limit(50))
        records = await cursor.to_list(length=50)
        superseded = {item['revises'] for item in records if item.get('revises')}
        return [{**self._event_public(item),
                 'active': item['key'] not in superseded}
                for item in records]


KINDS = {
    'idea': 'Ideia em avaliação',
    'directive': 'Diretriz aprovada pelo proprietário',
    'proposal': 'Sugestão técnica',
    'verified': 'Fato verificado',
    'revised_directive': 'Diretriz revisada pelo proprietário',
}


def validate_entry(payload):
    if not isinstance(payload, dict):
        raise ValueError('invalid_continuity_entry')
    kind = payload.get('kind')
    note = payload.get('text')
    key = payload.get('key')
    revises = payload.get('revises') or None
    if (kind not in KINDS or not isinstance(note, str) or not note.strip()
            or len(note) > 5000 or not isinstance(key, str)
            or not re.fullmatch(r'[a-zA-Z0-9_-]{12,72}', key)):
        raise ValueError('invalid_continuity_entry')
    if kind == 'revised_directive' and (
            not isinstance(revises, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{12,72}', revises)):
        raise ValueError('revision_reference_required')
    if kind != 'revised_directive' and revises is not None:
        raise ValueError('only_revised_directives_can_replace')
    return {'kind': kind, 'text': note.strip(), 'key': key, 'revises': revises}
