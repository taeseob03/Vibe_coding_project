"""Small, bounded live probes. Never prints API keys or request headers."""
import asyncio
import json
import os
import time

import httpx
from dotenv import load_dotenv

from app.analysis import INSTRUCTIONS, KeywordResult


async def probe(client, model, structured=False):
    started = time.monotonic()
    body = {"contents": [{"parts": [{"text": "도서관에서 공부했다."}]}]}
    if structured:
        body["systemInstruction"] = {"parts": [{"text": INSTRUCTIONS}]}
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseJsonSchema": KeywordResult.model_json_schema(),
            "maxOutputTokens": 2048,
        }
    else:
        body["contents"][0]["parts"][0]["text"] = "Reply with OK."
    result = {"model": model, "structured": structured}
    try:
        response = await client.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", json=body)
        result["status"] = response.status_code
        data = response.json()
        if response.is_success:
            result["text"] = "".join(p.get("text", "") for c in data.get("candidates", []) for p in c.get("content", {}).get("parts", []) if not p.get("thought"))
        else:
            error = data.get("error", {})
            result["error_status"] = error.get("status")
            result["message"] = str(error.get("message", "")).replace(os.environ["GEMINI_API_KEY"], "[redacted]")[:600]
    except Exception as exc:
        result["exception"] = type(exc).__name__
    result["seconds"] = round(time.monotonic() - started, 2)
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


async def main():
    load_dotenv(".env", override=True)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    print(json.dumps({"key_present": bool(key), "model": os.getenv("GEMINI_MODEL")}), flush=True)
    if not key:
        return
    async with httpx.AsyncClient(headers={"x-goog-api-key": key}, timeout=25) as client:
        await asyncio.gather(
            probe(client, os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")),
            probe(client, os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"), True),
            probe(client, "gemini-2.5-flash-lite"),
        )


if __name__ == "__main__":
    asyncio.run(main())
