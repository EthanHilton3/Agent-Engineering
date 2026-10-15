from __future__ import annotations

import difflib
import fnmatch
import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

from ..approvals import ApprovalRequest
from ..workspace import atomic_write_bytes, sha12
from .registry import ErrorCode, ToolContext, ToolResult, ToolSpec, ask_approval

MAX_DIR_ENTRIES = 200
MAX_READ_BYTES = 10 * 1024 * 1024
MAX_SEARCH_FILE_BYTES = 2 * 1024 * 1024
MAX_LINE_CHARS = 2000
MAX_SEARCH_LINE_CHARS = 200
BOM = b"\xef\xbb\xbf"


# ---------------------------------------------------------------------------------------------
# Shared helpers (also used by edit.py)
# ---------------------------------------------------------------------------------------------

def format_numbered(lines: list[str], start: int) -> list[str]:
    """Right-aligned line numbers of minimal width: ` 41| text`."""
    width = len(str(start + len(lines) - 1))
    return [f"{start + i:>{width}}| {line}" for i, line in enumerate(lines)]


def split_lines(text: str) -> list[str]:
    """Split on \\n (tolerating \\r\\n); a trailing newline does not create an extra empty line."""
    if text == "":
        return []
    lines = [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]
    if text.endswith("\n"):
        lines.pop()
    return lines


def diff_stats(old: list[str], new: list[str]) -> tuple[int, int, int, int]:
    """(added, removed, first_changed_line, last_changed_line) — line numbers refer to `new`."""
    added = removed = 0
    first = last = 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        added += j2 - j1
        removed += i2 - i1
        lo, hi = j1 + 1, max(j2, j1 + 1)
        first = lo if first == 0 else min(first, lo)
        last = max(last, hi)
    return added, removed, first, last


def restore_endings(original: str, text: str) -> str:
    """Give \\n-normalized `text` the line endings of `original` (as decoded, \\r\\n intact).

    Lines kept from `original` keep their own ending; new or changed lines get the majority ending,
    so a mixed-ending file is not rewritten wholesale (ties go to \\r\\n)."""
    old = original.split("\n")
    crlf = sum(line.endswith("\r") for line in old[:-1])
    if crlf == 0:
        return text
    if crlf == len(old) - 1:
        return text.replace("\n", "\r\n")
    majority = "\r\n" if 2 * crlf >= len(old) - 1 else "\n"
    old_bodies = [line.removesuffix("\r") for line in old[:-1]]
    new = text.split("\n")
    out = []
    for tag, i1, _, j1, j2 in difflib.SequenceMatcher(None, old_bodies, new[:-1], autojunk=False).get_opcodes():
        for k in range(j2 - j1):
            ending = ("\r\n" if old[i1 + k].endswith("\r") else "\n") if tag == "equal" else majority
            out.append(new[j1 + k] + ending)
    return "".join(out) + new[-1]


def unified_diff(old: list[str], new: list[str], name_old: str, name_new: str) -> str:
    return "\n".join(difflib.unified_diff(old, new, name_old, name_new, lineterm=""))


def human_size(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / 1024 / 1024:.1f} MB"


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _outside_meta(ctx: ToolContext, path: Path) -> dict:
    return {} if ctx.workspace.is_inside(path) else {"outside_workspace": True}


def _not_found(ctx: ToolContext, raw_path: str, path: Path, what: str = "Path") -> ToolResult | None:
    if not path.exists():
        return ToolResult.failure(ErrorCode.NOT_FOUND,
                                  f"{what} '{raw_path}' does not exist. Use list_dir or glob_files to find it.",
                                  summary="not found", path=ctx.workspace.display(path))
    return None


def iter_files(root: Path, ignores: frozenset[str]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in ignores)
        for name in sorted(filenames):
            yield Path(dirpath) / name


def looks_binary(raw: bytes) -> bool:
    return b"\0" in raw[:8192]


# ---------------------------------------------------------------------------------------------
# list_dir
# ---------------------------------------------------------------------------------------------

class ListDirArgs(BaseModel):
    path: str = Field(description="Directory, relative to the workspace or absolute.")
    offset: int | None = Field(default=None, ge=0, description="Zero-based entry offset for paging. Default 0.")


