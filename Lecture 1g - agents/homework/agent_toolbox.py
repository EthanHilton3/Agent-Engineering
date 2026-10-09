from pathlib import Path
import subprocess
from tools import ToolBox

toolbox = ToolBox()

# Settings. agent.py sets AUTO_APPROVE from the --auto flag.
AUTO_APPROVE = False		# skip approval for shell, write, and edit
MAX_TOOL_OUTPUT = 20000		# characters of shell output sent back to the model
MAX_TIMEOUT = 300			# seconds; the most the model may ask for
MAX_READ_LINES = 400		# lines returned by one read call
MAX_READ_CHARS = 20000		# characters returned by one read call
PREVIEW_LINES = 15			# lines of content shown in an approval prompt
PREVIEW_WIDTH = 200			# characters per line shown in an approval prompt
# Full path on purpose: plain "bash" finds System32\bash.exe first, which is WSL.
GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"


def _approve(action: str, details: str) -> bool:
	"""Ask the user before an action. Anything but y/yes means no."""
	if AUTO_APPROVE:
		return True
	print(f"\nThe agent wants to {action}:")
	print(details)
	try:
		answer = input("Allow? [y/N] ").strip().lower()
	except EOFError:
		answer = ""
	return answer in {"y", "yes"}


def _preview(text: str, prefix: str) -> str:
	"""Show the first PREVIEW_LINES lines of text for an approval prompt, each cut to PREVIEW_WIDTH."""
	lines = text.splitlines() or [""]
	shown = []
	for line in lines[:PREVIEW_LINES]:
		if len(line) > PREVIEW_WIDTH:
			line = line[:PREVIEW_WIDTH] + f" ... ({len(line) - PREVIEW_WIDTH:,} more characters)"
		shown.append(prefix + line)
	if len(lines) > PREVIEW_LINES:
		shown.append(f"{prefix}... ({len(lines) - PREVIEW_LINES} more lines)")
	return "\n".join(shown)


def _truncate(output: str) -> str:
	"""Keep the start and end of long output so one command can't flood the history."""
	if not output:
		return "(no output)"
	if len(output) <= MAX_TOOL_OUTPUT:
		return output
	half = MAX_TOOL_OUTPUT // 2
	cut = len(output) - MAX_TOOL_OUTPUT
	return f"{output[:half]}\n...[{cut:,} characters truncated]...\n{output[-half:]}"


def _bash_command(command: str, timeout: int) -> list[str]:
	"""
	Build the Git Bash call that runs `command` under bash's own `timeout`.
	`timeout` asks the command to stop after `timeout` seconds, force-kills it
	2 seconds later if needed, and exits with code 124. The command is passed as
	its own argument ("$1") instead of being pasted into the string, so quotes
	inside it can't break anything.
	"""
	return [GIT_BASH, "-c", 'timeout -k 2 "$0" bash -c "$1"', str(timeout), command]


@toolbox.tool
def list_dir(path: str) -> str:
	"""
	List the contents of a directory.

	Use this to find out what files exist before reading or editing them.

	Args:
		path: Directory to list, relative to the working folder or absolute.

	Returns:
		One entry per line, folders first; folder names end with "/".
		"(empty directory)" if there is nothing in it, or an error message.
	"""
	print('TOOL: list_dir', path)
	try:
		p = Path(path)
		if not p.exists():
			return f"Path '{path}' does not exist"
		if p.is_file():
			return f"Path '{path}' is a file, not a directory"

		lines = [i.name + "/" if i.is_dir() else i.name
		         for i in sorted(p.iterdir(), key=lambda i: (not i.is_dir(), i.name.lower()))]

		if not lines:
			return "(empty directory)"
		return "\n".join(lines)

	except Exception as e:
		return f"Failed to list directory: {type(e).__name__}: {e}"


@toolbox.tool
def read(path: str, start_line: int) -> str:
	"""
	Read a text file, with line numbers.

	Always read a file before editing it. Long files are returned in sections of
	up to 400 lines; a note at the end gives the start_line for the next section.

	Args:
		path: File to read, relative to the working folder or absolute.
		start_line: First line to return, counting from 1. Use 1 to start at the top.

	Returns:
		Lines formatted as "0001| text", plus a note if more of the file remains.
		"(empty file)", or an error message for a missing, folder, or binary path.
	"""
	print('TOOL: read', path, f'(from line {start_line})')
	try:
		p = Path(path).expanduser()
		if not p.exists():
			return f"Path '{path}' does not exist"
		if p.is_dir():
			return f"Path '{path}' is a directory, not a file"
		with p.open("r", encoding="utf-8") as file:
			lines = file.readlines()
		if not lines:
			return "(empty file)"

		total = len(lines)
		start_line = max(1, start_line)
		if start_line > total:
			return f"start_line {start_line} is past the end of '{path}', which has {total} lines."

		# Add whole lines until either limit is reached, so no line is cut in half.
		shown = []
		size = 0
		end_line = start_line - 1
		for number in range(start_line, min(total, start_line - 1 + MAX_READ_LINES) + 1):
			numbered = f"{number:04}| {lines[number - 1]}"
			if len(numbered) > MAX_READ_CHARS:		# one huge line, e.g. minified code
				numbered = numbered[:MAX_READ_CHARS] + " ...[line cut off]\n"
			if shown and size + len(numbered) > MAX_READ_CHARS:
				break
			shown.append(numbered)
			size += len(numbered)
			end_line = number

		text = "".join(shown)
		if end_line < total:
			if not text.endswith("\n"):
				text += "\n"
			text += (f"[Showing lines {start_line}-{end_line} of {total}. "
			         f"To read more, call read with start_line={end_line + 1}.]")
		return text
	except UnicodeDecodeError:
		return f"'{path}' appears to be a binary file (not UTF-8 text), so read can't show it."
	except Exception as e:
		return f"Failed to read file: {type(e).__name__}: {e}"


