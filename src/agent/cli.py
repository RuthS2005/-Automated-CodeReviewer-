"""Shared command-line setup for both Gemini implementations."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence

from src.agent.core import Agent, ModelProvider
from src.llm.config import Settings
from src.tools.base import ToolRegistry
from src.tools.workspace import ListFilesTool, ReadFileTool

ProviderFactory = Callable[[str, str], ModelProvider]


def main(provider_factory: ProviderFactory, argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ask a read-only Gemini code-review agent about a workspace."
    )
    parser.add_argument("prompt", help="Question or code-review task")
    arguments = parser.parse_args(argv)
    try:
        settings = Settings()
        provider = provider_factory(
            settings.gemini_api_key.get_secret_value(), settings.gemini_model
        )
        tools = ToolRegistry(
            [
                ListFilesTool(settings.agent_workspace),
                ReadFileTool(settings.agent_workspace),
            ]
        )
        result = Agent(
            provider, tools, max_iterations=settings.max_agent_iterations
        ).run(arguments.prompt)
    except Exception as error:
        parser.exit(2, f"Configuration/startup failed: {error}\n")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    return 0 if result.status == "completed" else 1
