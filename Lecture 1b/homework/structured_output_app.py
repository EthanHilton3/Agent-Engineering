"""structured_output_app.py -- basic_completion_app.py, but with enforced JSON output.

1A's basic_completion_app.py only ever printed response.output_text: free text.
That's why the BOM-sermon experiment on gpt-4.1 hallucinated writing a file
instead of actually writing one -- there was no schema, no tool, just prose
describing an action that never happened.

This app passes a JSON schema straight into the responses.create() call via
`text.format` (type "json_schema", strict=True), so the API itself guarantees
a parseable object back -- not just a prompt that politely asks for one, the
way multi-translate.md does with a fenced text template. If the schema
includes "file_type", "filename", and "content" fields, this app writes that
file to disk itself, so "write your output to a file" is something the code
does deterministically, not something the model claims to have done.

The model can't pick a non-colliding filename on its own, either: each
responses.create() call is a stateless completion with no visibility into
what's already on disk. timestamped_path() below sidesteps that entirely by
stamping the current datetime onto a short prefix instead of asking the
model to reason about the filesystem.

Different file types need different comment/header conventions (a .py file
needs its header commented out to stay valid Python; a .md file reads better
with Markdown bold/rule syntax than a plain divider). write_output() dispatches
to one small formatter per file_type instead of branching on file extension.
"""
from datetime import datetime
from openai import OpenAI
from time import time
from usage import print_usage, format_usage_markdown, format_usage_text
from pathlib import Path
import json
import sys
import argparse

NON_REASONING_MODELS = {'gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'gpt-4.1-nano'}


def timestamped_path(proposed_filename: str, suffix: str) -> Path:
    prefix = Path(proposed_filename).stem.split('_')[0]
    stamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    return Path(f'{prefix}_{stamp}{suffix}')


def _header_lines(result: dict) -> list[str]:
    # Every other string field the schema returned (author, sermon_title, ...)
    # is metadata about the content, not the content itself -- surface it as a
    # readable header instead of silently dropping it on the floor.
    return [
        f'{key.replace("_", " ").title()}: {value}'
        for key, value in result.items()
        if key not in ('filename', 'content', 'file_type') and isinstance(value, str)
    ]


def format_txt(result: dict, content: str) -> str:
    header_lines = _header_lines(result)
    if not header_lines:
        return content
    return '\n'.join(header_lines) + '\n' + '-' * 40 + '\n\n' + content


def format_py(result: dict, content: str) -> str:
    # Plain text at the top of a .py file isn't valid Python, so comment the
    # header out (# ...) instead so the generated code still compiles.
    header_lines = _header_lines(result)
    if not header_lines:
        return content
    commented = [f'# {line}' for line in header_lines]
    return '\n'.join(commented) + '\n' + f"# {'-' * 40}" + '\n\n' + content


def format_md(result: dict, content: str) -> str:
    header_lines = [f'**{line.split(": ", 1)[0]}:** {line.split(": ", 1)[1]}' for line in _header_lines(result)]
    if not header_lines:
        return content
    return '\n'.join(header_lines) + '\n\n---\n\n' + content


WRITERS = {'txt': format_txt, 'py': format_py, 'md': format_md}


def usage_footer(file_type: str, model: str, usage, reasoning: str) -> str:
    reasoning_line = f'Reasoning Level: {reasoning}'
    if model in NON_REASONING_MODELS:
        reasoning_line += f' (not applicable for {model})'

    if file_type == 'md':
        return f'**{reasoning_line}**\n\n' + format_usage_markdown(model, usage)

    text = reasoning_line + '\n' + format_usage_text(model, usage)
    if file_type == 'py':
        # Keep the footer a valid Python comment block so the file still compiles.
        text = '\n'.join(f'# {line}' if line else '#' for line in text.splitlines())
    return text


def render_fields(result: dict) -> str:
    # For schemas with no separate "content" field (e.g. the devotional
    # summarizer), the structured fields *are* the content -- render them
    # directly instead of also asking the model to restate its own
    # key_takeaways/speaker_emphasis/etc. as prose, which just doubles output
    # tokens for no new information.
    lines = []
    for key, value in result.items():
        if key in ('filename', 'file_type'):
            continue
        heading = key.replace('_', ' ').title()
        if isinstance(value, list):
            lines.append(f'## {heading}\n')
            lines.extend(f'- {item}' for item in value)
            lines.append('')
        elif isinstance(value, dict):
            lines.append(f"## {value.get('criterion_name', heading)}\n")
            lines.extend(f'- {item}' for item in value.get('matches', []))
            lines.append('')
        else:
            lines.append(f'## {heading}\n\n{value}\n')
    return '\n'.join(lines)


def write_output(result: dict, model: str, usage, reasoning: str) -> Path | None:
    # Whether to write a file is decided by the schema's own shape, not a CLI
    # flag: if the model's response includes file_type/filename, write it; if
    # the schema doesn't define those fields, there's nothing to write and
    # that's expected, not an error.
    file_type = result.get('file_type')
    filename = result.get('filename')
    writer = WRITERS.get(file_type)

    if not (filename and writer):
        return None

    content = result.get('content')
    text = writer(result, content) if content is not None else render_fields(result)
    text += '\n\n' + usage_footer(file_type, model, usage, reasoning)

    path = timestamped_path(filename, f'.{file_type}')
    path.write_text(text, encoding='utf-8')
    return path


def main(model: str, prompt: str, reasoning: str, schema_file: Path):
    schema = json.loads(schema_file.read_text(encoding='utf-8'))
    schema_name = schema_file.name.split('.')[0]

    client = OpenAI()
    start = time()
    kwargs = dict(
        model=model,
        input=prompt,
        text={
            'format': {
                'type': 'json_schema',
                'name': schema_name,
                'schema': schema,
                'strict': True,
            }
        },
    )
    if model not in NON_REASONING_MODELS:
        kwargs['reasoning'] = {'effort': reasoning}  # Options include: "none", "minimal", "low", "medium", "high", "xhigh", "max"
    response = client.responses.create(**kwargs)

    result = json.loads(response.output_text)
    print(json.dumps(result, indent=2))

    path = write_output(result, model, response.usage, reasoning)
    if path:
        print(f'Wrote {path}', file=sys.stderr)

    print(f'{round(time() - start, 2)} seconds elapsed', file=sys.stderr)
    print_usage([(model, response.usage)])

    return result


# Launch this sucker
if __name__ == "__main__":
    parser = argparse.ArgumentParser('Structured Output App')
    parser.add_argument('prompt_file', type=Path)
    parser.add_argument('--schema', type=Path, required=True, help='Path to a JSON Schema file describing the desired output shape')
    parser.add_argument('--input-file', type=Path, default=None, help='Optional extra text file appended after the prompt (e.g. a transcript to analyze)')
    parser.add_argument('--model', default='gpt-5.6-luna')
    parser.add_argument('--reasoning', default='low')
    args = parser.parse_args()

    prompt_text = args.prompt_file.read_text(encoding='utf-8')
    if args.input_file:
        prompt_text += '\n\n' + args.input_file.read_text(encoding='utf-8')

    main(args.model, prompt_text, args.reasoning, args.schema)
