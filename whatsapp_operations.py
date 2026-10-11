"""Owner-only, read-only operational WhatsApp summary. Never modifies Meta registration."""
import os
from datetime import datetime, timezone


def mode_status(env=None):
    env = env or os.environ
    mode = env.get("JARVIS_REPLY_MODE", "openai")
    test_only = mode == "test" or (mode == "hybrid"
                                  and env.get("AI_ALLOWED_TEST_ONLY", "true") == "true")
    return {
        "reply_mode": mode,
        "test_only": test_only,
        "followups_automatic_enabled": env.get("CONVERSATION_EXECUTOR_ENABLED", "false") == "true",
        "paid_fallback_configured": (
            mode == "hybrid" and env.get("AI_PAID_FALLBACK_ENABLED", "false") == "true"
        ),
    }


async def operations(database):
    if database is None:
        raise ValueError("database_unavailable")
    # Only essential fields are queried; no name, phone, message body or tokens.
    rows = await database.inbox.find(
        {}, {"state": 1, "received_at": 1, "outbound_id": 1, "_id": 0}
    ).sort("received_at", -1).limit(40).to_list(40)
    rows = [x for x in rows if isinstance(x, dict)]
    latest = next((x for x in rows if isinstance(x.get("received_at"), (int, float))), None)
    accepted = next((x for x in rows if x.get("state") == "sent" and x.get("outbound_id")), None)
    def date_of(record):
        if not record:
            return None
        stamp = record.get("received_at")
        return datetime.fromtimestamp(stamp, timezone.utc).isoformat() if (
            isinstance(stamp, (int, float)) and 0 < stamp < 4e9
        ) else None
    return {
        **mode_status(),
        "most_recent_inbound_at": date_of(latest),
        "last_meta_accepted_reply_inbound_at": date_of(accepted),
        "recent_message_state": latest.get("state") if latest else None,
        "review_required_in_last_40": sum(x.get("state") == "review_required" for x in rows),
        "recent_jobs_checked": len(rows),
        "message_delivery_verified": False,
        "registration_changed": False,
        "note": (
            "Status calculado pelo histórico local. Um envio aceito pela Meta nao prova entrega; "
            "se nenhum evento aparece, isso nao prova desconexao. "
            "Nao desregistre o numero para tentar coexistencia."
        ),
    }
