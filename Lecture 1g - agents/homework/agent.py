import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from time import time
from openai import OpenAI
from usage import print_usage
import agent_toolbox
from agent_toolbox import toolbox

MAX_TURNS = 15
WEB_SEARCH_COST_USD = 0.01	# per search, as in the class materials


def _log(transcript: Path | None, text: str):
	"""Append a line of Markdown to the transcript file, if there is one."""
	if transcript:
		with transcript.open("a", encoding="utf-8") as file:
			file.write(text + "\n")


def _short(value, limit: int = 80) -> str:
	"""Shorten long tool arguments (like a whole file's content) for the transcript."""
	text = repr(value)
	return text if len(text) <= limit else text[:limit] + "...'"

def _describe_search(action) -> tuple[str, str]:
	"""Turn a web_search_call's action into a short label and detail for printing."""
	if action.type == "search":
		queries = action.queries or ([action.query] if action.query else [])
		return "web_search", ", ".join(repr(q) for q in queries)
	if action.type == "open_page":
		return "open_page", action.url or ""
	if action.type == "find_in_page":
		return "find_in_page", f"{action.pattern!r} in {action.url}"
	return action.type, ""

def _print_search_cost(total_searches: int, file=sys.stderr):
	"""Print the web search count and cost, which print_usage doesn't include."""
	print(f'Web searches: {total_searches}', file=file)
	print(f'Web search cost (USD): ${total_searches * WEB_SEARCH_COST_USD:.6f}', file=file)

def _count_searches(items) -> int:
	"""Count the web searches OpenAI ran during a turn."""
	return sum(getattr(item, "type", None) == "web_search_call" for item in items)

def _sources(items) -> list[tuple[str, str]]:
	"""Collect (title, url) from the url_citation annotations in the answer, without duplicates."""
	found = []
	for item in items:
		if getattr(item, "type", None) != "message":
			continue
		for content in item.content:
			for annotation in getattr(content, "annotations", []) or []:
				if annotation.type == "url_citation":
					source = (annotation.title, annotation.url)
					if source not in found:
						found.append(source)
	return found


def _run_agent_turn(client, model: str, reasoning: str, history: list, transcript: Path | None, web_search_tool: dict):
	turn_history = []
	turn_usage = []

	for _ in range(MAX_TURNS):
		response = client.responses.create(
			model=model,
			input=history + turn_history,
			reasoning={'effort': reasoning},
			tools=[web_search_tool, *toolbox.tools],
		)

		turn_history.extend(response.output)
		turn_usage.append((response.model, response.usage))

		for item in response.output:
			if item.type == "web_search_call":
				label, detail = _describe_search(item.action)
				print(f'TOOL: {label}', detail)
				_log(transcript, f"> TOOL: `{label}({detail})`\n")

		calls = [
			item for item in response.output
			if item.type == "function_call"
		]

		if not calls:
			return response.output_text, turn_history, turn_usage

		for call in calls:
			name = call.name
			call_id = call.call_id
			raw_arguments = call.arguments

			try:
				arguments = json.loads(raw_arguments)
			except json.JSONDecodeError:
				arguments = {}

			result = toolbox.call_tool(name, arguments)
			shown_args = ", ".join(f"{key}={_short(value)}" for key, value in arguments.items())
			first_line = str(result).strip().splitlines()[0] if str(result).strip() else ""
			_log(transcript, f"> TOOL: `{name}({shown_args})` -> {_short(first_line, 120)}\n")
			turn_history.append({
				'type': 'function_call_output',
				"call_id": call_id,
				'output': str(result)
			})

	return "Stopped: reached MAX_TURNS without finishing.", turn_history, turn_usage


def main(model: str, reasoning: str, prompt: str, transcript: Path | None, web_search_tool: dict):
	client = OpenAI()

	history = [{'role': 'system', 'content': prompt}]
	usage = []
	total_searches = 0
	_log(transcript, f"\n---\n\n# Transcript {datetime.now():%Y-%m-%d %H:%M} "
	                 f"(model={model}, reasoning={reasoning}, auto={agent_toolbox.AUTO_APPROVE}, "
	                 f"search_context_size={web_search_tool['search_context_size']})\n")

	try:
		while True:
			user_message = input('USER: ')
			if not user_message:
				break

			history.append({'role': 'user', 'content': user_message})
			_log(transcript, f"**USER:** {user_message}\n")

			start = time()
			output_text, turn_history, turn_usage = _run_agent_turn(client, model, reasoning, history, transcript, web_search_tool)
			history += turn_history
			usage += turn_usage

			searches = _count_searches(turn_history)
			total_searches += searches
			sources = _sources(turn_history)

			elapsed = round(time() - start, 2)
			print(f'{elapsed} seconds elapsed, {searches} web searches', file=sys.stderr)
			print('AGENT: ', output_text)
			if sources:
				print('Sources:')
				for number, (title, url) in enumerate(sources, 1):
					print(f'  {number}. {title}: {url}')

			_log(transcript, f"**AGENT:** {output_text}\n\n*({elapsed} seconds)*\n")
			if sources:
				_log(transcript, "**Sources:**\n" + "\n".join(f"{n}. [{title}]({url})" for n, (title, url) in enumerate(sources, 1)) + "\n")

	except KeyboardInterrupt:
		print()  # move past the "USER: " prompt line

	print_usage(usage)
	_print_search_cost(total_searches)
	if transcript:
		with transcript.open("a", encoding="utf-8") as file:
			print("```", file=file)  # code block keeps the table's line breaks in Markdown
			print_usage(usage, file=file)
			_print_search_cost(total_searches, file=file)
			print("```", file=file)


# Launch this sucker
if __name__ == "__main__":
	parser = argparse.ArgumentParser('AI Response')
	parser.add_argument('prompt_file', type=Path, nargs='?')
	parser.add_argument('--model', default='gpt-5.6-luna')
	parser.add_argument('--reasoning', default='none')
	parser.add_argument('--auto', action='store_true', help='Run shell commands, writes, and edits without asking for approval.')
	parser.add_argument('--transcript', type=Path, help='Append the conversation to this Markdown file.')
	parser.add_argument('--search-context-size', choices=('low', 'medium', 'high'), default='medium',
	                    help='How much search-result text the model reads per search (more = better answers, more tokens).')

	args = parser.parse_args()
	agent_toolbox.AUTO_APPROVE = args.auto
	prompt = args.prompt_file.read_text(encoding="utf-8") if args.prompt_file else "You are a helpful agent."
	# Facts that change between runs are added here instead of hard-coded in the prompt file.
	prompt += f"\n\n## Environment\n- Working folder: {Path.cwd()}\n- Today's date: {date.today()}\n"

	web_search_tool = {'type': 'web_search', 'search_context_size': args.search_context_size}
	main(model=args.model, reasoning=args.reasoning, prompt=prompt, transcript=args.transcript, web_search_tool=web_search_tool)