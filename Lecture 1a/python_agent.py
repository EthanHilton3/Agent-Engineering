#!/usr/bin/env python3

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from openai import OpenAI
from usage import print_usage


TOOLS = [
    {
        "type": "function",
        "name": "shell",
        "description": "Run a shell command in the workspace. Use this for inspecting, testing, building, and modifying the project.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds.",
                    "minimum": 1,
                    "maximum": 600,
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "read_file",
        "description": "Read a UTF-8 text file from the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the workspace.",
                },
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "write_file",
        "description": "Write UTF-8 text to a file in the workspace, creating parent directories if needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path relative to the workspace.",
                },
                "content": {
                    "type": "string",
                    "description": "Complete file contents.",
                },
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "list_dir",
        "description": "List files and directories in a workspace directory.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path relative to the workspace. Defaults to '.'.",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
]


def resolve_path(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise ValueError("path must remain inside the workspace")
    return path


def approve(message: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    try:
        answer = input(f"{message}\nProceed? [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in {"y", "yes"}


def run_shell(root: Path, args: dict[str, Any], assume_yes: bool) -> str:
    command = str(args["command"])
    timeout = max(1, min(int(args.get("timeout", 120)), 600))

    if not approve(f"\n$ {command}", assume_yes):
        return "Command denied by user."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env=os.environ.copy(),
        )
        output = result.stdout or ""
        if len(output) > 30000:
            output = output[-30000:] + "\n[output truncated]"
        return f"exit_code: {result.returncode}\n{output}"
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode(errors="replace")
        return f"Command timed out after {timeout} seconds.\n{output}"
    except Exception as exc:
        return f"Command failed: {exc}"


def read_file(root: Path, args: dict[str, Any]) -> str:
    try:
        path = resolve_path(root, args["path"])
        content = path.read_text(encoding="utf-8")
        if len(content) > 50000:
            content = content[:50000] + "\n[content truncated]"
        return content
    except Exception as exc:
        return f"Unable to read file: {exc}"


def write_file(root: Path, args: dict[str, Any], assume_yes: bool) -> str:
    path_text = str(args["path"])
    content = str(args["content"])

    if not approve(f"\nWrite {path_text} ({len(content)} bytes)?", assume_yes):
        return "File write denied by user."

    try:
        path = resolve_path(root, path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path_text}"
    except Exception as exc:
        return f"Unable to write file: {exc}"


def list_dir(root: Path, args: dict[str, Any]) -> str:
    try:
        path = resolve_path(root, args.get("path", "."))
        if not path.is_dir():
            return f"Not a directory: {args.get('path', '.')}"
        entries = []
        for entry in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            suffix = "/" if entry.is_dir() else ""
            entries.append(entry.name + suffix)
        return "\n".join(entries) or "(empty)"
    except Exception as exc:
        return f"Unable to list directory: {exc}"


def execute_tool(
    name: str,
    arguments: dict[str, Any],
    root: Path,
    assume_yes: bool,
) -> str:
    if name == "shell":
        return run_shell(root, arguments, assume_yes)
    if name == "read_file":
        return read_file(root, arguments)
    if name == "write_file":
        return write_file(root, arguments, assume_yes)
    if name == "list_dir":
        return list_dir(root, arguments)
    return f"Unknown tool: {name}"


def run_agent(
    client: OpenAI,
    prompt: str,
    root: Path,
    model: str,
    assume_yes: bool,
    max_turns: int,
) -> None:
    instructions = f"""
You are a practical coding agent operating in the workspace: {root}

Work directly on the user's task. Inspect the existing project before making changes.
Use the available tools to read, edit, test, and validate code. Prefer small, focused changes.
Do not merely describe changes when you can implement them. Run relevant tests or checks.
Never claim success unless you have verified it. At the end, summarize what changed and any
remaining issues. The workspace is the current project directory.
""".strip()

    history: list[Any] = [{"role": "user", "content": prompt}]

    for _ in range(max_turns):
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=history,
            tools=TOOLS,
        )

        # Print out the usage for each API call
        if hasattr(response, "usage"):
            print_usage([(model, response.usage)])

        history.extend(response.output)
        calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]

        if not calls:
            text = response.output_text.strip()
            if text:
                print(text)
            return

        for call in calls:
            try:
                arguments = json.loads(call.arguments or "{}")
            except json.JSONDecodeError as exc:
                result = f"Invalid tool arguments: {exc}"
            else:
                result = execute_tool(
                    call.name,
                    arguments,
                    root,
                    assume_yes,
                )

            history.append(
                {
                    "type": "function_call_output",
                    "call_id": call.call_id,
                    "output": result,
                }
            )

    print("Agent stopped after reaching the maximum number of turns.", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="A small OpenAI-powered command-line coding agent."
    )
    parser.add_argument("prompt", nargs="*", help="Task for the agent.")
    parser.add_argument(
        "-m",
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
        help="OpenAI model to use.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Automatically approve shell commands and file writes.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=40,
        help="Maximum number of agent/tool turns.",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory. Defaults to the current directory.",
    )
    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("OPENAI_API_KEY is not set.", file=sys.stderr)
        return 1

    root = Path(args.workspace).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"Workspace is not a directory: {root}", file=sys.stderr)
        return 1

    client = OpenAI()

    if args.prompt:
        prompt = " ".join(args.prompt)
        try:
            run_agent(
                client,
                prompt,
                root,
                args.model,
                args.yes,
                args.max_turns,
            )
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    print(f"Workspace: {root}")
    print("Enter a task, or press Ctrl-D/Ctrl-C to exit.")

    while True:
        try:
            prompt = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not prompt:
            continue

        try:
            run_agent(
                client,
                prompt,
                root,
                args.model,
                args.yes,
                args.max_turns,
            )
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
