from __future__ import annotations

import difflib
import os
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field

from ..approvals import ApprovalRequest
from ..workspace import atomic_write_bytes, sha12
from .files import (BOM, MAX_READ_BYTES, diff_stats, format_numbered, looks_binary, plural,
                    restore_endings, split_lines, unified_diff)
from .registry import ErrorCode, ToolContext, ToolResult, ToolSpec, ask_approval

CLOSEST_MIN_RATIO = 0.6
CLOSEST_MAX_LINES = 30
CLOSEST_MAX_FILE_LINES = 20_000


class Edit(BaseModel):
    path: str = Field(description="File to edit.")
    old_text: str = Field(description="Exact existing text to replace, copied from read_file output without "
                                      "line-number prefixes. Include enough context to be unique.")
    new_text: str = Field(description="Replacement text.")
    replace_all: bool | None = Field(default=None, description="Replace every occurrence instead of requiring "
                                                               "exactly one. Default false.")


class EditFilesArgs(BaseModel):
    edits: list[Edit] = Field(min_length=1, description="Edits, applied in order. Several edits may target the same file.")


class _EditFail(Exception):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class _FileBuf:
    path: Path
    rel: str
    sha: str
    decoded: str           # as decoded, line endings intact
    bom: bool
    had_newline: bool
    original: str          # \n-normalized
    text: str              # \n-normalized, edits applied so far


def _load(ctx: ToolContext, path: Path, rel: str) -> _FileBuf:
    if not path.exists():
        raise _EditFail(ErrorCode.NOT_FOUND, f"{rel} does not exist. Use write_file to create a new file.")
    if path.is_dir():
        raise _EditFail(ErrorCode.INVALID_ARGUMENTS, f"{rel} is a directory.")
    if path.stat().st_size > MAX_READ_BYTES:
        raise _EditFail(ErrorCode.TOO_LARGE, f"{rel} is larger than 10 MB.")
    raw = path.read_bytes()
    if looks_binary(raw):
        raise _EditFail(ErrorCode.BINARY, f"{rel} is a binary file, not text.")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise _EditFail(ErrorCode.BINARY, f"{rel} is not UTF-8 text.")
    sha = sha12(raw)
    known = ctx.files.get(path)
    if known is not None and known != sha:
        raise _EditFail(ErrorCode.CONFLICT, f"{rel} changed since you last read it (sha {known}→{sha}). "
                                            "Re-read the region you are editing.")
    text = decoded.replace("\r\n", "\n")
    return _FileBuf(path, rel, sha, decoded, raw.startswith(BOM), text.endswith("\n"), text, text)


# ---------------------------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------------------------

def _find_all(text: str, sub: str) -> list[int]:
    idxs, i = [], text.find(sub)
    while i != -1:
        idxs.append(i)
        i = text.find(sub, i + len(sub))
    return idxs


def _block_lines(s: str) -> list[str]:
    """Whole-line view of a snippet: a single trailing newline does not add an empty line."""
    if s == "":
        return []
    return (s[:-1] if s.endswith("\n") else s).split("\n")


def _leading(line: str) -> str:
    return line[:len(line) - len(line.lstrip())]


def _ambiguous(line_numbers: list[int]) -> _EditFail:
    shown = ", ".join(map(str, line_numbers[:5])) + (", …" if len(line_numbers) > 5 else "")
    return _EditFail(ErrorCode.AMBIGUOUS,
                     f"old_text matches {len(line_numbers)} places (lines {shown}). Add surrounding context "
                     "to make it unique, or set replace_all=true.")


def _spaces_to_tabs(width: int):
    def convert(line: str) -> str | None:
        ws = _leading(line)
        if "\t" in ws:
            return None
        tabs, spaces = divmod(len(ws), width)
        return "\t" * tabs + " " * spaces + line[len(ws):]
    return convert


def _tabs_to_spaces(width: int):
    def convert(line: str) -> str | None:
        ws = _leading(line)
        return ws.replace("\t", " " * width) + line[len(ws):]
    return convert


