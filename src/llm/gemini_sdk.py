"""Gemini integration using Google's official google-genai SDK."""

from __future__ import annotations

import base64
from typing import Any

from google import genai
from google.genai import types

from src.agent.core import SYSTEM_INSTRUCTION
from src.agent.schemas import (
    ConversationMessage,
    FunctionCallPart,
    ModelTurn,
)


class GeminiSdkProvider:
    """Uses the official Google Gen AI Python client for generateContent."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY must not be empty")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate(
        self,
        history: list[ConversationMessage],
        function_declarations: list[dict[str, object]],
    ) -> ModelTurn:
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            tools=[
                types.Tool(function_declarations=function_declarations)  # type: ignore[arg-type]
            ],
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=[message.to_gemini_payload() for message in history],
            config=config,
        )
        if not response.candidates or response.candidates[0].content is None:
            raise RuntimeError("Gemini API response had no candidate content")

        text_chunks: list[str] = []
        calls: list[FunctionCallPart] = []
        for part in response.candidates[0].content.parts or []:
            if part.text:
                text_chunks.append(part.text)
            function_call = part.function_call
            if function_call and function_call.name:
                args: dict[str, Any] = dict(function_call.args or {})
                calls.append(
                    FunctionCallPart(
                        name=function_call.name,
                        args=args,
                        thought_signature=(
                            base64.b64encode(part.thought_signature).decode("ascii")
                            if isinstance(part.thought_signature, bytes)
                            else part.thought_signature
                        ),
                    )
                )
        return ModelTurn(text="".join(text_chunks) or None, calls=calls)
