"""Gemini REST API integration without a vendor SDK."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.agent.core import SYSTEM_INSTRUCTION
from src.agent.schemas import (
    ConversationMessage,
    FunctionCallPart,
    ModelTurn,
    TextPart,
)

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT_SECONDS = 30


class GeminiRestProvider:
    """Calls generateContent directly over HTTPS using Python's standard library."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY must not be empty")
        self.api_key = api_key
        self.model = model

    def generate(
        self,
        history: list[ConversationMessage],
        function_declarations: list[dict[str, object]],
    ) -> ModelTurn:
        body = {
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "contents": [message.to_gemini_payload() for message in history],
            "tools": [{"functionDeclarations": function_declarations}],
        }
        request = Request(
            f"{API_ROOT}/{self.model}:generateContent",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(
                f"Gemini API returned HTTP {error.code}: {detail}"
            ) from error
        except (URLError, TimeoutError) as error:
            raise RuntimeError(f"Gemini API request failed: {error}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("Gemini API returned invalid JSON") from error

        try:
            candidate = payload["candidates"][0]
            parts = candidate["content"]["parts"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("Gemini API response had no candidate content") from error

        text_chunks: list[str] = []
        calls: list[FunctionCallPart] = []
        for part in parts:
            if "text" in part:
                text_chunks.append(str(part["text"]))
            if "functionCall" in part:
                call: dict[str, Any] = part["functionCall"]
                calls.append(
                    FunctionCallPart(
                        name=call["name"],
                        args=call.get("args") or {},
                        thought_signature=part.get("thoughtSignature"),
                    )
                )
        text = "".join(text_chunks) or None
        return ModelTurn(text=text, calls=calls)
