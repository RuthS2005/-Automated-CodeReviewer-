"""Typed tool contract and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict


class ToolArguments(BaseModel):
    """Base schema for validated tool arguments."""

    model_config = ConfigDict(extra="forbid")


class BaseTool(ABC):
    """Tool definition that validates model-provided arguments before running."""

    name: ClassVar[str]
    description: ClassVar[str]
    arguments_model: ClassVar[type[ToolArguments]]

    @abstractmethod
    def run(self, arguments: ToolArguments) -> dict[str, Any]:
        """Run this tool with already validated arguments."""
        raise NotImplementedError

    def function_declaration(self) -> dict[str, Any]:
        """Return a Gemini function declaration derived from the Pydantic schema."""
        schema = self.arguments_model.model_json_schema()
        self._clean_schema(schema)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": schema,
        }

    @classmethod
    def _clean_schema(cls, schema: dict[str, Any]) -> None:
        """Remove Pydantic metadata not needed in a Gemini function schema."""
        schema.pop("title", None)
        schema.pop("additionalProperties", None)
        for value in schema.values():
            if isinstance(value, dict):
                cls._clean_schema(value)

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate arguments and perform the deterministic tool operation."""
        validated = self.arguments_model.model_validate(arguments)
        return self.run(validated)


class ToolRegistry:
    """Small registry used to expose and dispatch the available tools."""

    def __init__(self, tools: list[BaseTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("Tool names must be unique")

    def declarations(self) -> list[dict[str, Any]]:
        """Return provider-compatible declarations for every registered tool."""
        return [tool.function_declaration() for tool in self._tools.values()]

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a tool by name or raise for the agent to report as a tool error."""
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        return self._tools[name].invoke(arguments)
