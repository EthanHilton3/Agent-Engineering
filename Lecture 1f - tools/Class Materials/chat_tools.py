import argparse
import json
import random
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from tools import ToolBox
from usage import print_usage

toolbox = ToolBox()


@toolbox.tool
def multiply(a: float, b: float) -> float:
    """Multiplies two numbers together."""
    print('TOOL:', a, b, a * b)
    return a * b


@toolbox.tool
def random_number() -> float:
    """Returns a random number."""
    foo = random.random()
    print('TOOL:', foo)
    return foo


def _run_agent_turn(client, model: str, reasoning: str, history: list):
    turn_history = []
    turn_usage = []

    while True:
        response = client.responses.create(
            model=model,
            input=history + turn_history,
            reasoning={'effort': reasoning},
            tools=toolbox.tools
        )
        turn_history += response.output
        turn_usage.append((response.model, response.usage))

        if response.output_text:
            return response.output_text, turn_history, turn_usage

        for output in response.output:
            if output.type == 'function_call':
                args = json.loads(output.arguments)
                func = toolbox.get_tool_function(output.name)
                result = func(**args)
                turn_history.append({
                    'type': 'function_call_output',
                    'call_id': output.call_id,
                    'output': str(result)
                })


def main(model: str, reasoning: str, prompt: str):
    client = OpenAI()

    history = [{'role': 'system', 'content': prompt}]
    usage = []

    while True:
        usr_message = input('USER: ')
        if not usr_message:
            break

        history.append({'role': 'user', 'content': usr_message})

        start = time()
        output_text, turn_history, turn_usage = _run_agent_turn(client, model, reasoning, history)
        history += turn_history
        usage += turn_usage
        print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
        print('AGENT:', output_text)

    print_usage(usage)


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('AI Response')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='none')

    args = parser.parse_args()
    main(args.model, args.reasoning, args.prompt_file.read_text())
