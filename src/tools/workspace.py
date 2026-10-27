"""Read-only workspace tools with path traversal and size protections."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field

from src.tools.base import BaseTool, ToolArguments

MAX_FILE_BYTES = 100_000
MAX_LIST_ENTRIES = 200


class WorkspaceArguments(ToolArguments):
    path: str = "."


class ListFilesArguments(WorkspaceArguments):
    limit: int = Field(default=100, ge=1, le=MAX_LIST_ENTRIES)


class ReadFileArguments(WorkspaceArguments):
    pass


class WorkspaceTool(BaseTool):
    """Base class for tools confined to a configured workspace."""

    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace.expanduser().resolve()

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a relative path, rejecting paths that escape the workspace."""
        requested = Path(relative_path)
        if requested.is_absolute():
            raise ValueError("Only paths relative to the workspace are allowed")
        if any(
            part.casefold() == ".git"
            or part.casefold().startswith(".env")
            or Path(part).suffix.casefold() in {".pem", ".key", ".p12", ".pfx"}
            for part in requested.parts
        ):
            raise ValueError("Access to repository metadata and secret files is denied")
        resolved = (self.workspace / requested).resolve()
        if not resolved.is_relative_to(self.workspace):
            raise ValueError("Path must stay inside the configured workspace")
        return resolved


class ListFilesTool(WorkspaceTool):
    name = "list_files"
    description = (
        "List immediate files and directories at a path in the workspace. "
        "Use this to discover relevant project files."
    )
    arguments_model = ListFilesArguments

    def run(self, arguments: ToolArguments) -> dict[str, Any]:
        if not isinstance(arguments, ListFilesArguments):
            raise TypeError("Expected ListFilesArguments")
        directory = self.resolve_path(arguments.path)
        if not directory.is_dir():
            raise ValueError("The requested path is not a directory")
        entries = sorted(directory.iterdir(), key=lambda entry: entry.name.casefold())
        visible = [
            entry
            for entry in entries
            if entry.name.casefold() != ".git"
            and not entry.name.casefold().startswith(".env")
        ][: arguments.limit]
        return {
            "path": directory.relative_to(self.workspace).as_posix() or ".",
            "entries": [
                {
                    "name": entry.name,
                    "type": "directory" if entry.is_dir() else "file",
                }
                for entry in visible
            ],
            "truncated": len(entries) > len(visible),
        }


class ReadFileTool(WorkspaceTool):
    name = "read_file"
    description = (
        "Read a UTF-8 text file inside the workspace. "
        "Do not use this for secrets or files outside the workspace."
    )
    arguments_model = ReadFileArguments

    def run(self, arguments: ToolArguments) -> dict[str, Any]:
        if not isinstance(arguments, ReadFileArguments):
            raise TypeError("Expected ReadFileArguments")
        path = self.resolve_path(arguments.path)
        if not path.is_file():
            raise ValueError("The requested path is not a file")
        try:
            with path.open("rb") as source:
                content_bytes = source.read(MAX_FILE_BYTES + 1)
            if len(content_bytes) > MAX_FILE_BYTES:
                raise ValueError(f"File exceeds the {MAX_FILE_BYTES}-byte read limit")
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("Only UTF-8 text files can be read") from error
        return {
            "path": path.relative_to(self.workspace).as_posix(),
            "content": content.replace("\r\n", "\n").replace("\r", "\n"),
        }
