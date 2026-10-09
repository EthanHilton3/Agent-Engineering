import argparse
import base64
import io
import subprocess
import sys
import time
from pathlib import Path

import pyautogui
from openai import OpenAI

from usage import print_usage


SAMPLE_DIR = Path(__file__).with_name('sample_dir').resolve()
MAX_TURNS = 20

KEY_NAMES = {
    'enter': 'enter',
    'return': 'return',
    'esc': 'esc',
    'escape': 'esc',
    'cmd': 'command',
    'command': 'command',
    'ctrl': 'ctrl',
    'control': 'ctrl',
    'alt': 'alt',
    'option': 'alt',
    'shift': 'shift',
    'tab': 'tab',
    'backspace': 'backspace',
    'delete': 'delete',
}


def _as_dict(item):
    if isinstance(item, dict):
        return item
    if hasattr(item, 'model_dump'):
        return item.model_dump(exclude_none=True)
    return dict(item)


def _image_data_url(image):
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def _normalize_key(key):
    return KEY_NAMES.get(key.lower(), key.lower())


def _execute_actions(actions):
    print('\nCOMPUTER ACTIONS\n----------------', file=sys.stderr)
    for action in actions:
        action = _as_dict(action)
        action_type = action.get('type')
        print(action, file=sys.stderr)

        if action_type == 'click':
            pyautogui.click(
                x=action['x'],
                y=action['y'],
                button=action.get('button', 'left'),
            )
        elif action_type == 'double_click':
            pyautogui.doubleClick(
                x=action['x'],
                y=action['y'],
                button=action.get('button', 'left'),
            )
        elif action_type == 'move':
            pyautogui.moveTo(action['x'], action['y'])
        elif action_type == 'type':
            pyautogui.write(action['text'], interval=0.01)
        elif action_type == 'keypress':
            keys = [_normalize_key(key) for key in action.get('keys', [])]
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
        elif action_type == 'drag':
            path = action.get('path', [])
            if path:
                pyautogui.moveTo(path[0]['x'], path[0]['y'])
                pyautogui.mouseDown(button=action.get('button', 'left'))
                for point in path[1:]:
                    pyautogui.moveTo(point['x'], point['y'], duration=0.1)
                pyautogui.mouseUp(button=action.get('button', 'left'))
        elif action_type == 'scroll':
            pyautogui.moveTo(action['x'], action['y'])
            pyautogui.hscroll(action.get('scroll_x', 0))
            pyautogui.scroll(action.get('scroll_y', 0))
        elif action_type == 'wait':
            time.sleep(action.get('ms', 1000) / 1000)
        elif action_type == 'screenshot':
            pass
        else:
            raise RuntimeError(f'Unsupported computer action: {action_type}')

    print('----------------', file=sys.stderr)
    return _image_data_url(pyautogui.screenshot())


def _run_agent_turn(client, model, prompt, task):
    next_input = [{
        'role': 'user',
        'content': [
            {'type': 'input_text', 'text': task},
            {
                'type': 'input_image',
                'image_url': _image_data_url(pyautogui.screenshot()),
                'detail': 'original',
            },
        ],
    }]
    previous_response_id = None
    turn_usage = []

    for _ in range(MAX_TURNS):
        response = client.responses.create(
            model=model,
            instructions=prompt,
            input=next_input,
            previous_response_id=previous_response_id,
            reasoning={'effort': 'low'},
            tools=[{'type': 'computer'}],
        )
        turn_usage.append((response.model, response.usage))

        if response.status != 'completed':
            raise RuntimeError(f'Response stopped with status: {response.status}')

        calls = [
            item for item in response.output
            if item.type == 'computer_call'
        ]
        if not calls:
            if response.output_text:
                return response.output_text, turn_usage
            raise RuntimeError(
                f'No computer call or final response: '
                f'{[item.type for item in response.output]}'
            )

        next_input = []
        for call in calls:
            screenshot = _execute_actions(call.actions)
            next_input.append({
                'type': 'computer_call_output',
                'call_id': call.call_id,
                'output': {
                    'type': 'computer_screenshot',
                    'image_url': screenshot,
                    'detail': 'original',
                },
            })
        previous_response_id = response.id

    raise RuntimeError(f'The task reached the {MAX_TURNS}-turn limit.')


def main(model, prompt, task):
    if not SAMPLE_DIR.is_dir():
        raise RuntimeError(f'Missing sample directory: {SAMPLE_DIR}')

    subprocess.run(['open', str(SAMPLE_DIR)], check=True)
    time.sleep(2)
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1

    client = OpenAI()
    output_text, usage = _run_agent_turn(client, model, prompt, task)
    print('AGENT:', output_text)
    print_usage(usage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Native computer-use demo')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('task_file', type=Path)
    parser.add_argument('--model', default='gpt-5.6-sol')

    args = parser.parse_args()
    main(
        args.model,
        args.prompt_file.read_text(),
        args.task_file.read_text(),
    )
