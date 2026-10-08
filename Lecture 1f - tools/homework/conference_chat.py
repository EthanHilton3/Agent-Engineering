import argparse
import json
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from conference_tools import toolbox
from usage import print_usage


def _log(transcript: Path | None, text: str):
    if transcript:
        with transcript.open("a", encoding="utf-8") as file:
            file.write(text + "\n")


def _run_turn(client, model, reasoning, history, use_tools: bool, transcript: Path | None):
    start = time()
    turn_history = []
    turn_usage = []

    while True:
        response = client.responses.create(
            model=model,
            input=history + turn_history,
            reasoning={"effort": reasoning},
            tools=toolbox.tools if use_tools else [],
        )
        turn_history += response.output
        turn_usage.append((response.model, response.usage))

        if response.output_text:
            print(f"{round(time() - start, 2)} seconds elapsed", file=sys.stderr)
            return response.output_text, turn_history, turn_usage

        tool_results = []
        for output in response.output:
            if output.type != "function_call":
                continue

            args = json.loads(output.arguments)
            function = toolbox.get_tool_function(output.name)
            if function is None:
                result = f"TOOL_ERROR: unknown tool {output.name}"
            else:
                # Send errors back to the model so it can correct itself
                try:
                    result = function(**args)
                except Exception as error:
                    result = f"TOOL_ERROR: {error}"
            error = f" -> {result}" if str(result).startswith("TOOL_ERROR") else ""  # pages are too long to print; errors aren't
            print(f"TOOL: {output.name}({args}){error}")
            _log(transcript, f"> TOOL: `{output.name}({args})`{error}\n")
            tool_results.append({
                "type": "function_call_output",
                "call_id": output.call_id,
                "output": str(result),
            })

        turn_history += tool_results


def main(model: str, reasoning: str, prompt: str, use_tools: bool, transcript: Path | None):
    client = OpenAI()
    history = [{"role": "system", "content": prompt}]
    usage = []
    _log(transcript, f"# Transcript (model={model}, tools={use_tools})\n")

    try:
        while True:
            user_message = input("USER: ")
            if not user_message:
                break

            history.append({"role": "user", "content": user_message})
            _log(transcript, f"**USER:** {user_message}\n")

            output_text, turn_history, turn_usage = _run_turn(
                client, model, reasoning, history, use_tools, transcript
            )
            history += turn_history
            usage += turn_usage

            print("AGENT:", output_text)
            _log(transcript, f"**AGENT:** {output_text}\n")
    except KeyboardInterrupt:
        print()  # move past the "USER: " prompt line

    print_usage(usage)
    if transcript:
        with transcript.open("a", encoding="utf-8") as file:
            print("```", file=file)  # code block keeps the table's line breaks in Markdown
            print_usage(usage, file=file)
            print("```", file=file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("General Conference quote finder")
    parser.add_argument("prompt_file", type=Path)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning", default="none")
    parser.add_argument("--tools", required=True, choices=("false", "true"))
    parser.add_argument("--transcript", type=Path, help="Append the conversation to this Markdown file.")
    args = parser.parse_args()
    main(
        args.model,
        args.reasoning,
        args.prompt_file.read_text(),
        args.tools == "true",
        args.transcript,
    )