def list_dir(args: ListDirArgs, ctx: ToolContext) -> ToolResult:
    path = ctx.workspace.resolve(args.path)
    meta = {"path": ctx.workspace.display(path), **_outside_meta(ctx, path)}
    if (err := _not_found(ctx, args.path, path)):
        return err
    if path.is_file():
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS,
                                  f"'{args.path}' is a file, not a directory. Use read_file.", **meta)
    try:
        entries = sorted(os.scandir(path), key=lambda e: (not e.is_dir(), e.name.lower()))
    except OSError as e:
        return ToolResult.failure(ErrorCode.INTERNAL, f"Cannot list '{args.path}': {e}", **meta)
    rows = []
    for e in entries:
        if e.is_dir():
            rows.append(e.name + "/")
        else:
            try:
                rows.append(f"{e.name}  {human_size(e.stat().st_size)}")
            except OSError:
                rows.append(e.name)
    if not rows:
        return ToolResult.success("(empty directory)", "0 entries", entries=0, **meta)
    offset = args.offset or 0
    total = len(rows)
    if offset >= total:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS,
                                  f"offset {offset} is past the end of '{args.path}', which has {total} entries.", **meta)
    page = rows[offset:offset + MAX_DIR_ENTRIES]
    text = "\n".join(page)
    nxt = offset + len(page)
    if nxt < total:
        text += f"\n[Showing entries {offset + 1}-{nxt} of {total}. To list more, call list_dir with offset={nxt}.]"
    return ToolResult.success(text, f"{total} entries" if total != 1 else "1 entry", entries=total, **meta)


# ---------------------------------------------------------------------------------------------
# glob_files
# ---------------------------------------------------------------------------------------------

class GlobFilesArgs(BaseModel):
    pattern: str = Field(description="Glob pattern, e.g. '**/*.py' or 'src/**/test_*.py'.")
    path: str | None = Field(default=None, description="Directory to search in. Default: the workspace root.")
    max_results: int | None = Field(default=None, ge=1, le=1000, description="Maximum files to return. Default 200, max 1000.")


def glob_to_regex(pattern: str) -> re.Pattern:
    pat = pattern.replace("\\", "/")
    while pat.startswith("./"):
        pat = pat[2:]
    out, i, n = [], 0, len(pat)
    while i < n:
        c = pat[i]
        if c == "*":
            if pat[i:i + 2] == "**":
                j = i + 2
                if j < n and pat[j] == "/":
                    out.append("(?:.*/)?")
                    i = j + 1
                else:
                    out.append(".*")
                    i = j
            else:
                out.append("[^/]*")
                i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        elif c == "[" and (j := pat.find("]", i + 2)) != -1:
            body = pat[i + 1:j]
            if body.startswith("!"):
                body = "^" + body[1:]
            out.append("[" + body.replace("\\", "\\\\") + "]")
            i = j + 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("".join(out) + r"\Z", re.IGNORECASE if os.name == "nt" else 0)


def glob_files(args: GlobFilesArgs, ctx: ToolContext) -> ToolResult:
    root = ctx.workspace.resolve(args.path) if args.path else ctx.workspace.root
    meta = {"path": ctx.workspace.display(root), **_outside_meta(ctx, root)}
    if (err := _not_found(ctx, args.path or ".", root)):
        return err
    if not root.is_dir():
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS, f"'{args.path}' is not a directory.", **meta)
    rx = glob_to_regex(args.pattern)
    ignores = ctx.workspace.active_ignores(root)
    found = sorted(rel for f in iter_files(root, ignores)
                   if rx.match(rel := f.relative_to(root).as_posix()))
    limit = args.max_results or 200
    shown, chars = [], 0
    for rel in found[:limit]:
        chars += len(rel) + 1
        if shown and chars > ctx.config.tool_output_max_chars:
            break
        shown.append(rel)
    total = len(found)
    if not found:
        return ToolResult.success("[0 files]", "0 files", matches=0, **meta)
    footer = f"[{total} files]" if len(shown) == total else f"[showing {len(shown)} of {total} files]"
    return ToolResult.success("\n".join(shown) + "\n" + footer, plural(total, "file"),
                              matches=total, truncated=len(shown) < total, **meta)


