import json
import os
from pathlib import Path
from urllib import error, request

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv(Path(__file__).with_name(".env"), override=True)

app = FastAPI(title="Chatbot API")

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CHAT_ALLOWED_ORIGINS",
        "http://127.0.0.1:5173,http://localhost:5173,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
GEMINI_SYSTEM_PROMPT = os.getenv(
    "GEMINI_SYSTEM_PROMPT",
    "You are Nexus, an assistant for a student chatbot MVP. "
    "Give concise, practical answers in plain language and be honest about uncertainty.",
)

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)

class ChatResponse(BaseModel):
    reply: str


def _extract_reply(api_response: dict) -> str:
    candidates = api_response.get("candidates") or []
    if not candidates:
        return ""

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []

    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n".join(text_parts).strip()


def _generate_gemini_reply(message: str, api_key: str) -> str:
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={api_key}"
    )
    payload = {
        "system_instruction": {
            "parts": [{"text": GEMINI_SYSTEM_PROMPT}],
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": message}],
            }
        ],
        "generationConfig": {
            "temperature": 0.6,
            "maxOutputTokens": 512,
        },
    }

    req = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=45) as response:
            body = response.read().decode("utf-8")
            data = json.loads(body)
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {detail or exc.reason}",
        ) from exc
    except error.URLError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini network error: {exc.reason}",
        ) from exc

    reply = _extract_reply(data)
    if not reply:
        raise HTTPException(
            status_code=502,
            detail="Gemini returned an empty response",
        )

    return reply

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not configured on the chat server",
        )

    reply = await run_in_threadpool(_generate_gemini_reply, req.message, api_key)
    return ChatResponse(reply=reply)


@app.get("/")
async def root():
    return {
        "message": "Nexus Chat API is running",
        "model": GEMINI_MODEL,
        "endpoints": {
            "chat": "POST /chat",
        },
    }