"""Authenticated WhatsApp webhook with persistent duplicate protection."""
import hashlib
import hmac
import json
import logging
import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from pymongo.errors import DuplicateKeyError, InvalidURI, ConfigurationError, OperationFailure

log = logging.getLogger("jarvis")
REQUIRED = ("WHATSAPP_VERIFY_TOKEN", "META_APP_SECRET", "WHATSAPP_ACCESS_TOKEN",
            "WHATSAPP_PHONE_NUMBER_ID", "META_GRAPH_VERSION", "OPENAI_API_KEY",
            "OPENAI_MODEL", "MONGODB_URI", "JARVIS_INSTRUCTIONS")
inbox = None
storage_error = None


def missing():
    mode = os.getenv("JARVIS_REPLY_MODE", "openai")
    if mode not in ("openai", "test"):
        return ["JARVIS_REPLY_MODE"]
    required = REQUIRED
    if mode == "test":
        required = tuple(key for key in REQUIRED if key not in
                         ("OPENAI_API_KEY", "OPENAI_MODEL", "JARVIS_INSTRUCTIONS"))
        recipient = os.getenv("WHATSAPP_TEST_RECIPIENT", "")
        if not recipient.isascii() or not recipient.isdigit() or not 8 <= len(recipient) <= 15:
            return ["WHATSAPP_TEST_RECIPIENT"]
        destination = os.getenv("WHATSAPP_TEST_DESTINATION", recipient)
        if not destination.isascii() or not destination.isdigit() or not 8 <= len(destination) <= 15:
            return ["WHATSAPP_TEST_DESTINATION"]
    return [key for key in required if not os.getenv(key, "").strip()]


@asynccontextmanager
async def lifespan(app):
    global inbox, storage_error
    mongo = None
    inbox = None
    storage_error = None
    if os.getenv("MONGODB_URI"):
        try:
            mongo = AsyncIOMotorClient(os.environ["MONGODB_URI"], serverSelectionTimeoutMS=3000)
            inbox = mongo[os.getenv("MONGODB_DATABASE", os.getenv("DB_NAME", "jarvis"))].inbox
        except (InvalidURI, ConfigurationError, ValueError):
            storage_error = "invalid_connection_string"
            log.warning("MongoDB configuration invalid; integration remains disabled")
    try:
        yield
    finally:
        if mongo is not None:
            mongo.close()
        inbox = None


app = FastAPI(title="JARVIS Core", lifespan=lifespan)


@app.get("/")
@app.get("/health")
async def health():
    return {"service": "jarvis-core", "status": "ok"}


@app.get("/ready")
async def ready():
    absent = missing()
    storage = False
    error = storage_error
    if inbox is not None:
        try:
            await inbox.database.command("ping")
            storage = True
        except OperationFailure:
            error = "authentication_or_permission_failed"
        except Exception:
            error = "database_unreachable"
    return JSONResponse(status_code=200 if not absent and storage else 503,
                        content={"configured": not absent, "missing": absent,
                                 "storage_available": storage,
                                 "storage_error": error,
                                 "reply_mode": os.getenv("JARVIS_REPLY_MODE", "openai"),
                                 "note": "Does not verify Meta registration or API credentials"})


@app.get("/webhook")
async def verify(request: Request):
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Verification token not configured")
    query = request.query_params
    if (query.get("hub.mode") != "subscribe" or not query.get("hub.challenge")
            or not hmac.compare_digest(query.get("hub.verify_token", ""), expected)):
        raise HTTPException(403, "Verification failed")
    return PlainTextResponse(query["hub.challenge"])


async def generate_reply(text):
    if os.getenv("JARVIS_REPLY_MODE", "openai") == "test":
        return ("Sou o JARVIS, assistente virtual da Nova Vida. "
                "Recebi sua mensagem: este é um teste de conexão com resposta fixa, "
                "sem uso de IA paga. O atendimento automático ainda está em implantação.")
    async with AsyncOpenAI(timeout=35, max_retries=0) as client:
        result = await client.responses.create(
            model=os.environ["OPENAI_MODEL"], store=False,
            instructions=("Você é JARVIS, assistente virtual da Nova Vida. "
                          "Identifique-se como assistente virtual. Responda em português, "
                          "brevemente. Não invente preços, disponibilidade ou agendamentos. "
                          "Não faça diagnósticos nem solicite dados sensíveis de saúde. "
                          "Quando faltar informação, encaminhe para atendimento humano.\n"
                          + os.environ["JARVIS_INSTRUCTIONS"]),
            input=text[:6000], max_output_tokens=500)
        if not result.output_text.strip():
            raise RuntimeError("empty_ai_reply")
        return result.output_text.strip()[:4000]


