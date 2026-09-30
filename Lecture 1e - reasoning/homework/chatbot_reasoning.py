import argparse
import json
import sys
from pathlib import Path
from time import time
import openai
from openai import OpenAI
from usage import print_usage, _aggregate_usage, _calculate_cost_usd


MODEL_EFFORTS = {
	'gpt-5.6-luna': ['none', 'low', 'medium', 'high', 'xhigh'],
	'gpt-5':        ['minimal', 'low', 'medium', 'high'],
	'gpt-5-mini':   ['minimal', 'low', 'medium', 'high'],
	'gpt-5-nano':   ['minimal', 'low', 'medium', 'high'],
}

ALL_EFFORTS = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh']

SUMMARY_TYPES = ['auto', 'concise', 'detailed']


def print_models():
	print("Supported models (and their effort levels):")
	for m, efforts in MODEL_EFFORTS.items():
		print(f"  {m:<14} {', '.join(efforts)}")


def print_history(history: list):
	print(f"History ({len(history)} items):")
	for item in history:
		if isinstance(item, dict):
			# Messages we added ourselves: system prompt and user messages
			text = item['content']
			label = item['role']
		elif item.type == 'message':
			# The model's reply
			text = ''.join(c.text for c in item.content if c.type == 'output_text')
			label = 'assistant'
		elif item.type == 'reasoning':
			text = ' '.join(s.text for s in item.summary) or '(no summary)'
			label = 'reasoning'
		else:
			text = ''
			label = item.type
		# Collapse newlines so each item stays on one line
		text = ' '.join(text.split())
		print(f"  [{label}] {text[:200]}")


def turn_cost(model: str, turn_usage) -> float:
	# Cost of a single response, using the same pricing table as print_usage
	return _calculate_cost_usd(_aggregate_usage([(model, turn_usage)]))


def turn_stats(model: str, effort: str, seconds: float, turn_usage) -> str:
	reasoning_tokens = turn_usage.output_tokens_details.reasoning_tokens
	return (
		f'[{model} | effort={effort} | {seconds:.2f}s | '
		f'in={turn_usage.input_tokens} out={turn_usage.output_tokens} '
		f'(reasoning={reasoning_tokens}) | ${turn_cost(model, turn_usage):.6f}]'
	)


def new_history(prompt: str) -> list:
	if prompt:
		return [{'role': 'system', 'content': prompt}]
	return []


def find_schema(name: str) -> Path | None:
	# Look for the schema file where you ran the program, then next to this script
	for path in (Path(name), Path(__file__).parent / name):
		if path.exists():
			return path
	return None


def load_schema(path: Path) -> dict:
	return {
		'format': {
			'type': 'json_schema',
			'name': path.stem,
			'strict': True,
			'schema': json.loads(path.read_text()),
		}
	}


def build_request(model: str, messages: list, reasoning: dict, text_format: dict | None) -> dict:
	request = {
		'model': model,
		'input': messages,
		'reasoning': reasoning,
	}
	if text_format:
		request['text'] = text_format
	return request


def run_compare(client: OpenAI, question: str, prompt: str, model: str, usage: list, text_format: dict | None):
	# Ask the same question once per effort level, each with a fresh history,
	# then print a table comparing time, tokens and cost.
	rows = []
	for effort in MODEL_EFFORTS[model]:
		messages = new_history(prompt)
		messages.append({'role': 'user', 'content': question})
		print(f'\n===== {model} | effort={effort} =====')
		start = time()
		try:
			response = client.responses.create(**build_request(model, messages, {'effort': effort}, text_format))
		except openai.APIError as e:
			print(f'API error: {e}')
			continue
		seconds = time() - start

		# Record usage so these runs are included in the final total
		usage.append((model, response.usage))
		print(response.output_text)
		print(turn_stats(model, effort, seconds, response.usage), file=sys.stderr)

		answer = response.output_text
		if text_format:
			# Show the schema's "answer" field in the table instead of the start of the JSON
			try:
				answer = str(json.loads(answer).get('answer', answer))
			except json.JSONDecodeError:
				pass
		answer = ' '.join(answer.split())
		rows.append((
			effort,
			seconds,
			response.usage.output_tokens,
			response.usage.output_tokens_details.reasoning_tokens,
			turn_cost(model, response.usage),
			answer,
		))

	if not rows:
		return
	total_cost = sum(row[4] for row in rows)
	print(f'\nComparison on {model}:')
	print(f"  {'effort':<8} {'time':>7} {'out tok':>8} {'reasoning':>10} {'cost':>11}   answer")
	for effort, seconds, out_tokens, reasoning_tokens, cost, answer in rows:
		print(f"  {effort:<8} {seconds:>6.2f}s {out_tokens:>8} {reasoning_tokens:>10} {'$' + format(cost, '.6f'):>11}   {answer[:50]}")
	print(f'  compare total cost: ${total_cost:.6f}')


