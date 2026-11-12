import argparse
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage

# https://byu-cs-mcp-demo.fastmcp.app/mcp

def _run_agent_turn(client, model: str, reasoning: str, history: list, mcp_url: str):
    mcp_tool = {
        'type': 'mcp',
        'server_label': 'Stock_Ticker_Server',
        'server_url': mcp_url,
        'require_approval': 'never',
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


def main(model: str, reasoning: str, prompt: str, mcp_url: str):
    client = OpenAI()

    history = [{'role': 'system', 'content': prompt}]
    usage = []

    while True:
        usr_message = input('\nUSER: ')
        if not usr_message:
            break

        history.append({'role': 'user', 'content': usr_message})
        start = time()
        output_text, turn_history, turn_usage = _run_agent_turn(
            client, model, reasoning, history, mcp_url
        )
        history += turn_history
        usage += turn_usage
        print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
        print('AGENT:', output_text)

    print_usage(usage)


# Launch app
if __name__ == '__main__':
    parser = argparse.ArgumentParser('MCP Bot')
    parser.add_argument('prompt_file', type=Path, nargs='?')
    parser.add_argument('--model', default='gpt-6-luna')
    parser.add_argument('--reasoning', default='none')
    parser.add_argument(
        '--mcp-url',
        default='http://127.0.0.1:8000/mcp',
        help='MCP endpoint URL (for example, an ngrok HTTPS URL ending in /mcp)'
    )

    args = parser.parse_args()
    prompt = args.prompt_file.read_text() if args.prompt_file else 'You are a helpful agent.'
    main(args.model, args.reasoning, prompt, args.mcp_url)
