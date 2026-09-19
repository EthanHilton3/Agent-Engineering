import argparse
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage


def main(model: str, reasoning: str, prompt: str, preamble: str):
    client = OpenAI()
    usage = []

    try:
        previous_response_id = None

        if preamble:
            print(preamble)

        while True:
            user_message = input('USER: ')
            if not user_message:
                break

            start = time()
            request = {
                'model': model,
                'reasoning': {'effort': reasoning},
                'instructions': prompt,
                'input': user_message
            }
            if previous_response_id is not None:
                request['previous_response_id'] = previous_response_id

            response = client.responses.create(**request)
            
            print('AGENT:', response.output_text)
            usage.append((model, response.usage))
            previous_response_id = response.id
            
            print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
    finally:
        print_usage(usage)


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('AI Response')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('--preamble', default='')
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='none')
    args = parser.parse_args()
    main(args.model, args.reasoning, args.prompt_file.read_text(), args.preamble)
