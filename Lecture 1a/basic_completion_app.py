from openai import OpenAI
from time import time
from usage import print_usage
from pathlib import Path
import sys
import argparse

NON_REASONING_MODELS = {'gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano'}

def main(model: str, prompt: str, reasoning: str):
	client = OpenAI()
	start = time()
	kwargs = dict(model = model, input = prompt)
	if model not in NON_REASONING_MODELS:
		kwargs['reasoning'] = { 'effort': reasoning } # Options include: "none", "minimal", "low", "medium", "high", "xhigh", "max"
	response = client.responses.create(**kwargs)
	print(response.output_text)

	print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
	print_usage([(model, response.usage)])

# Launch this sucker
if __name__ == "__main__":
	parser = argparse.ArgumentParser('AI Response')
	parser.add_argument('prompt_file', type = Path)
	parser.add_argument('--model', default = 'gpt-5.6-luna')
	parser.add_argument('--reasoning', default = 'low')
	args = parser.parse_args()
	main(args.model, args.prompt_file.read_text(), args.reasoning)
