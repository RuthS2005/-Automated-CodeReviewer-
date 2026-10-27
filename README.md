# Automated Code Reviewer

A minimal, read-only code-review agent implemented twice against Gemini:

1. **Direct REST implementation** — Python standard-library HTTPS calls to Gemini.
2. **Official SDK implementation** — Google's `google-genai` Python SDK.

Both entry points use the same bounded ReAct loop, Pydantic-validated tool and
result schemas, and workspace tools. The agent can list immediate directory
contents and read small UTF-8 text files; it does not execute repository code or
commands. Tool errors are sent back to Gemini so it can recover instead of
crashing the loop.

## Requirements

- Python 3.11+
- A Gemini API key

Install the project (including the official SDK required by the SDK entry point):

```shell
python -m pip install -e .
```

Set configuration in the environment. The API key is required; the other values
are optional:

```shell
# PowerShell
$env:GEMINI_API_KEY = "your-key"
$env:GEMINI_MODEL = "gemini-2.5-flash"
$env:AGENT_WORKSPACE = (Get-Location).Path
$env:MAX_AGENT_ITERATIONS = "8"
```

`GEMINI_API_KEY` is never stored in source code. Settings can also be loaded from
a local `.env` file; do not commit that file.

## Run either implementation

From the repository root, provide one prompt as the final command argument:

```shell
python -m src.agent.direct "Review the Python files for correctness issues."
python -m src.agent.sdk "Review the Python files for correctness issues."
```

The direct implementation does not need the SDK to make requests, but the
project install includes it so both entry points work. Each command prints a
JSON `AgentResult` with its status, answer, iteration count, and tool results.

The workspace is controlled by `AGENT_WORKSPACE` (defaults to the current
directory). Reads are confined to that directory; `.git`, `.env*`, and common
private-key files are denied, and file reads are limited to 100 KB.

## Tests

Tests use only mock model responses and temporary directories; they do not
require an API key or make network requests:

```shell
python -m unittest discover -s tests -v
```
