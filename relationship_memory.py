"""Grounded relationship memory for the PULSE business assistant.

Only explicit customer statements may become relationship cues. The assistant
must not invent goodwill, promises, dissatisfaction, or consent from a score.
No outbound message is sent by this module.
"""
import re
import unicodedata
from datetime import datetime, timedelta, timezone

# Conservative phrases; feedback is *reported*, not independently verified.
CUES = (
    ("complaint", (
        r"\bnao (?:resolveram|foi resolvido|conseguiram resolver|me responderam|recebi resposta)\b",
        r"\b(?:fui mal atendid[oa]|me deixaram esperando|ninguem me respondeu)\b",
        r"\b(?:tive um problema|tivemos um problema|houve um problema) (?:com o atendimento|com a empresa|com voces)\b",
        r"\b(?:nao cumpriram o combinado|estou insatisfeit[oa] com o atendimento)\b",
        r"\b(?:nao (?:esta|ta) resolvido|continua sem solucao|nao houve solucao)\b",
    )),
    ("resolved", (
        r"\b(?:agora (?:esta|ta|foi) resolvido|problema (?:foi )?resolvido)\b",
        r"\b(?:conseguimos resolver|deu tudo certo com (?:o atendimento|aquela questao))\b",
    )),
    ("praise", (
        r"\b(?:gostei (?:muito )?do atendimento|fui (?:muito )?bem atendid[oa])\b",
        r"\b(?:atendimento (?:foi |esta )?(?:otimo|excelente|maravilhoso))\b",
        r"\b(?:muito obrigad[oa] pelo atendimento|agradeco (?:muito )?o atendimento)\b",
    )),
    ("no_calls", (
        r"\b(?:nao quero (?:receber )?ligac(?:ao|oes)|prefiro que nao me ligu(?:em|e))\b",
    )),
    ("messages", (
        r"\b(?:prefiro (?:conversar|falar|receber contato) (?:por|via) mensagem|prefiro mensagens)\b",
    )),
    ("calls", (
        r"\b(?:prefiro (?:conversar|falar) por telefone|prefiro que me ligu(?:em|e))\b",
    )),
)
PATTERNS = tuple((kind, tuple(re.compile(pattern) for pattern in patterns))
                 for kind, patterns in CUES)
MAX_MOMENTS = 10
MAX_AGE_DAYS = 365


def plain(text):
    normalized = unicodedata.normalize("NFD", unicodedata.normalize("NFC", text).casefold())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def observe_all(text):
    """Capture independent feedback and channel preferences in one message."""
    if not isinstance(text, str) or not text.strip():
        return []
    original = unicodedata.normalize("NFC", text)
    folded = plain(original)
    found = []
    for kind, patterns in PATTERNS:
        matches = sorted((m for p in patterns for m in p.finditer(folded)),
                         key=lambda m: m.start())
        for match in matches:
            prefix = folded[max(0, match.start() - 13):match.start()]
            # A preceding "não" reverses praise, resolution and complaint.
            # "Não quero ligações" is itself a channel preference.
            if kind != "no_calls" and re.search(r"(?:\bnao|\bnunca|\bjamais)\s+$", prefix):
                continue
            found.append((match.start(), {"kind": kind,
                          "evidence": original[match.start():match.end()][:180]}))
            break
    found.sort(key=lambda entry: entry[0])
    return [cue for _, cue in found]


def observe(text):
    """Backward compatible one-cue adapter; complaint takes precedence."""
    cues = observe_all(text)
    return next((cue for cue in cues if cue["kind"] == "complaint"),
                cues[0] if cues else None)


def update_relation(profile, source_id, text, at):
    """Return a bounded, inspectable update (or None); caller persists it."""
    cues = observe_all(text)
    if not cues:
        return None
    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)
    old = profile.get("relationship") or {}
    moments = [{**cue, "source_message_id": source_id, "at": at} for cue in cues]
    keep = []
    for prior in old.get("moments", []):
        date = prior.get("at")
        if not isinstance(date, datetime) or date.tzinfo is None:
            continue
        if at - timedelta(days=MAX_AGE_DAYS) <= date <= at and prior.get("kind") in dict(CUES):
            keep.append(prior)
    relation = {
        "moments": (keep + moments)[-MAX_MOMENTS:],
        "updated_at": at,
        "issue_open": old.get("issue_open") is True,
    }
    for moment in moments:
        if moment["kind"] == "complaint":
            relation["issue_open"] = True
            relation["last_problem"] = moment
        elif moment["kind"] == "resolved":
            relation["issue_open"] = False
        elif moment["kind"] in ("no_calls", "messages", "calls"):
            relation["contact_preference"] = moment
    # Keep a prior reported problem, even if the latest feedback was positive.
    if "last_problem" in old and "last_problem" not in relation:
        relation["last_problem"] = old["last_problem"]
    return relation


def context(profile, now=None):
    """Small evidence-based memory; never a script or an instruction to the AI."""
    rel = profile.get("relationship") or {}
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=MAX_AGE_DAYS)
    moments = []
    for item in (rel.get("moments") or [])[-MAX_MOMENTS:]:
        date = item.get("at")
        if not isinstance(date, datetime) or date.tzinfo is None or not cutoff <= date <= now:
            continue
        kind, evidence = item.get("kind"), item.get("evidence")
        if kind not in dict(CUES) or not isinstance(evidence, str):
            continue
        moments.append({"kind": kind, "customer_words": evidence[:180],
                        "at": date.date().isoformat()})
    return {
        "reported_moments": moments[-5:],
        "unresolved_difficulty_reported": bool(rel.get("issue_open") and
            any(item["kind"] == "complaint" for item in moments)),
        "guidance": "Use apenas relatos comprovados, sem inventar afeto, culpa ou solucao.",
    }

async def review(db, number, action, actor):
    """Operator decision; no messaging side effect. Preserve who verified it."""
    if action not in ("resolve", "clear"):
        raise ValueError("invalid_relationship_action")
    profile = await db.contacts.find_one({"contact_no": number})
    if not profile:
        raise ValueError("contact_not_found")
    if action == "clear":
        if actor != "owner":
            raise ValueError("owner_only")
        await db.contacts.update_one({"_id": profile["_id"]},
                                     {"$unset": {"relationship": ""}})
        return {"action": "cleared", "reviewed": True}

    if not (profile.get("relationship") or {}).get("issue_open"):
        raise ValueError("no_open_relationship_issue")
    result = await db.contacts.update_one(
        {"_id": profile["_id"], "relationship.issue_open": True},
        {"$set": {"relationship.issue_open": False,
                  "relationship.reviewed_by": actor,
                  "relationship.reviewed_at": datetime.now(timezone.utc)}})
    if not result.matched_count:
        raise ValueError("relationship_changed_reload")
    return {"action": "resolved", "reviewed": True}
