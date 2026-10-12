"""Official Meta WhatsApp typing indicator; opt-in and best-effort.

This only marks an incoming message read and signals that a response is
being prepared. It does not simulate a human operator.
"""
import os
import httpx

async def send_typing_indicator(message_id):
    if os.getenv("WHATSAPP_TYPING_INDICATOR_ENABLED", "false").lower() != "true":
        return False
    if not isinstance(message_id, str) or not message_id.startswith("wamid."):
        return False
    required = ("META_GRAPH_VERSION", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN")
    if not all(os.getenv(k) for k in required):
        return False
    url = ("https://graph.facebook.com/" + os.environ["META_GRAPH_VERSION"]
           + "/" + os.environ["WHATSAPP_PHONE_NUMBER_ID"] + "/messages")
    payload = {"messaging_product": "whatsapp", "status": "read",
               "message_id": message_id, "typing_indicator": {"type": "text"}}
    try:
        async with httpx.AsyncClient(timeout=4) as client:
            result = await client.post(url, json=payload, headers={
                "Authorization": "Bearer " + os.environ["WHATSAPP_ACCESS_TOKEN"]})
        return result.is_success
    except httpx.HTTPError:
        return False
