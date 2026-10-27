"""Validated data structures shared by the agent and Gemini adapters."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Base schema that rejects unexpected fields."""

    model_config = ConfigDict(extra="forbid")


class TextPart(StrictModel):
    kind: Literal["text"] = "text"
    text: str


class FunctionCallPart(StrictModel):
    kind: Literal["function_call"] = "function_call"
    name: str
    args: dict[str, Any] = Field(default_factory=dict)
    thought_signature: str | None = None


class FunctionResponsePart(StrictModel):
    kind: Literal["function_response"] = "function_response"
    name: str
    response: dict[str, Any]


ConversationPart = Annotated[
    TextPart | FunctionCallPart | FunctionResponsePart,
    Field(discriminator="kind"),
]


class ConversationMessage(StrictModel):
    role: Literal["user", "model"]
    parts: list[ConversationPart] = Field(min_length=1)

    def to_gemini_payload(self) -> dict[str, Any]:
        """Convert to the common Gemini REST/SDK content representation."""
        converted: list[dict[str, Any]] = []
        for part in self.parts:
            if isinstance(part, TextPart):
                converted.append({"text": part.text})
            elif isinstance(part, FunctionCallPart):
                function_part: dict[str, Any] = {
                    "functionCall": {"name": part.name, "args": part.args}
                }
                if part.thought_signature is not None:
                    function_part["thoughtSignature"] = part.thought_signature
                converted.append(function_part)
            else:
                converted.append(
                    {
                        "functionResponse": {
                            "name": part.name,
                            "response": part.response,
                        }
                    }
                )
        return {"role": self.role, "parts": converted}


class ModelTurn(StrictModel):
    """One model response, possibly requesting one or more tools."""

    text: str | None = None
    calls: list[FunctionCallPart] = Field(default_factory=list)


class ToolResult(StrictModel):
    """A serializable success or failure returned to the model."""

    name: str
    success: bool
    output: dict[str, Any] | None = None
    error: str | None = None


class AgentResult(StrictModel):
    """Validated final response from an agent run."""

    status: Literal["completed", "error", "max_iterations"]
    answer: str
    iterations: int = Field(ge=0)
    tool_results: list[ToolResult] = Field(default_factory=list)
