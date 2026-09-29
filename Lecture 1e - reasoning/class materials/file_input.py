import argparse
import json
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage


def main(
    model: str,
    reasoning: str,
    prompt: str,
    text: str,
    output_schema: Path | None = None,
):
    client = OpenAI()
    prompt += text

    request = {
        'model': model,
        'input': prompt,
        'reasoning': {'effort': reasoning},
    }
    if output_schema:
        request['text'] = {
            'format': {
                'type': 'json_schema',
                'name': output_schema.stem,
                'strict': True,
                'schema': json.loads(output_schema.read_text()),
            }
        }

    start = time()
    response = client.responses.create(**request)
    print(response.output_text)

    print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
    print_usage([(model, response.usage)])


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('AI Response')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('input_file', type=Path)
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='none')
    parser.add_argument(
        '--output',
        type=Path,
        help='JSON file containing the structured output schema',
    )

    args = parser.parse_args()
    main(
        args.model,
        args.reasoning,
        args.prompt_file.read_text(),
        args.input_file.read_text(),
        args.output,
    )
