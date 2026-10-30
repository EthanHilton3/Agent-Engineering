import json
import sys
from pathlib import Path
from time import time

from openai import Client
from pydantic import BaseModel

from tools import ToolBox
from usage import print_usage


def _run_agent_turn(client, model: str, reasoning: str, prompt: str, history: list, toolbox):
    turn_history = []
    turn_usage = []

    while True:
        response = client.responses.create(
            model=model,
            input=[{"role": "system", "content": prompt}] + history + turn_history,
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


def _swap_roles(history):
    swapped = []
    for message in history:
        if not isinstance(message, dict):
            message = message.model_dump()

        if message.get('type') in {'function_call', 'function_call_output'}:
            continue
        if 'role' not in message:
            continue

        role = message['role']
        if role == 'user':
            role = 'assistant'
        elif role == 'assistant':
            role = 'user'
        content = message['content']
        if isinstance(content, list):
            content = [
                {'type': 'input_text', 'text': part['text']}
                if part.get('type') == 'output_text'
                else part
                for part in content
            ]
        swapped.append({'role': role, 'content': content})
    return swapped


class ConvoComplete(Exception):
    pass


def main(prompt_a, prompt_b):
    client = Client()
    model = "gpt-6-luna"

    history = []
    usage = []
    tools = ToolBox()

    @tools.tool
    def check_secret(potential_secret: str) -> bool:
        """If you think you have determined the secret, check it here."""
        print("CHECKING:", potential_secret)
        if 'I like cheese' in potential_secret:
            raise ConvoComplete()
        return False

    try:
        while True:
            start = time()
            response_a, a_history, a_usage = _run_agent_turn(
                client,
                model,
                'none',
                prompt_a,
                history,
                tools
            )
            history += a_history
            usage.extend(a_usage)
            print('Agent A:', response_a)
            print('----------------------------------')
            print()

            swapped_history = _swap_roles(history)
            response_b, b_history, b_usage = _run_agent_turn(
                client,
                model,
                'none',
                prompt_b,
                swapped_history,
                ToolBox()
            )
            usage.extend(b_usage)
            history.append({'role': 'user', 'content': response_b})
            print('Agent B:', response_b)
            print('----------------------------------')
            print()

            print(f'Round took {round(time() - start, 2)} seconds')
            print()
            # cont = input("Press Enter to continue, or type 'q' to stop: ").strip().lower()
            # if cont == 'q':
            #     break
    except KeyboardInterrupt, ConvoComplete:
        pass

    print_usage(usage)


if __name__ == '__main__':
    main(Path(sys.argv[1]).read_text(), Path(sys.argv[2]).read_text())