# ---------------------------------------------------------------------------------------------
# read_file
# ---------------------------------------------------------------------------------------------

class ReadFileArgs(BaseModel):
    path: str = Field(description="File to read, relative to the workspace or absolute.")
    start_line: int | None = Field(default=None, ge=1, description="First line to read (1-based). Default 1.")
    end_line: int | None = Field(default=None, ge=1, description="Last line to read, inclusive. Default: start_line + 249.")


def read_file(args: ReadFileArgs, ctx: ToolContext) -> ToolResult:
    cfg = ctx.config
    path = ctx.workspace.resolve(args.path)
    shown_name = ctx.workspace.display(path)
    meta = {"path": shown_name, **_outside_meta(ctx, path)}
    if (err := _not_found(ctx, args.path, path)):
        return err
    if path.is_dir():
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS,
                                  f"'{args.path}' is a directory. Use list_dir.", **meta)
    try:
        if path.stat().st_size > MAX_READ_BYTES:
            return ToolResult.failure(ErrorCode.TOO_LARGE,
                                      f"'{args.path}' is larger than 10 MB. Use search_text to locate content.", **meta)
        raw = path.read_bytes()
    except OSError as e:
        return ToolResult.failure(ErrorCode.INTERNAL, f"Cannot read '{args.path}': {e}", **meta)
    if looks_binary(raw):
        return ToolResult.failure(ErrorCode.BINARY, f"'{args.path}' is a binary file, not text.", **meta)
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return ToolResult.failure(ErrorCode.BINARY, f"'{args.path}' is not UTF-8 text.", **meta)

    sha = sha12(raw)
    ctx.files.set(path, sha)          # whole-file sha, even for a partial range
    lines = split_lines(text)
    total = len(lines)
    meta["sha"] = sha
    if total == 0:
        return ToolResult.success(f"[{shown_name} · empty file · sha {sha}]", "empty file", **meta)

    start = args.start_line or 1
    if start > total:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS,
                                  f"start_line {start} is past the end of the file ({total} lines).", **meta)
    if args.end_line is not None and args.end_line < start:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS,
                                  f"end_line {args.end_line} is before start_line {start}.", **meta)
    end = min(args.end_line or total, start + cfg.read_max_lines - 1, total)

    kept, chars = [], 0
    for n in range(start, end + 1):
        line = lines[n - 1]
        if len(line) > MAX_LINE_CHARS:
            line = line[:MAX_LINE_CHARS] + f"…[line truncated, {len(lines[n - 1])} chars]"
        cost = len(line) + len(str(end)) + 3
        if kept and chars + cost > cfg.read_max_chars:
            break
        kept.append(line)
        chars += cost
    end = start + len(kept) - 1
    meta["line_range"] = [start, end]
    summary = f"lines {start}–{end}"

    if cfg.dedupe_reads:
        key = (os.path.normcase(str(path)), start, end, sha)
        with ctx.seen_lock:
            seen = key in ctx.seen_reads
            ctx.seen_reads[key] = True
        if seen:
            return ToolResult.success(
                f"Unchanged since your earlier read of these lines (same sha {sha}); "
                "content omitted — refer to that result.", summary + " (unchanged)", deduped=True, **meta)

    footer = f"[{shown_name} · lines {start}–{end} of {total} · sha {sha}"
    if end < total:
        footer += f" · next: start_line={end + 1}"
    footer += "]"
    out = "\n".join(format_numbered(kept, start)) + "\n" + footer
    return ToolResult.success(out, summary, **meta)


# ---------------------------------------------------------------------------------------------
# search_text
# ---------------------------------------------------------------------------------------------

class SearchTextArgs(BaseModel):
    pattern: str = Field(description="Text to search for (a regular expression if regex is true).")
    path: str | None = Field(default=None, description="Directory or single file to search. Default: the workspace root.")
    glob: str | None = Field(default=None, description="Only search files whose name matches this glob, e.g. '*.py'.")
    regex: bool | None = Field(default=None, description="Treat pattern as a regular expression. Default false.")
    ignore_case: bool | None = Field(default=None, description="Case-insensitive match. Default false.")
    context_lines: int | None = Field(default=None, ge=0, le=5, description="Lines of context around each match. Default 0, max 5.")
    max_results: int | None = Field(default=None, ge=1, le=300, description="Maximum matching lines to show. Default 60, max 300.")


