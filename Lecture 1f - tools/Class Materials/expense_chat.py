import argparse
import json
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from expense_tools import create_many_toolbox, expenses_json_from_task, one_toolbox
from usage import print_usage


def _run_turn(client, model, reasoning, history, tools, toolboxes):
    start = time()
    turn_history = []
    turn_usage = []

    while True:
        response = client.responses.create(
            model=model,
            input=history + turn_history,
            reasoning={"effort": reasoning},
            tools=tools,
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
            function = next(
                (
                    toolbox.get_tool_function(output.name)
                    for toolbox in toolboxes
                    if toolbox.get_tool_function(output.name)
                ),
                None,
            )
            if function is None:
                raise ValueError(f"Unknown tool requested: {output.name}")

            result = function(**args)
            print(f"TOOL: {output.name}({args}) -> {result}")
            tool_results.append({
                "type": "function_call_output",
                "call_id": output.call_id,
                "output": str(result),
            })

        turn_history += tool_results


def main(model: str, reasoning: str, prompt: str, task: str, tool_mode: str):
    client = OpenAI()
    history = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": task},
    ]

    if tool_mode == "one":
        tools = one_toolbox.tools
        toolboxes = [one_toolbox]
    elif tool_mode == "many":
        many_toolbox = create_many_toolbox(expenses_json_from_task(task))
        tools = many_toolbox.tools
        toolboxes = [many_toolbox]
    else:
        tools = []
        toolboxes = []

    output_text, _, usage = _run_turn(
        client, model, reasoning, history, tools, toolboxes
    )
    print("AGENT:", output_text)
    print_usage(usage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Expense report tool-calling demo")
    parser.add_argument("prompt_file", type=Path)
    parser.add_argument("input_file", type=Path)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning", default="none")
    parser.add_argument(
        "--tools",
        required=True,
        choices=("none", "one", "many"),
        help="Use no tools, one full-report tool, or many narrow tools.",
    )
    args = parser.parse_args()
    main(
        args.model,
        args.reasoning,
        args.prompt_file.read_text(),
        args.input_file.read_text(),
        args.tools,
    )
