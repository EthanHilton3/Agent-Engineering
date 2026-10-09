import argparse
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage

CODE_INTERPRETER_CONTAINER_COST_USD = 0.03


def _as_dict(item):
    '''Convert an SDK response item into a dictionary for inspection/history.'''
    if isinstance(item, dict):
        return item
    if hasattr(item, 'model_dump'):
        return item.model_dump(exclude_none=True)
    return dict(item)


def _print_code_trace(items):
    '''Show the Python code and outputs returned by Code Interpreter.'''
    print('\nCODE INTERPRETER TRACE', file=sys.stderr)
    print('----------------------', file=sys.stderr)

    for item in items:
        if item.get('type') != 'code_interpreter_call':
            continue

        code = item.get('code')
        if code:
            print('code:', file=sys.stderr)
            print(code, file=sys.stderr)

        outputs = item.get('outputs') or []
        for output in outputs:
            if output.get('type') == 'logs':
                print('output:', file=sys.stderr)
                print(output.get('logs', ''), file=sys.stderr)

    print('----------------------', file=sys.stderr)


def _run_agent_turn(client, model: str, reasoning: str, history: list):
    response = client.responses.create(
        model=model,
        input=history,
        reasoning={'effort': reasoning},
        tools=[{
            'type': 'code_interpreter',
            'container': {'type': 'auto'},
        }],
        tool_choice='required',
        include=['code_interpreter_call.outputs'],
    )

    response_items = [_as_dict(item) for item in response.output]
    _print_code_trace(response_items)
    code_interpreter_calls = sum(
        item.get('type') == 'code_interpreter_call'
        for item in response_items
    )
    container_ids = {
        item.get('container_id')
        for item in response_items
        if item.get('type') == 'code_interpreter_call'
        and item.get('container_id')
    }

    if not response.output_text:
        raise RuntimeError('code interpreter returned no final text response')
    return (response.output_text, response_items,
            [(response.model, response.usage)], code_interpreter_calls,
            container_ids)


def main(model: str, reasoning: str, prompt: str):
    client = OpenAI()

    history = [{'role': 'system', 'content': prompt}]
    usage = []
    code_interpreter_calls = 0
    container_ids = set()

    while True:
        usr_message = input('USER: ')
        if not usr_message:
            break

        history.append({'role': 'user', 'content': usr_message})

        start = time()
        (output_text, turn_history, turn_usage, turn_code_calls,
         turn_container_ids) = _run_agent_turn(
            client, model, reasoning, history
        )
        history += turn_history
        usage += turn_usage
        code_interpreter_calls += turn_code_calls
        container_ids.update(turn_container_ids)
        print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
        print('AGENT:', output_text)

    print_usage(usage)
    print(f'Code Interpreter calls: {code_interpreter_calls}', file=sys.stderr)
    print(f'Containers used: {len(container_ids)}', file=sys.stderr)
    print(
        'Estimated minimum container cost (USD): '
        f'${len(container_ids) * CODE_INTERPRETER_CONTAINER_COST_USD:.6f}',
        file=sys.stderr,
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Code Interpreter arithmetic demo')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='none')

    args = parser.parse_args()
    main(args.model, args.reasoning, args.prompt_file.read_text())
