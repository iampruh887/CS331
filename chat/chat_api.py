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


import httpx

def _extract_reply(api_response: dict) -> str:
    candidates = api_response.get("candidates") or []
    if not candidates:
        return ""

    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []

    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    return "\n".join(text_parts).strip()


async def _generate_gemini_reply(message: str, api_key: str) -> str:
    endpoint = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={api_key}"
    )
    payload = {
        "systemInstruction": {
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

    try:
        # httpx uses a reasonable default timeout to prevent indefinite hangs.
        # We set a 15-second connect timeout and 30-second read timeout.
        async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {detail}",
        ) from exc
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini network error: {str(exc)}",
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

    reply = await _generate_gemini_reply(req.message, api_key)
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