def _reindent(window: list[str], old_lines: list[str], new_lines: list[str]) -> list[str] | None:
    """If `window` is `old_lines` under ONE uniform leading-whitespace change, return `new_lines`
    under the same change; otherwise None. The change is either a constant prefix swap
    (e.g. 4 spaces → 8 spaces on every line) or a tab↔space unit conversion for nested blocks."""
    nonblank = [j for j, line in enumerate(old_lines) if line.strip()]
    if not nonblank:
        return None
    j0 = nonblank[0]
    old_prefix, file_prefix = _leading(old_lines[j0]), _leading(window[j0])

    def swap_prefix(line: str) -> str | None:
        return file_prefix + line[len(old_prefix):] if line.startswith(old_prefix) else None

    transforms = [swap_prefix, *(_spaces_to_tabs(w) for w in (4, 2, 8)), *(_tabs_to_spaces(w) for w in (4, 2, 8))]
    for convert in transforms:
        if not all((c := convert(old_lines[j])) is not None and c.rstrip() == window[j].rstrip() for j in nonblank):
            continue
        out = [line if not line.strip() else convert(line) for line in new_lines]
        if None not in out:
            return out
    return None


def _lenient(text: str, old: str, new: str) -> tuple[str, str] | None:
    """Whole-line fallbacks: ignore trailing whitespace, then ignore a uniform indent change."""
    lines = text.split("\n")
    old_lines, new_lines = _block_lines(old), _block_lines(new)
    n = len(old_lines)
    if n == 0 or n > len(lines):
        return None

    def splice(starts: list[int], replacement: list[str], note: str) -> tuple[str, str]:
        if len(starts) > 1:
            raise _ambiguous([s + 1 for s in starts])
        i = starts[0]
        return "\n".join(lines[:i] + replacement + lines[i + n:]), note

    rstripped = [line.rstrip() for line in lines]
    key = [line.rstrip() for line in old_lines]
    starts = [i for i in range(len(lines) - n + 1) if rstripped[i] == key[0] and rstripped[i:i + n] == key]
    if starts:
        return splice(starts, new_lines, "matched after ignoring trailing whitespace")

    stripped = [line.strip() for line in lines]
    key = [line.strip() for line in old_lines]
    cands = []
    for i in range(len(lines) - n + 1):
        if stripped[i] == key[0] and stripped[i:i + n] == key:
            mapped = _reindent(lines[i:i + n], old_lines, new_lines)
            if mapped is not None:
                cands.append((i, mapped))
    if cands:
        if len(cands) > 1:
            raise _ambiguous([i + 1 for i, _ in cands])
        return splice([cands[0][0]], cands[0][1], "matched after ignoring indentation differences")
    return None


def _closest(lines: list[str], old: str) -> str:
    old_lines = _block_lines(old)
    n = min(len(old_lines), len(lines))
    if n == 0 or len(lines) > CLOSEST_MAX_FILE_LINES:
        return ""
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2("\n".join(old_lines))
    best, best_i = CLOSEST_MIN_RATIO - 1e-9, -1
    for i in range(len(lines) - n + 1):
        sm.set_seq1("\n".join(lines[i:i + n]))
        if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
            continue
        if (r := sm.ratio()) > best:
            best, best_i = r, i
    if best_i < 0:
        return ""
    shown = lines[best_i:best_i + n][:CLOSEST_MAX_LINES]
    header = f" Closest match at lines {best_i + 1}–{best_i + len(shown)} (similarity {best:.2f}):"
    return "\n".join([header, *format_numbered(shown, best_i + 1)])


def _apply_edit(text: str, edit: Edit, lenient: bool) -> tuple[str, str | None]:
    old, new = edit.old_text.replace("\r\n", "\n"), edit.new_text.replace("\r\n", "\n")
    if old == "":
        raise _EditFail(ErrorCode.INVALID_ARGUMENTS, "old_text is empty. To create a file use write_file.")
    idxs = _find_all(text, old)
    if len(idxs) == 1:
        return text[:idxs[0]] + new + text[idxs[0] + len(old):], None
    if len(idxs) > 1:
        if edit.replace_all:
            return text.replace(old, new), None
        raise _ambiguous([text.count("\n", 0, i) + 1 for i in idxs])
    if lenient and (res := _lenient(text, old, new)):
        return res
    snippet = _closest(text.split("\n"), old)
    raise _EditFail(ErrorCode.NO_MATCH, "old_text not found." + (
        snippet + "\nFix old_text using this region." if snippet
        else " No similar text found; re-read the file region and copy the text exactly."))


# ---------------------------------------------------------------------------------------------
# edit_files
# ---------------------------------------------------------------------------------------------

def _encode(buf: _FileBuf, text: str) -> bytes:
    if buf.had_newline and not text.endswith("\n"):
        text += "\n"
    elif not buf.had_newline and text.endswith("\n"):
        text = text[:-1]
    return (BOM if buf.bom else b"") + restore_endings(buf.decoded, text).encode("utf-8")


