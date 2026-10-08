import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage

some_tools = [
    {
        "type": "function",
        "name": "multiply",
        "description": "Multiply two numbers together. Use this tool for **all** multiplication tasks.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "num1": {
                    "type": "number",
                    "description": "First operand"
                },
                "num2": {
                    "type": "number",
                    "description": "Second operand"
                }
            },
            "required": [
                "num1",
                "num2"
            ],
            "additionalProperties": False
        }
    }
]


def _run_agent_turn(client, model: str, reasoning: str, history: list):
    turn_history = deepcopy(history)
    turn_usage = []

    while True:
        response = client.responses.create(
            model=model,
            input=turn_history,
            reasoning={'effort': reasoning},
            tools=some_tools
        )
        turn_history += response.output
        turn_usage.append((response.model, response.usage))

        if response.output_text:
            return response.output_text, turn_history, turn_usage

        for output in response.output:
            if output.type == 'function_call':
                assert output.name == 'multiply'
                args = json.loads(output.arguments)
                print('TOOL:', args, str(args['num1'] * args['num2']))
                turn_history.append({
                    'type': 'function_call_output',
                    'call_id': output.call_id,
                    'output': str(args['num1'] * args['num2'])
                })


def main(model: str, reasoning: str, prompt: str):
    client = OpenAI()

    history = [{'role': 'system', 'content': prompt}]
    usage = []
    
    start = time()
    output_text, turn_history, turn_usage = _run_agent_turn(client, model, reasoning, history)
    history += turn_history
    usage += turn_usage

    print(output_text)

    print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
    print_usage(usage)


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('AI Response')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='none')

    args = parser.parse_args()
    main(args.model, args.reasoning, args.prompt_file.read_text())
