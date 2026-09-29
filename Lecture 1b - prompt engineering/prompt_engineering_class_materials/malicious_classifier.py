import argparse
import sys
from pathlib import Path
from time import time

import pandas as pd
from openai import OpenAI

from homework.usage import print_usage


# get the email data. Schema is: subject,body,label {0,1}
def load_data(prompt: str, samples: int = 10) -> pd.DataFrame:
    data = pd.read_csv('Ling.csv')
    sampled_data = pd.concat([
        data[data.label == 1].iloc[:samples],
        data[data.label == 0].iloc[:samples]],
        ignore_index=True
    )

    def fmt_prompt(row):
        """
        Uses .format() to inject `row['subject']` and `row['body']`
        into the template in a single operation.
        """
        return prompt.format(**row)

    sampled_data["prompt"] = sampled_data.apply(fmt_prompt, axis=1)
    return sampled_data

def main(model: str, prompt: str, samples: int):
    client = OpenAI()
    usages = []
    data = load_data(prompt, samples)

    start = time()
    for row in data.itertuples():
        print(f"{'-' * 50}\nEXPECTED: {row.label}")
        response = client.responses.create(
            model=model,
            input=row.prompt,
            reasoning={'effort': 'low'}
        )
        print(response.output_text)
        usages.append(response.usage)

    print(f'{round(time()-start, 2)} seconds elapsed', file=sys.stderr)
    print_usage([(model, usage) for usage in usages])


# Launch app
if __name__ == "__main__":
    parser = argparse.ArgumentParser('AI Response')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('--model', default='gpt-5-nano')
    parser.add_argument('--samples', type=int, default=10)
    args = parser.parse_args()

    main(args.model, args.prompt_file.read_text(), args.samples)
