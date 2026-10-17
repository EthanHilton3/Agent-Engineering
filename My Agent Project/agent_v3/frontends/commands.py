"""`python -m agent_v3 sessions ...` and `python -m agent_v3 export ...` (sessions spec §6.1), plus the listing
format the CLI's `/sessions` shares (§4.5). No Session is ever opened here: these only read or delete saved files."""
from __future__ import annotations

import argparse
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from ..sessions import SessionInfo, SessionStore, SessionStoreError
from .transcript import export_transcript

COMMANDS = ("sessions", "export")
_ID_SHOWN = 12                                  # "s_" + 10 hex: unique in practice, and any prefix resolves


def reconfigure_utf8() -> None:
    """Piped output on Windows defaults to a legacy code page; titles and transcripts contain Unicode."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8", errors="replace")


def _when(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return (iso or "")[:16]


def format_sessions(rows: list[SessionInfo], *, current: str | None = None, ascii_only: bool = False) -> list[str]:
    """The §4.5 listing, one string per line, header first. `current` is marked with `*`."""
    lines = ["  #  id            updated           turns    cost  title"]
    for n, info in enumerate(rows, 1):
        title = info.title or "(no title)"
        if ascii_only:
            title = title.replace("…", "...")
        flag = ""
        if info.session_id != current:           # the open session always looks "in use" to its own process
            flag = {"interrupted": "  (interrupted)", "in_use": "  (in use)"}.get(info.status, "")
        lines.append(f"{'*' if info.session_id == current else ' '}{n:>2}  {info.session_id[:_ID_SHOWN]:<{_ID_SHOWN}}  "
                     f"{_when(info.updated):<16}  {info.turns:>5}  {'$%.3f' % info.cost_usd:>6}  {title}{flag}")
    return lines


# -- subcommands -------------------------------------------------------------------------------


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _store(args: argparse.Namespace, parser: argparse.ArgumentParser) -> SessionStore:
    workspace = (args.workspace or Path.cwd()).expanduser()
    if not workspace.is_dir():
        parser.error(f"workspace is not a folder: {workspace}")
    return SessionStore.for_workspace(workspace)


def _sessions(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    store = _store(args, parser)
    words = args.words
    if words and words[0] == "delete":
        if len(words) < 2:
            parser.error("sessions delete needs at least one REF")
        try:
            ids = [store.resolve(ref) for ref in words[1:]]     # all refs first, so deleting one cannot change another
        except SessionStoreError as e:
            return _fail(str(e))
        status = 0
        for sid in dict.fromkeys(ids):
            try:
                store.delete(sid)
                print(f"Deleted {sid}")
            except SessionStoreError as e:
                status = _fail(str(e))
        return status
    if words:
        parser.error(f"unknown sessions action {words[0]!r} (use `sessions` or `sessions delete REF ...`)")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")
    rows = store.list(limit=args.limit)
    if not rows:
        print(f"No saved sessions in {store.root}.")
        return 0
    print("\n".join(format_sessions(rows, ascii_only=not sys.stdout.isatty())))
    return 0


def _export(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    store = _store(args, parser)
    try:
        sid = store.resolve(args.ref)
    except SessionStoreError as e:
        return _fail(str(e))
    events = store.events_path(sid)
    if not events.is_file():
        return _fail(f"Session {sid} has no saved events to export.")
    if args.output is not None:
        print(export_transcript(events, args.output))
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        text = export_transcript(events, Path(tmp) / "transcript.md").read_text(encoding="utf-8")
    sys.stdout.write(text)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("agent_v3", description="Manage saved sessions.")
    sub = p.add_subparsers(dest="command", required=True)
    s = sub.add_parser("sessions", help="List saved sessions, or `sessions delete REF [REF ...]`.")
    s.add_argument("words", nargs="*", metavar="delete REF", help="Leave empty to list; `delete REF ...` removes sessions.")
    s.add_argument("--workspace", type=Path, default=None, help="Workspace whose sessions to use (default: current folder).")
    s.add_argument("--limit", type=int, default=None, metavar="N", help="Show only the N most recent sessions.")
    e = sub.add_parser("export", help="Write a session's transcript as Markdown (to stdout unless -o is given).")
    e.add_argument("ref", help="Session id, unique prefix, or 'latest'.")
    e.add_argument("-o", "--output", type=Path, default=None, metavar="PATH", help="Write to this file instead of stdout.")
    e.add_argument("--workspace", type=Path, default=None, help="Workspace whose sessions to use (default: current folder).")
    return p


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    reconfigure_utf8()
    return (_sessions if args.command == "sessions" else _export)(args, parser)