@toolbox.tool
def write(path: str, content: str) -> str:
	"""
	Create a new file, or completely replace an existing one.

	To change part of an existing file, use edit instead. Missing parent folders
	are created. The user must approve each write unless auto-approve is on.

	Args:
		path: File to write, relative to the working folder or absolute.
		content: The complete new contents of the file.

	Returns:
		"Created '<path>'" or "Overwrote '<path>'", a rejection message if the
		user declines, or an error message.
	"""
	print('TOOL: write', path)
	try:
		p = Path(path).expanduser()
		if p.is_dir():
			return f"Path '{path}' is a directory, not a file"
		existed = p.exists()

		action = f"{'overwrite' if existed else 'create'} '{path}'"
		if not _approve(action, _preview(content, "  | ")):
			return "Write rejected by the user. Ask them how they would like to proceed."

		p.parent.mkdir(parents=True, exist_ok=True)
		p.write_text(content, encoding="utf-8", newline="")
		if existed:
			return f"Overwrote '{path}'"
		return f"Created '{path}'"
	except Exception as e:
		return f"Failed to write file: {type(e).__name__}: {e}"


@toolbox.tool
def edit(path: str, replace_this: str, with_this: str) -> str:
	"""
	Replace one exact piece of text in an existing file.

	Read the file first, then copy replace_this exactly from it, including
	indentation. Include enough surrounding lines that it appears only once.
	The user must approve each edit unless auto-approve is on.

	Args:
		path: File to edit, relative to the working folder or absolute.
		replace_this: The exact text to replace. Must appear exactly once in the file.
		with_this: The text to put in its place.

	Returns:
		"Edited '<path>'", a rejection message if the user declines, or an error
		message saying what to fix (text not found, or found more than once).
	"""
	print('TOOL: edit', path)
	try:
		p = Path(path).expanduser()
		if not replace_this:
			return "Failed to edit file: text to replace must not be empty"
		if replace_this == with_this:
			return "No change: replace_this and with_this are identical"
		if not p.exists():
			return f"Path '{path}' does not exist. Use write to create a new file."
		if p.is_dir():
			return f"Path '{path}' is a directory, not a file"

		# newline="" keeps the file's own line endings. read shows the model "\n",
		# so convert its text to "\r\n" when the file uses Windows line endings.
		original = p.read_text(encoding="utf-8", newline="")
		if "\r\n" in original:
			replace_this = replace_this.replace("\r\n", "\n").replace("\n", "\r\n")
			with_this = with_this.replace("\r\n", "\n").replace("\n", "\r\n")

		occurrences = original.count(replace_this)
		if occurrences == 0:
			return (
				f"Text to replace not found in '{path}'. It must match exactly, including "
				"whitespace and indentation. Read the file again to copy the exact text."
			)
		if occurrences > 1:
			return (
				f"Text to replace was found {occurrences} times in '{path}'. "
				"Include more surrounding lines so it matches only once."
			)

		change = _preview(replace_this, "  - ") + "\n" + _preview(with_this, "  + ")
		if not _approve(f"edit '{path}'", change):
			return "Edit rejected by the user. Ask them how they would like to proceed."

		p.write_text(original.replace(replace_this, with_this, 1), encoding="utf-8", newline="")
		return f"Edited '{path}'"
	except Exception as e:
		return f"Failed to edit file: {type(e).__name__}: {e}"


@toolbox.tool
def shell(command: str, timeout: int) -> str:
	"""
	Run a command in bash (Git Bash on Windows).

	Use for running programs, tests, git, and pip. For files, prefer list_dir,
	read, write, and edit. Linux commands like ls, cat, grep, and pipes work;
	Windows paths can be written as C:/Users/... or /c/Users/.... Each call
	starts a new shell in the working folder, so cd does not carry over between
	calls; use "cd folder && command" in one call instead. Do not start servers
	or other commands that never finish. The user must approve each command
	unless auto-approve is on.

	Args:
		command: The bash command to run.
		timeout: Most seconds the command may run (1-300). About 30 for quick
			commands; more for installs or test suites.

	Returns:
		The exit code and combined stdout/stderr. Long output is cut in the middle.
		A command that runs past timeout is stopped and its partial output returned.
		A rejection message if the user declines.
	"""
	print('TOOL: shell', command)
	if not _approve("run", f"  {command}"):
		return "Command rejected by the user. Ask them how they would like to proceed."

	timeout = max(1, min(timeout, MAX_TIMEOUT))
	try:
		proc = subprocess.Popen(
			_bash_command(command, timeout),
			stdin=subprocess.DEVNULL,
			stdout=subprocess.PIPE,
			stderr=subprocess.STDOUT,
			text=True,
			encoding="utf-8",
			errors="replace",
		)
		try:
			output, _ = proc.communicate(timeout=timeout + 10)
		except subprocess.TimeoutExpired:
			# Backup only: bash's timeout should always stop the command first.
			proc.kill()
			return f"Command did not stop after {timeout} seconds and was killed."

		if proc.returncode == 124:
			return f"Command timed out after {timeout} seconds.\nOutput before timeout:\n{_truncate(output)}"
		return f"Exit code: {proc.returncode}\nOutput:\n{_truncate(output)}"
	except Exception as e:
		return f"Failed to run shell command: {type(e).__name__}: {e}"
