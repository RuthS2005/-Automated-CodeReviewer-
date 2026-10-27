"""Focused tests for tool validation and agent-loop resilience."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.agent.core import Agent
from src.agent.schemas import (
    ConversationMessage,
    FunctionCallPart,
    ModelTurn,
)
from src.tools.base import ToolRegistry
from src.tools.workspace import ListFilesTool, ReadFileTool


class QueueProvider:
    def __init__(self, turns: list[ModelTurn]) -> None:
        self.turns = turns
        self.histories: list[list[ConversationMessage]] = []

    def generate(
        self,
        history: list[ConversationMessage],
        function_declarations: list[dict[str, object]],
    ) -> ModelTurn:
        self.histories.append(list(history))
        return self.turns.pop(0)


class AgentTests(unittest.TestCase):
    def test_tool_failure_is_returned_to_model_and_loop_continues(self) -> None:
        provider = QueueProvider(
            [
                ModelTurn(
                    calls=[
                        FunctionCallPart(
                            name="read_file", args={"path": "../../outside.txt"}
                        )
                    ]
                ),
                ModelTurn(text="The requested path was outside the workspace."),
            ]
        )
        with TemporaryDirectory() as directory:
            tools = ToolRegistry(
                [ReadFileTool(Path(directory)), ListFilesTool(Path(directory))]
            )
            result = Agent(provider, tools).run("Review the project.")

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.tool_results), 1)
        self.assertFalse(result.tool_results[0].success)
        self.assertIn("workspace", result.tool_results[0].error or "")
        function_response = provider.histories[1][-1].parts[0]
        self.assertEqual(function_response.kind, "function_response")

    def test_invalid_tool_arguments_are_reported_without_crashing(self) -> None:
        provider = QueueProvider(
            [
                ModelTurn(
                    calls=[
                        FunctionCallPart(
                            name="list_files",
                            args={"path": ".", "limit": 999999},
                        )
                    ]
                )
            ]
        )
        with TemporaryDirectory() as directory:
            result = Agent(
                provider, ToolRegistry([ListFilesTool(Path(directory))]), max_iterations=1
            ).run("List project files")

        self.assertEqual(result.status, "max_iterations")
        self.assertFalse(result.tool_results[0].success)
        self.assertIn("ValidationError", result.tool_results[0].error or "")

    def test_read_file_returns_content_inside_workspace(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "sample.py").write_text("print('hello')\n", encoding="utf-8")
            output = ReadFileTool(root).invoke({"path": "sample.py"})

        self.assertEqual(output["path"], "sample.py")
        self.assertEqual(output["content"], "print('hello')\n")

    def test_read_file_rejects_environment_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".ENV").write_text("GEMINI_API_KEY=secret", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret files"):
                ReadFileTool(root).invoke({"path": ".ENV"})


if __name__ == "__main__":
    unittest.main()