def handle_user_command(user_msg: str, history: list, prompt: str, model_setting: dict, reasoning_setting: dict,
						output_setting: dict, client: OpenAI, usage: list) -> bool:
	# Run a /command. Returns True if user_msg was a command (so it shouldn't be sent to the model).
	if not user_msg.startswith('/'):
		return False

	parts = user_msg.split()
	command = parts[0]
	arg = parts[1] if len(parts) > 1 else None

	if command == '/help':
		print("Available commands:")
		print("  /help           - List all available commands")
		print("  /effort <level> - Set reasoning effort (allowed levels depend on the model, see /models)")
		print(f"  /summary <type> - Set summary type ({', '.join(SUMMARY_TYPES)})")
		print("  /model <name>   - Set the model to use")
		print("  /models         - Lists all the supported models")
		print("  /schema <file>  - Use a JSON schema for structured output (/schema off for plain text)")
		print("  /settings       - Show the current model, effort, summary and schema settings")
		print("  /history        - Show the conversation history")
		print("  /reset          - Reset the conversation history")
		print("  /compare <question> - Ask the question at every effort level and compare time, tokens and cost")
		return True

	if command == '/effort':
		allowed = MODEL_EFFORTS[model_setting['name']]
		if arg is None:
			print(f'usage: /effort <level>  ({", ".join(allowed)})')
		elif arg in allowed:
			reasoning_setting['effort'] = arg
			print(f'effort set to {reasoning_setting["effort"]}')
		else:
			print(f'unsupported effort level for {model_setting["name"]}: {arg}')
			print(f'choose one of: {", ".join(allowed)}')
		return True

	if command == '/summary':
		if arg is None:
			print(f'usage: /summary <type>  ({", ".join(SUMMARY_TYPES)})')
		elif arg in SUMMARY_TYPES:
			reasoning_setting['summary'] = arg
			print(f'summary set to {reasoning_setting["summary"]}')
		else:
			print(f'unsupported summary type: {arg}')
			print(f'choose one of: {", ".join(SUMMARY_TYPES)}')
		return True

	if command == '/model':
		if arg is None:
			print('usage: /model <name>')
			print_models()
		elif arg in MODEL_EFFORTS:
			model_setting['name'] = arg
			print(f'model set to {model_setting["name"]}')
			# Switching models can leave an effort level the new model rejects
			allowed = MODEL_EFFORTS[arg]
			if reasoning_setting['effort'] not in allowed:
				reasoning_setting['effort'] = allowed[0]
				print(f'effort level not supported by {arg}, changed to {allowed[0]}')
		else:
			print(f'unsupported model: {arg}')
			print_models()
		return True

	if command == '/models':
		print_models()
		return True

	if command == '/settings':
		print("Current settings:")
		print(f"  model:   {model_setting['name']}")
		print(f"  effort:  {reasoning_setting['effort']}")
		print(f"  summary: {reasoning_setting.get('summary', 'off')}")
		print(f"  schema:  {output_setting['name'] or 'off'}")
		print(f"  system prompt: {'yes' if prompt else 'none'}")
		return True

	if command == '/schema':
		if arg is None:
			print('usage: /schema <file.json> | off')
		elif arg == 'off':
			output_setting['text'] = None
			output_setting['name'] = None
			print('structured output off')
		else:
			path = find_schema(arg)
			if path is None:
				print(f'schema file not found: {arg}')
			else:
				try:
					output_setting['text'] = load_schema(path)
					output_setting['name'] = path.name
					print(f'using schema {path.name}')
				except json.JSONDecodeError as e:
					print(f'invalid JSON in {path.name}: {e}')
		return True

	if command == '/history':
		print_history(history)
		return True

	if command == '/reset':
		history.clear()
		history.extend(new_history(prompt))
		print('history reset')
		return True

	if command == '/compare':
		# Everything after "/compare" is the question, not just the first word
		question = user_msg[len('/compare'):].strip()
		if not question:
			print('usage: /compare <question>')
		else:
			run_compare(client, question, prompt, model_setting['name'], usage, output_setting['text'])
		return True

	print(f'unknown command: {command}  (try /help)')
	return True


def main(model: str, reasoning: str, summary: str | None, prompt: str, schema: str | None):
	client = OpenAI()
	usage = []
	history = new_history(prompt)

	model_setting = {'name' : model}
	reasoning_setting = {'effort': reasoning}
	if summary:
		reasoning_setting['summary'] = summary

	# Structured output: 'text' is the format sent to the API, 'name' is for display
	output_setting = {'text': None, 'name': None}
	if schema:
		path = find_schema(schema)
		if path is None:
			print(f'schema file not found: {schema}  (continuing with plain text)')
		else:
			output_setting['text'] = load_schema(path)
			output_setting['name'] = path.name

	print("use the command \'/help\' to list all avalaible commands")

	try:
		while True:
			user_msg = input('USER: ')
			if not user_msg:
				break

			if handle_user_command(user_msg, history, prompt, model_setting, reasoning_setting,
								   output_setting, client, usage):
				continue

			history.append({'role': 'user', 'content': user_msg})

			start = time()
			try:
				response = client.responses.create(
					**build_request(model_setting['name'], history, reasoning_setting, output_setting['text'])
				)
			except openai.APIError as e:
				print(f'API error: {e}')
				# Remove the failed message so it isn't resent with the next request
				history.pop()
				continue

			for item in response.output:
				if item.type == 'reasoning':
					for s in item.summary:
						print('[reasoning]', s.text)
			print(response.output_text)
			usage.append((model_setting['name'], response.usage))
			history.extend(response.output)

			print(turn_stats(model_setting['name'], reasoning_setting['effort'], time() - start, response.usage), file=sys.stderr)
	finally:
		print_usage(usage)


# Launch app
if __name__ == "__main__":
	parser = argparse.ArgumentParser('AI Response')
	parser.add_argument('prompt_file', type=Path, nargs='?', default=None)
	parser.add_argument('--model', default='gpt-5.6-luna', choices=list(MODEL_EFFORTS))
	parser.add_argument('--reasoning', default='none', choices=ALL_EFFORTS)
	parser.add_argument('--summary', default=None, choices=SUMMARY_TYPES)
	parser.add_argument('--schema', default=None, help='JSON schema file for structured output')
	args = parser.parse_args()
	prompt = args.prompt_file.read_text() if args.prompt_file else ''
	main(args.model, args.reasoning, args.summary, prompt, args.schema)