def search_text(args: SearchTextArgs, ctx: ToolContext) -> ToolResult:
    root = ctx.workspace.resolve(args.path) if args.path else ctx.workspace.root
    meta = {"path": ctx.workspace.display(root), **_outside_meta(ctx, root)}
    if (err := _not_found(ctx, args.path or ".", root)):
        return err
    try:
        rx = re.compile(args.pattern if args.regex else re.escape(args.pattern),
                        re.IGNORECASE if args.ignore_case else 0)
    except re.error as e:
        return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS, f"pattern: invalid regular expression: {e}", **meta)

    ctx_n = args.context_lines or 0
    limit = args.max_results or 60
    char_budget = ctx.config.tool_output_max_chars
    if root.is_file():
        files, base = [root], root.parent
    else:
        files, base = iter_files(root, ctx.workspace.active_ignores(root)), root

    blocks: list[tuple[str, list[tuple[int, str, bool] | None]]] = []
    total_matches = total_files = shown = chars = 0
    for f in files:
        rel = f.relative_to(base).as_posix()
        if args.glob and not (fnmatch.fnmatch(f.name, args.glob) or fnmatch.fnmatch(rel, args.glob)):
            continue
        try:
            if f.stat().st_size > MAX_SEARCH_FILE_BYTES:
                continue
            raw = f.read_bytes()
        except OSError:
            continue
        if looks_binary(raw):
            continue
        lines = split_lines(raw.decode("utf-8-sig", errors="replace"))
        hits = [i for i, line in enumerate(lines) if rx.search(line)]
        if not hits:
            continue
        total_files += 1
        total_matches += len(hits)
        take = []
        for m in hits[:max(0, limit - shown)]:
            # Always show at least one match; after that stop once the output budget is spent.
            cost = sum(min(len(lines[j]), MAX_SEARCH_LINE_CHARS) + 8
                       for j in range(max(0, m - ctx_n), min(len(lines), m + ctx_n + 1)))
            if (shown + len(take)) > 0 and chars + cost > char_budget:
                break
            chars += cost
            take.append(m)
        if not take:
            continue
        rows: list[tuple[int, str, bool] | None] = []
        hitset, last = set(take), -1
        for i in sorted({j for m in take for j in range(max(0, m - ctx_n), min(len(lines), m + ctx_n + 1))}):
            if last != -1 and i != last + 1:
                rows.append(None)
            text = lines[i] if len(lines[i]) <= MAX_SEARCH_LINE_CHARS else lines[i][:MAX_SEARCH_LINE_CHARS] + "…"
            rows.append((i + 1, text, i in hitset))
            last = i
        shown += len(take)
        blocks.append((rel, rows))

    if total_matches == 0:
        return ToolResult.success("[0 matches in 0 files]", "0 matches", matches=0, files=0, **meta)
    width = len(str(max(r[0] for _, rows in blocks for r in rows if r)))
    out = []
    for rel, rows in blocks:
        out.append(rel)
        for r in rows:
            out.append("  --" if r is None else f"  {r[0]:>{width}}{':' if r[2] else '-'} {r[1]}")
    where = f"in {plural(total_files, 'file')}"
    if shown < total_matches:
        out.append(f"[showing {shown} of {total_matches} matches {where} — narrow with path or glob]")
    else:
        out.append(f"[{total_matches} match{'' if total_matches == 1 else 'es'} {where}]")
    return ToolResult.success("\n".join(out), f"{total_matches} matches in {plural(total_files, 'file')}",
                              matches=total_matches, files=total_files, truncated=shown < total_matches, **meta)


# ---------------------------------------------------------------------------------------------
# write_file
# ---------------------------------------------------------------------------------------------

