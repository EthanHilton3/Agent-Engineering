import subprocess
from pathlib import Path

from tools import ToolBox

toolbox = ToolBox()


@toolbox.tool
def shell(command: str) -> str:
    """
    Run a shell command.
    Returns the exit code and stdout/stderr text in a combined string.
    """
    print('TOOL shell:', command)
    try:
        completed = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = completed.stdout or ""
        return f"Exit code: {completed.returncode}\n{output}"
    except Exception as exc:
        return f"Failed to execute command: {type(exc).__name__}: {exc}"


@toolbox.tool
def read(path: str) -> str:
    """
    Read the specified file.
    `path` is relative to current directory or absolute.
    Returns line-enumerated contents of the file or an error message.
    """
    print('TOOL read:', path)
    try:
        with Path(path).expanduser().open("r", encoding="utf-8") as file:
            return "".join(
                f"{line_number:04}| {line}"
                for line_number, line in enumerate(file, 1)
            )
    except Exception as exc:
        return f"Failed to read file: {type(exc).__name__}: {exc}"


@toolbox.tool
def write(path: str, content: str) -> str:
    """
    Write the `content` to the specified file.
    `path` is relative to current directory or absolute.
    Returns a status message (success or failure with error details).
    """
    print('TOOL write:', path)
    try:
        file_path = Path(path).expanduser()
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Successfully wrote {file_path}"
    except Exception as exc:
        return f"Failed to write file: {type(exc).__name__}: {exc}"


@toolbox.tool
def edit(path: str, replace_this: str, with_this: str) -> str:
    """
    Edit the specified file.
    `path` is relative to current directory or absolute.
    `replace_this` is the content you want to replace; must be unique within the file.
    `with_this` is the new content to insert where `replace_this` is found.
    Returns a status message (success or failure with error details).
    """
    print('TOOL edit:', path)
    try:
        file_path = Path(path).expanduser()
        original = file_path.read_text(encoding="utf-8")
        if not replace_this:
            return "Failed to edit file: text to replace must not be empty"

        occurrences = original.count(replace_this)
        if occurrences != 1:
            if occurrences == 0:
                return "Failed to edit file: text to replace was not found"
            return (
                f"Failed to edit file: text to replace was found {occurrences} times; "
                "it must be unique"
            )

        file_path.write_text(original.replace(replace_this, with_this, 1), encoding="utf-8")
        return f"Successfully edited {file_path}"
    except Exception as exc:
        return f"Failed to edit file: {type(exc).__name__}: {exc}"