async def send_reply(sender, text):
    if os.getenv("JARVIS_REPLY_MODE", "openai") == "test":
        if sender != os.getenv("WHATSAPP_TEST_RECIPIENT", ""):
            raise ValueError("unauthorized_test_recipient")
        sender = os.getenv("WHATSAPP_TEST_DESTINATION", sender)
    url = ("https://graph.facebook.com/" + os.environ["META_GRAPH_VERSION"]
           + "/" + os.environ["WHATSAPP_PHONE_NUMBER_ID"] + "/messages")
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(url, headers={
            "Authorization": "Bearer " + os.environ["WHATSAPP_ACCESS_TOKEN"]}, json={
                "messaging_product": "whatsapp", "to": sender,
                "type": "text", "text": {"body": text}})
        if response.is_error:
            try:
                code = response.json().get("error", {}).get("code")
            except (ValueError, AttributeError):
                code = None
            log.warning("Meta reply rejected: http_status=%s code=%s",
                        response.status_code, code if isinstance(code, int) else "unknown")
        response.raise_for_status()
        return response.json()["messages"][0]["id"]


async def process_message(message):
    if (os.getenv("JARVIS_REPLY_MODE", "openai") == "test"
            and message["from"] != os.getenv("WHATSAPP_TEST_RECIPIENT", "")):
        authorized = os.getenv("WHATSAPP_TEST_RECIPIENT", "")
        alias_match = (len(authorized) == 13 and authorized.startswith("55")
                       and authorized[4] == "9"
                       and message["from"] == authorized[:4] + authorized[5:])
        log.warning("Test sender rejected: digits=%s authorized_brazil_alias=%s",
                    len(message["from"]), alias_match)
        return
    log.warning("Authorized text received for configured phone")
    timestamp = float(message["timestamp"])
    if timestamp < time.time() - 23 * 3600 or timestamp > time.time() + 300:
        return
    job = {"_id": message["id"], "state": "processing",
           "received_at": timestamp}
    try:
        await inbox.insert_one(job)
    except DuplicateKeyError:
        return
    # A failed/uncertain job is held for human review, never blindly resent.
    try:
        reply = await generate_reply(message["text"]["body"])
        await inbox.update_one({"_id": job["_id"]}, {"$set": {"state": "sending"}})
        message_id = await send_reply(message["from"], reply)
        await inbox.update_one({"_id": job["_id"]}, {"$set": {
            "state": "sent", "outbound_id": message_id}})
    except Exception:
        log.warning("Reply failed or uncertain; manual review required")
        await inbox.update_one({"_id": job["_id"]}, {"$set": {"state": "review_required"}})


@app.post("/webhook")
async def receive(request: Request):
    secret = os.getenv("META_APP_SECRET", "")
    if not secret:
        raise HTTPException(503, "App secret not configured")
    body = await request.body()
    if len(body) > 1024 * 1024:
        raise HTTPException(413, "Payload too large")
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(request.headers.get("x-hub-signature-256", ""), signature):
        raise HTTPException(403, "Invalid signature")
    try:
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ValueError()
    except ValueError:
        raise HTTPException(400, "Invalid JSON")
    if missing() or inbox is None:
        raise HTTPException(503, "Integration not configured")
    try:
        messages = []
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if value.get("metadata", {}).get("phone_number_id") != os.environ["WHATSAPP_PHONE_NUMBER_ID"]:
                    continue
                for message in value.get("messages", []):
                    if message.get("type") == "text" and message.get("text", {}).get("body"):
                        if not message.get("id") or not message.get("from"):
                            raise ValueError()
                        float(message["timestamp"])
                        messages.append(message)
    except (KeyError, TypeError, ValueError, AttributeError):
        raise HTTPException(400, "Malformed webhook")
    try:
        for message in messages:
            await process_message(message)
    except Exception:
        raise HTTPException(503, "Inbox unavailable")
    return {"received": True}
