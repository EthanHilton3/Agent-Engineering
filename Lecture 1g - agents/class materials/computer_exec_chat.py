import argparse
import base64
import io
import json
import subprocess
import sys
import time
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pyautogui
from openai import OpenAI

from usage import print_usage


SAMPLE_DIR = Path(__file__).with_name('sample_dir').resolve()
MAX_TURNS = 20

TOOLS = [{
    'type': 'function',
    'name': 'exec_py',
    'description': (
        'Run Python in the persistent local desktop. PyAutoGUI, time, '
        'display(image), and log(value) are available. Use PyAutoGUI for '
        'visible UI actions. Inspect the screen before acting and display a '
        'screenshot after each short group of actions.'
    ),
    'parameters': {
        'type': 'object',
        'properties': {'code': {'type': 'string'}},
        'required': ['code'],
        'additionalProperties': False,
    },
    'strict': True,
}]


def _image_data_url(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def _execute_code(code, namespace):
    print('\nCODE REQUESTED BY MODEL\n' + '-' * 30, file=sys.stderr)
    print(code, file=sys.stderr)
    print('-' * 30, file=sys.stderr)
    # if input('Allow this code to run locally? [y/N] ').lower() != 'y':
    #     return [{'type': 'input_text', 'text': 'The user denied this execution.'}]

    output_buffer = io.StringIO()
    error_buffer = io.StringIO()
    screenshot = None

    def display(image):
        nonlocal screenshot
        screenshot = image

    namespace['display'] = display
    namespace['log'] = print
    namespace['pyautogui'] = pyautogui
    namespace['time'] = time

    try:
        with redirect_stdout(output_buffer), redirect_stderr(error_buffer):
            exec(code, namespace)
    except Exception as error:
        error_buffer.write(f'{type(error).__name__}: {error}')

    result = []
    text = output_buffer.getvalue()
    errors = error_buffer.getvalue()
    if text:
        result.append({'type': 'input_text', 'text': f'OUTPUT:\n{text}'})
    if errors:
        result.append({'type': 'input_text', 'text': f'ERROR:\n{errors}'})
    if screenshot is not None:
        result.append({
            'type': 'input_image',
            'image_url': _image_data_url(screenshot),
            'detail': 'original',
        })
    else:
        result.append({
            'type': 'input_image',
            'image_url': _image_data_url(pyautogui.screenshot()),
            'detail': 'original',
        })
    if not result:
        result.append({'type': 'input_text', 'text': 'Code completed with no output.'})
    return result


def _run_agent_turn(client, model, prompt, user_message, namespace,
                    previous_response_id):
    next_input = [{
        'role': 'user',
        'content': [
            {'type': 'input_text', 'text': user_message},
            {
                'type': 'input_image',
                'image_url': _image_data_url(pyautogui.screenshot()),
                'detail': 'original',
            },
        ],
    }]
    turn_usage = []

    for _ in range(MAX_TURNS):
        response = client.responses.create(
            model=model,
            instructions=prompt,
            input=next_input,
            previous_response_id=previous_response_id,
            reasoning={'effort': 'low'},
            tools=TOOLS,
            tool_choice='auto',
        )
        turn_usage.append((response.model, response.usage))

        if response.status != 'completed':
            raise RuntimeError(f'Response stopped with status: {response.status}')

        calls = [
            item for item in response.output
            if item.type == 'function_call'
        ]
        if not calls:
            has_final_message = any(
                item.type == 'message'
                and getattr(item, 'phase', None) != 'commentary'
                for item in response.output
            )
            if has_final_message and response.output_text:
                return response.output_text, response.id, turn_usage

            print(
                'No tool call or final message; continuing with output types: '
                f'{[item.type for item in response.output]}',
                file=sys.stderr,
            )
            previous_response_id = response.id
            next_input = []
            continue

        next_input = []
        for call in calls:
            if call.name != 'exec_py':
                raise RuntimeError(f'Unexpected tool: {call.name}')
            arguments = json.loads(call.arguments)
            output = _execute_code(arguments['code'], namespace)
            next_input.append({
                'type': 'function_call_output',
                'call_id': call.call_id,
                'output': output,
            })
        previous_response_id = response.id

    raise RuntimeError(f'The task reached the {MAX_TURNS}-turn limit.')


def main(model, prompt, task):
    if not SAMPLE_DIR.is_dir():
        raise RuntimeError(f'Missing sample directory: {SAMPLE_DIR}')

    subprocess.run(['open', str(SAMPLE_DIR)], check=True)
    time.sleep(2)

    client = OpenAI()
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
    namespace = {'__name__': '__main__'}
    previous_response_id = None
    usage = []

    output_text, previous_response_id, turn_usage = _run_agent_turn(
        client, model, prompt, task, namespace, previous_response_id
    )
    usage += turn_usage
    print('AGENT:', output_text)

    print_usage(usage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Local computer-use demo')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('task_file', type=Path)
    parser.add_argument('--model', default='gpt-5.6-sol')

    args = parser.parse_args()
    main(
        args.model,
        args.prompt_file.read_text(),
        args.task_file.read_text(),
    )
