import argparse
import json
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage

tool_schemas = [
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
                    "description": "First operand",
                },
                "num2": {
                    "type": "number",
                    "description": "Second operand",
                },
            },
            "required": ["num1", "num2"],
            "additionalProperties": False,
        },
    }
]


def _run_turn(client, model, reasoning, history, tool_schemas):
    start = time()
    turn_history = []
    turn_usage = []
    
    while True:
        response = client.responses.create(
            model=model,
            input=history + turn_history,
            reasoning={'effort': reasoning},
            tools=tool_schemas
        )
        turn_history += response.output
        turn_usage.append((response.model, response.usage))
        
        if response.output_text:
            print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
            return response.output_text, turn_history, turn_usage
        
        tool_results = []
        for output in response.output:
            if output.type == 'function_call':
                args = json.loads(output.arguments)
                result = args['num1'] * args['num2']
                print(f"TOOL: {args['num1']} * {args['num2']} = {result}")
                tool_results.append({
                    'type': 'function_call_output',
                    'call_id': output.call_id,
                    'output': str(result)
                })

        turn_history += tool_results
        

def main(model: str, reasoning: str, prompt: str, text: str):
    client = OpenAI()
    
    history = [{'role': 'system', 'content': prompt}]
    if text:
        history.append({'role': 'user', 'content': text})
        
    output_text, turn_history, turn_usage = _run_turn(client, model, reasoning, history, tool_schemas)
    print(output_text)
    
    print_usage(turn_usage)


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('AI Response')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('input_file', type=Path, nargs='?')
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='none')

    args = parser.parse_args()
    input_text = args.input_file.read_text() if args.input_file else ''
    main(args.model, args.reasoning, args.prompt_file.read_text(), input_text)
