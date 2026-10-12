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
        "instant_greeting_enabled": env.get("NOVA_VIDA_INSTANT_GREETING", "false").lower() == "true",
        "typing_indicator_enabled": env.get("WHATSAPP_TYPING_INDICATOR_ENABLED", "false").lower() == "true",
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
    # Read the Meta delivery receipt linked to the most recent inbound message.
    # No message text, phone, external message ID or token leaves this route.
    last_receipt = None
    last_outbound = latest.get("outbound_id") if latest else None
    if last_outbound and latest.get("state") == "sent":
        last_receipt = await database.delivery_receipts.find_one(
            {"_id": last_outbound},
            {"delivery_read_at": 1, "delivery_delivered_at": 1,
             "delivery_failed_at": 1, "delivery_sent_at": 1, "_id": 0})
    if not last_outbound or (latest and latest.get("state") != "sent"):
        receipt_status = "no_accepted_reply"
    elif last_receipt and last_receipt.get("delivery_read_at"):
        receipt_status = "read"
    elif last_receipt and last_receipt.get("delivery_delivered_at"):
        receipt_status = "delivered"
    elif last_receipt and last_receipt.get("delivery_failed_at"):
        receipt_status = "failed"
    elif last_receipt and last_receipt.get("delivery_sent_at"):
        receipt_status = "sent_not_confirmed_delivered"
    else:
        receipt_status = "awaiting_delivery_receipt"
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
        "recent_message_meta_accepted": bool(last_outbound and latest.get("state") == "sent") if latest else False,
        "recent_message_delivery_state": receipt_status,
        "review_required_in_last_40": sum(x.get("state") == "review_required" for x in rows),
        "recent_jobs_checked": len(rows),
        "message_delivery_verified": receipt_status in ("delivered", "read"),
        "registration_changed": False,
        "note": (
            "Status calculado pelo histórico local. Um envio aceito pela Meta nao prova entrega; "
            "se nenhum evento aparece, isso nao prova desconexao. "
            "Nao desregistre o numero para tentar coexistencia."
        ),
    }
