"""Run the agent using the direct Gemini REST API integration."""

from src.agent.cli import main
from src.llm.gemini_rest import GeminiRestProvider


if __name__ == "__main__":
    raise SystemExit(main(GeminiRestProvider))