class WriteFileArgs(BaseModel):
    path: str = Field(description="File to create or replace, relative to the workspace or absolute.")
    content: str = Field(description="Complete new file content.")
    overwrite: bool | None = Field(default=None, description="Allow replacing an existing file (you must have read it). Default false.")


def write_file(args: WriteFileArgs, ctx: ToolContext) -> ToolResult:
    path = ctx.workspace.resolve(args.path)
    rel = ctx.workspace.display(path)
    outside = not ctx.workspace.is_inside(path)
    meta = {"path": rel, **_outside_meta(ctx, path)}
    existed = path.exists()
    old_raw = b""
    if existed:
        if path.is_dir():
            return ToolResult.failure(ErrorCode.INVALID_ARGUMENTS, f"'{args.path}' is a directory.", **meta)
        if not args.overwrite:
            return ToolResult.failure(ErrorCode.CONFLICT,
                                      "File exists. Use edit_files, or set overwrite=true after reading it.", **meta)
        old_raw = path.read_bytes()
        known = ctx.files.get(path)
        if known is None or known != sha12(old_raw):
            return ToolResult.failure(ErrorCode.CONFLICT, "Read the current file before overwriting it.", **meta)

    bom = old_raw.startswith(BOM)
    old_text = old_raw.decode("utf-8-sig", errors="replace")
    content = args.content.replace("\r\n", "\n")
    new_lines = split_lines(content)
    if existed:
        old_lines = split_lines(old_text)
        diff = unified_diff(old_lines, new_lines, f"a/{rel}", f"b/{rel}")
        added, removed, _, _ = diff_stats(old_lines, new_lines)
        title, extra = "Overwrite file", {}
    else:
        added, removed = len(new_lines), 0
        diff = "\n".join([f"--- /dev/null", f"+++ b/{rel}", *[f"+{l}" for l in new_lines[:40]]])
        if len(new_lines) > 40:
            diff += f"\n… {len(new_lines) - 40} more lines"
        title, extra = "Create file", {"full_content": args.content}

    rejected = ask_approval(ctx, ApprovalRequest(
        kind="edit", title=title, paths=[str(path)], diff=diff, outside_workspace=outside, metadata=extra))
    if rejected:
        return rejected

    # Re-check after the (possibly long) approval wait.
    if path.exists() != existed or (existed and path.read_bytes() != old_raw):
        return ToolResult.failure(ErrorCode.CONFLICT, f"{rel} changed while waiting for approval. Re-read it and retry.", **meta)
    data = restore_endings(old_text, content).encode("utf-8")
    if bom:
        data = BOM + data
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(path, data)
    except OSError as e:
        return ToolResult.failure(ErrorCode.INTERNAL, f"Could not write {rel}: {e}", **meta)
    sha = sha12(data)
    ctx.files.set(path, sha)
    meta.update(sha=sha, files_changed=[{"path": rel, "added": added, "removed": removed}])
    if existed:
        return ToolResult.success(f"Overwrote {rel} (+{added} −{removed}, sha {sha})", f"+{added} −{removed}", **meta)
    return ToolResult.success(f"Created {rel} ({plural(len(new_lines), 'line')}, sha {sha})",
                              f"created · {plural(len(new_lines), 'line')}", **meta)


READ_TOOLS = [
    ToolSpec("list_dir", ListDirArgs, list_dir, True,
             "List a directory: folders first (name ends with /), then files with sizes. 200 entries per page; use offset for more."),
    ToolSpec("glob_files", GlobFilesArgs, glob_files, True,
             "Find files by glob pattern, e.g. `**/*.py` or `src/**/test_*.py`. Returns paths relative to the search root, sorted."),
    ToolSpec("read_file", ReadFileArgs, read_file, True,
             "Read a line range of a UTF-8 text file. Prefer narrow ranges found via search_text. Output lines are prefixed with line numbers."),
    ToolSpec("search_text", SearchTextArgs, search_text, True,
             "Search file contents. Fixed-string by default; set regex=true for regular expressions. Use this to locate code before reading it."),
]
WRITE_TOOLS = [
    ToolSpec("write_file", WriteFileArgs, write_file, False,
             "Create a new file, or replace an entire existing file. Use edit_files for partial changes. Overwriting requires that you have read the current version."),
]
