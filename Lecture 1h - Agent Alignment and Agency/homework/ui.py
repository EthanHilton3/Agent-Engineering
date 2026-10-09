import os
import sys
import threading
from contextlib import contextmanager
from itertools import cycle
from time import sleep


# Enable ANSI escape-sequence handling in supported Windows terminals.
if os.name == "nt":
	os.system("")


_VERBOSE = False
_TTY = sys.stdout.isatty()
_RESET = "\033[0m"
_PROMPT_MARK = "›" if _TTY else ">"
_RESULT_MARK = "↳" if _TTY else "->"
_SUCCESS_MARK = "✓" if _TTY else "ok"
_FAILURE_MARK = "✗" if _TTY else "x"
_ELLIPSIS = "…" if _TTY else "..."
_COMPLETION_SEPARATOR = " · " if _TTY else " - "


def configure(verbose: bool = False) -> None:
	"""Configure command-line display options."""
	global _VERBOSE
	_VERBOSE = verbose


def _style(text: str, code: str) -> str:
	if not _TTY:
		return text
	return f"\033[{code}m{text}{_RESET}"


YOU = _style("You", "1;36")
AGENT = _style("Agent", "1;32")


def prompt() -> str:
	"""Read one user message with consistent conversation spacing."""
	return input(f"\n{YOU} {_PROMPT_MARK} ")


def agent_message(text: str) -> None:
	"""Print an agent response in the conversation layout."""
	print(f"\n{AGENT} {_PROMPT_MARK}")
	if not _TTY:
		print(text)
		return

	from rich.console import Console
	from rich.markdown import Markdown

	console = Console(width=min(Console().width, 100))
	console.print(Markdown(text, code_theme="monokai"))


def sources(items: list[tuple[str, str]]) -> None:
	"""Display the unique web sources cited by an agent response."""
	print(f"\n{_style('Sources', '1')}")
	for number, (title, url) in enumerate(items, 1):
		print(f"  {number}. {title}: {_style(url, '2')}")


class _Spinner:
	def __init__(self, message: str):
		self.message = message
		self._stopped = threading.Event()
		self._thread = None

	def start(self) -> None:
		if not _TTY:
			return
		self._thread = threading.Thread(target=self._animate, daemon=True)
		self._thread.start()

	def _animate(self) -> None:
		for frame in cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
			if self._stopped.is_set():
				break
			print(f"\r  {_style(frame, '36')} {self.message}", end="", flush=True)
			sleep(0.08)

	def stop(self) -> None:
		if not _TTY:
			return
		self._stopped.set()
		if self._thread:
			self._thread.join()
		print("\r\033[2K", end="", flush=True)


@contextmanager
def thinking(message: str = "Thinking…"):
	"""Show a temporary spinner while waiting for the model."""
	spinner = _Spinner(message)
	spinner.start()
	try:
		yield
	finally:
		spinner.stop()


def _failed(result: str) -> bool:
	"""Return whether a tool result begins with a known failure message."""
	text = str(result).lstrip()
	lower = text.lower()
	failure_prefixes = (
		"error:",
		"command rejected by the user",
		"write rejected by the user",
		"edit rejected by the user",
		"command timed out",
		"command did not stop",
	)
	if lower.startswith(failure_prefixes):
		return True

	first_line = lower.splitlines()[0] if lower.splitlines() else ""
	if first_line.startswith("exit code:"):
		return first_line != "exit code: 0"
	return False


def _target(arguments: dict) -> str:
	for key in ("path", "command"):
		if key in arguments:
			value = str(arguments[key])
			return value if len(value) <= 90 else value[:87] + _ELLIPSIS
	return ""


def tool_start(name: str, arguments: dict) -> None:
	"""Print a tool call before it starts running."""
	target = _target(arguments)
	line = f"  {_RESULT_MARK} {name}"
	if target:
		line += f"  {_style(target, '2')}"
	print(line, flush=True)


def web_search(label: str, detail: str) -> None:
	"""Display a completed built-in web-search action."""
	shown = detail if len(detail) <= 120 else detail[:117] + _ELLIPSIS
	line = f"  {_RESULT_MARK} {label}"
	if shown:
		line += f"  {_style(shown, '2')}"
	print(line)
	print(f"    {_style(_SUCCESS_MARK, '32')} done")


def tool_result(name: str, arguments: dict, result: str) -> None:
	"""Print a tool's status, with expanded details in verbose mode."""
	failed = _failed(result)
	if failed:
		symbol = _style(_FAILURE_MARK, "31")
		lines = str(result).splitlines()
		first_line = lines[0] if lines else "(no output)"
		print(f"    {symbol} {first_line}")
	else:
		symbol = _style(_SUCCESS_MARK, "32")
		print(f"    {symbol} done")
	if _VERBOSE:
		print(_style(f"      arguments: {arguments!r}", "2"))
		for output_line in str(result).splitlines() or ["(no output)"]:
			print(_style(f"      {output_line}", "2"))


def completion(elapsed: float, tool_calls: int, web_searches: int = 0) -> None:
	"""Print compact timing and tool-use metadata after a response."""
	tools = f"{_COMPLETION_SEPARATOR}{tool_calls} tool call{'s' if tool_calls != 1 else ''}" if tool_calls else ""
	searches = (f"{_COMPLETION_SEPARATOR}{web_searches} web search{'es' if web_searches != 1 else ''}"
	            if web_searches else "")
	print()
	print(_style(f"  Completed in {elapsed:.2f}s{tools}{searches}", "2"))
