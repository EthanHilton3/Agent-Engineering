import argparse
import os
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage

MAPS_MCP_URL = 'https://mapstools.googleapis.com/mcp'


def _run_agent_turn(client, model: str, reasoning: str, history: list, api_key: str):
    mcp_tool = {
        'type': 'mcp',
        'server_label': 'google-maps',
        'server_url': MAPS_MCP_URL,
        'require_approval': 'never',
        'headers': {
            'X-Goog-Api-Key': api_key,
        },
    }

    response = client.responses.create(
        model=model,
        input=history,
        reasoning={'effort': reasoning},
        tools=[mcp_tool]
    )

    for output in response.output:
        if output.type == 'mcp_call':
            print(f'MCP CALL: {output.name}({output.arguments})', file=sys.stderr)

    if not response.output_text:
        raise RuntimeError(f'No agent reply was returned: {response.output}')

    return response.output_text, response.output, [(response.model, response.usage)]


def main(model: str, reasoning: str, prompt: str, api_key: str):
    client = OpenAI()
    history = [{'role': 'system', 'content': prompt}]
    usage = []

    while True:
        try:
            usr_message = input('\nUSER: ')
        except EOFError:
            break

        if not usr_message:
            break

        history.append({'role': 'user', 'content': usr_message})
        start = time()
        output_text, turn_history, turn_usage = _run_agent_turn(
            client, model, reasoning, history, api_key
        )
        history += turn_history
        usage += turn_usage
        print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
        print('AGENT:', output_text)

    print_usage(usage)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Google Maps MCP Bot')
    parser.add_argument('prompt_file', type=Path, nargs='?')
    parser.add_argument('--model', default='gpt-6-luna')
    parser.add_argument('--reasoning', default='none')
    args = parser.parse_args()

    api_key = os.getenv('GOOGLE_API_KEY')
    if not api_key:
        parser.error('Set GOOGLE_API_KEY before starting mapbot.')

    prompt = (
        args.prompt_file.read_text()
        if args.prompt_file
        else (
            'You are a helpful agent with access to Google Maps tools. '
            'Use them for place searches, routes, weather, and location lookups. '
            'Base location and route claims on tool results; do not invent '
            'turn-by-turn directions.'
        )
    )
    main(args.model, args.reasoning, prompt, api_key)
