"""Run the agent using Google's official google-genai SDK."""

from src.agent.cli import main
from src.llm.gemini_sdk import GeminiSdkProvider


if __name__ == "__main__":
    raise SystemExit(main(GeminiSdkProvider))