def edit_files(args: EditFilesArgs, ctx: ToolContext) -> ToolResult:
    lenient = ctx.config.lenient_edit_match
    bufs: dict[str, _FileBuf] = {}
    failures: list[tuple[int, str, _EditFail]] = []     # (edit number, path, failure)
    broken: set[str] = set()
    notes: list[str] = []

    for n, edit in enumerate(args.edits, start=1):
        path = ctx.workspace.resolve(edit.path)
        key = os.path.normcase(str(path))
        rel = ctx.workspace.display(path)
        if key in broken:
            continue                        # the file itself is unusable; already reported once
        try:
            if key not in bufs:
                bufs[key] = _load(ctx, path, rel)
            buf = bufs[key]
            buf.text, note = _apply_edit(buf.text, edit, lenient)
            if note:
                notes.append(f"edit {n} {note}")
        except _EditFail as e:
            failures.append((n, rel, e))
            if key not in bufs:
                broken.add(key)

    if failures:
        lines = [f"{plural(len(failures), 'edit')} failed; no files were changed."]
        lines += [f"edit {n} ({rel}): {e.message}" for n, rel, e in failures]
        return ToolResult.failure(failures[0][2].code, "\n".join(lines),
                                  summary=f"{plural(len(failures), 'edit')} failed")

    changed = [b for b in bufs.values() if b.text != b.original]
    diff_parts, stats = [], {}
    for b in bufs.values():
        old_l, new_l = split_lines(b.original), split_lines(b.text)
        stats[b.rel] = diff_stats(old_l, new_l)
        if b.text != b.original:
            diff_parts.append(unified_diff(old_l, new_l, f"a/{b.rel}", f"b/{b.rel}"))

    outside = any(not ctx.workspace.is_inside(b.path) for b in bufs.values())
    if changed:
        rejected = ask_approval(ctx, ApprovalRequest(
            kind="edit", title=f"Edit {plural(len(changed), 'file')}", paths=[str(b.path) for b in changed],
            diff="\n".join(diff_parts), outside_workspace=outside))
        if rejected:
            return rejected

    # Build every payload first, then verify nothing changed during the approval wait.
    payloads = {b.rel: _encode(b, b.text) for b in changed}
    for b in changed:
        if sha12(b.path.read_bytes()) != b.sha:
            return ToolResult.failure(ErrorCode.CONFLICT,
                                      f"{b.rel} changed while waiting for approval. Re-read it and retry.")
    shas = {}
    for b in changed:
        try:
            atomic_write_bytes(b.path, payloads[b.rel])
        except OSError as e:
            return ToolResult.failure(ErrorCode.INTERNAL, f"Could not write {b.rel}: {e}. "
                                      f"Already written: {', '.join(shas) or 'none'}.")
        shas[b.rel] = sha12(payloads[b.rel])
        ctx.files.set(b.path, shas[b.rel])

    rows, changes = [], []
    for b in bufs.values():
        added, removed, first, last = stats[b.rel]
        sha = shas.get(b.rel, b.sha)
        span = f"  lines {first}–{last}" if first else "  (no change)"
        rows.append(f"  {b.rel}  +{added} −{removed}{span}  sha {sha}")
        changes.append({"path": b.rel, "added": added, "removed": removed})
    out = "\n".join([f"Edited {plural(len(bufs), 'file')}:", *rows, *[f"Note: {n}." for n in notes]])
    added_total, removed_total = sum(c["added"] for c in changes), sum(c["removed"] for c in changes)
    meta = {"paths": [b.rel for b in bufs.values()], "files_changed": changes}
    if len(bufs) == 1:
        b = next(iter(bufs.values()))
        meta.update(path=b.rel, sha=shas.get(b.rel, b.sha),
                    **({"line_range": [stats[b.rel][2], stats[b.rel][3]]} if stats[b.rel][2] else {}))
    return ToolResult.success(out, f"{plural(len(bufs), 'file')} +{added_total} −{removed_total}", **meta)


EDIT_TOOLS = [
    ToolSpec("edit_files", EditFilesArgs, edit_files, False,
             "Apply one or more exact text replacements across one or more existing files in a single call. "
             "Put every edit you have decided on into one call. All edits are validated before anything is "
             "written; if any edit fails, nothing is changed."),
]
