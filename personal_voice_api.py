"""Personal JARVIS text conversation API (speech recognition lives on Android)."""
import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

router = APIRouter(prefix="/assistant", tags=["personal-assistant"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


def check_token(authorization: str | None = Header(default=None)):
    expected = os.getenv("JARVIS_PERSONAL_TOKEN", "")
    token = (authorization or "").removeprefix("Bearer ")
    if not expected or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(check_token)])
async def chat(payload: ChatRequest):
    uri = os.getenv("MONGODB_URI")
    model = os.getenv("JARVIS_PERSONAL_MODEL") or os.getenv("OPENAI_MODEL")
    if not uri or not model or not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="Personal assistant not configured")

    mongo = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=4000)
    try:
        db = mongo[os.getenv("MONGODB_DATABASE", os.getenv("DB_NAME", "jarvis"))]
        collection = db.personal_conversation
        recent = await collection.find({}, {"_id": 0, "role": 1, "content": 1}).sort(
            "_id", -1
        ).limit(12).to_list(length=12)
        history = list(reversed(recent))
        instructions = (
            "Você é JARVIS, o assistente pessoal do usuário, em português do Brasil. "
            "Seja direto, ajude a retomar projetos e não afirme ter executado algo sem verificar. "
            "O histórico fornecido é apenas uma janela recente, não uma memória completa."
        )
        client = AsyncOpenAI(timeout=35, max_retries=0)
        response = await client.responses.create(
            model=model, store=False, instructions=instructions,
            input=history + [{"role": "user", "content": payload.message}],
            max_output_tokens=700
        )
        reply = response.output_text.strip()
        if not reply:
            raise RuntimeError("Empty model response")
        now = datetime.now(timezone.utc)
        await collection.insert_many([
            {"role": "user", "content": payload.message, "created_at": now},
            {"role": "assistant", "content": reply, "created_at": now},
        ])
        return ChatResponse(reply=reply)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=503, detail="Personal assistant temporarily unavailable")
    finally:
        mongo.close()
