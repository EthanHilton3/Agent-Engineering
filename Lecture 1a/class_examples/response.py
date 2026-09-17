import argparse
import sys
from pathlib import Path
from time import time

from openai import OpenAI

from usage import print_usage


def main(model: str, reasoning: str, prompt: str):
    client = OpenAI()
    start = time()
    response = client.responses.create(
        model=model,
        input=prompt,
        reasoning={'effort': reasoning}
    )
    print(response.output_text)

    print(f'{round(time()-start, 2)} seconds elapsed', file=sys.stderr)
    print_usage([(model, response.usage)])


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('AI Response')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='low')
    args = parser.parse_args()
    main(args.model, args.reasoning, args.prompt_file.read_text())
