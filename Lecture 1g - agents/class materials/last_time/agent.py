#!/usr/bin/env python3

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from openai import OpenAI


SYSTEM_PROMPT = """You are a coding agent operating in a user's repository.

You can inspect and modify the workspace by running shell commands. Work carefully:
- First inspect relevant files before changing them.
- Prefer small, targeted edits.
- Run tests or validation after making changes.
- Explain what you changed and mention any remaining issues.
- Never pretend a command succeeded if it did not.
- Use the current working directory as the project root.
"""

MAX_TOOL_OUTPUT = 20000

TOOLS = [
    {
        "type": "function",
        "name": "run_shell",
        "description": (
            "Run a shell command in the project workspace. Use this to inspect files, "
            "edit code, run tests, install dependencies, and perform other coding tasks."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Command timeout in seconds, from 1 to 300.",
                    "minimum": 1,
                    "maximum": 300,
                    "default": 120,
                },
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    }
]


def serialize_item(item):
    if isinstance(item, dict):
        return item
    if hasattr(item, "model_dump"):
        return item.model_dump(exclude_none=True)
    return dict(item)


def run_shell(command, timeout, cwd, auto_approve):
    if not auto_approve:
        print("\nThe agent wants to run:")
        print(f"  {command}")
        try:
            answer = input("Allow? [y/N] ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in {"y", "yes"}:
            return "Command rejected by user."

    timeout = max(1, min(int(timeout or 120), 300))

    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            env=os.environ.copy(),
        )
        output = completed.stdout or ""
        if len(output) > MAX_TOOL_OUTPUT:
            output = (
                output[: MAX_TOOL_OUTPUT // 2]
                + "\n...[output truncated]...\n"
                + output[-MAX_TOOL_OUTPUT // 2 :]
            )
        return f"Exit code: {completed.returncode}\n{output}"
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        return f"Command timed out after {timeout} seconds.\n{output}"
    except Exception as exc:
        return f"Failed to execute command: {type(exc).__name__}: {exc}"


def ask_agent(client, history, cwd, auto_approve, model):
    while True:
        response = client.responses.create(
            model=model,
            input=history,
            tools=TOOLS,
            tool_choice="auto",
        )

        output_items = [serialize_item(item) for item in response.output]
        history.extend(output_items)

        calls = [
            item for item in output_items
            if item.get("type") == "function_call"
        ]

        if not calls:
            text = response.output_text or ""
            if text:
                print(text)
            return

        for call in calls:
            name = call.get("name")
            call_id = call.get("call_id")
            raw_arguments = call.get("arguments", "{}")

            try:
                arguments = json.loads(raw_arguments)
            except json.JSONDecodeError:
                arguments = {}

            if name == "run_shell":
                result = run_shell(
                    command=str(arguments.get("command", "")),
                    timeout=arguments.get("timeout", 120),
                    cwd=cwd,
                    auto_approve=auto_approve,
                )
            else:
                result = f"Unknown tool: {name}"

            history.append(
                {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": result,
                }
            )


def build_parser():
    parser = argparse.ArgumentParser(
        description="A command-line coding agent powered by the OpenAI Responses API."
    )
    parser.add_argument(
        "prompt",
        nargs="*",
        help="Task for the agent. Omit for interactive mode.",
    )
    parser.add_argument(
        "--model",
        default=os.getenv("OPENAI_MODEL", "gpt-4.1"),
        help="OpenAI model to use.",
    )
    parser.add_argument(
        "--cwd",
        default=".",
        help="Project directory.",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Run shell commands without asking for approval.",
    )
    parser.add_argument(
        "--system",
        default=SYSTEM_PROMPT,
        help="Additional system instruction.",
    )
    return parser


def main():
    args = build_parser().parse_args()
    cwd = Path(args.cwd).expanduser().resolve()

    if not cwd.is_dir():
        print(f"Error: not a directory: {cwd}", file=sys.stderr)
        return 2

    try:
        client = OpenAI()
    except Exception as exc:
        print(f"Error initializing OpenAI client: {exc}", file=sys.stderr)
        return 1

    history = [
        {
            "role": "developer",
            "content": args.system
            + f"\n\nWorkspace: {cwd}",
        }
    ]

    if args.prompt:
        history.append({"role": "user", "content": " ".join(args.prompt)})
        try:
            ask_agent(client, history, cwd, args.auto, args.model)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
            return 130
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0

    print("OpenAI coding agent. Type 'exit' or press Ctrl-D to quit.")
    print(f"Workspace: {cwd}")

    while True:
        try:
            prompt = input("\n> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print("\n")
            break

        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            break

        history.append({"role": "user", "content": prompt})
        try:
            ask_agent(client, history, cwd, args.auto, args.model)
        except KeyboardInterrupt:
            print("\nInterrupted.", file=sys.stderr)
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

