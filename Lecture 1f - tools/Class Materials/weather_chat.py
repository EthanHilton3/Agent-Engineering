import argparse
import json
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage
from weather_tools import toolbox


def _run_turn(client, model, reasoning, history, use_tools: bool):
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
                raise ValueError(f"Unknown tool requested: {output.name}")

            try:
                result = function(**args)
            except Exception as error:
                result = f"TOOL_ERROR: {error}"
            print(f"TOOL: {output.name}({args}) -> {result}")
            tool_results.append({
                "type": "function_call_output",
                "call_id": output.call_id,
                "output": str(result),
            })

        turn_history += tool_results


def main(model: str, reasoning: str, prompt: str, task: str, use_tools: bool):
    client = OpenAI()
    history = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": task},
    ]
    output_text, _, usage = _run_turn(client, model, reasoning, history, use_tools)
    print("AGENT:", output_text)
    print_usage(usage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Command-line weather tool-calling demo")
    parser.add_argument("prompt_file", type=Path)
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning", default="none")
    parser.add_argument(
        "--tools",
        required=True,
        choices=("false", "true"),
        help="Disable tools or enable location and weather tools.",
    )
    args = parser.parse_args()
    main(
        args.model,
        args.reasoning,
        args.prompt_file.read_text(),
        args.input_file.read_text(),
        args.tools == "true",
    )
