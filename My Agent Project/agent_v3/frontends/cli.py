"""Terminal frontend (plan §10.1), minimal by design, with v2's look.

Threading: `Session` calls `on_event` on worker threads while holding its lock, so `on_event` only does
`queue.put`. This module's main thread owns stdout and stdin: every print, the spinner and every `input()`
(including approval prompts) happen here. The look-and-feel helpers are copied from the homework's `ui.py`
(not imported), so the package stays self-contained.
"""
from __future__ import annotations

import argparse
import os
import queue
import re
import sys
import threading
import time
from collections import Counter, deque
from contextlib import suppress
from itertools import cycle
from pathlib import Path
from typing import Callable

from ..approvals import Decision
from ..config import APPROVAL_MODES, REASONING_EFFORTS, SEARCH_CONTEXT_SIZES, AgentConfig
from ..events import Event
from ..session import Session
from .eventlog import EventLogWriter
from .formatting import completion_line, format_usage, round_summary
from .transcript import TranscriptWriter

# Enable ANSI escape-sequence handling in supported Windows terminals.
if os.name == "nt":
    os.system("")

_TTY = sys.stdout.isatty()
_COLOR = _TTY and not os.environ.get("NO_COLOR")
_RESET = "\033[0m"
_PROMPT_MARK = "›" if _TTY else ">"
_RESULT_MARK = "↳" if _TTY else "->"
_SUCCESS_MARK = "✓" if _TTY else "ok"
_FAILURE_MARK = "✗" if _TTY else "x"
_ELLIPSIS = "…" if _TTY else "..."
_TIMES = "×" if _TTY else "x"
_SEP = " · " if _TTY else " - "
_MINUS = "−" if _TTY else "-"

DOUBLE_INTERRUPT_S = 2.0
DIFF_PREVIEW_LINES = 40
SLASH_COMMANDS = ("/new", "/usage", "/quit")


def _style(text: str, code: str) -> str:
    return f"\033[{code}m{text}{_RESET}" if _COLOR else text


def _dim(text: str) -> str:
    return _style(text, "2")


def _clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1] + _ELLIPSIS


YOU = _style("You", "1;36")
AGENT = _style("Agent", "1;32")


class _Quit(Exception):
    """Leave the program (double Ctrl+C, /quit)."""


class _Spinner:
    """A "Thinking…" spinner on its own thread. Only the main thread starts/stops it, and it is always
    stopped before anything else is printed, so the two never interleave."""

    def __init__(self):
        self._stopped = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, message: str) -> None:
        if not _TTY or self._thread is not None:
            return
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._animate, args=(message, self._stopped), daemon=True)
        self._thread.start()

    @staticmethod
    def _animate(message: str, stopped: threading.Event) -> None:
        for frame in cycle("⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"):
            if stopped.is_set():
                break
            print(f"\r  {_style(frame, '36')} {message}", end="", flush=True)
            time.sleep(0.08)

    def stop(self) -> None:
        if self._thread is None:
            return
        self._stopped.set()
        self._thread.join()
        self._thread = None
        print("\r\033[2K", end="", flush=True)


# -- diff display ------------------------------------------------------------------------------


def diff_files(diff: str) -> list[list]:
    """[[name, added, removed], ...] from a (multi-file) unified diff."""
    files: list[list] = []
    lines = diff.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- ") and i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
            name = lines[i + 1][4:].strip()
            files.append([name[2:] if name.startswith("b/") else name, 0, 0])
            i += 2
            continue
        if files:
            if line.startswith("+"):
                files[-1][1] += 1
            elif line.startswith("-"):
                files[-1][2] += 1
        i += 1
    return files


def _color_diff_line(line: str) -> str:
    if line.startswith(("+++", "---")):
        return _style(line, "1")
    if line.startswith("@@"):
        return _style(line, "36")
    if line.startswith("+"):
        return _style(line, "32")
    if line.startswith("-"):
        return _style(line, "31")
    return _dim(line) if line.startswith("…") else line


def _diff_lines(req: dict) -> list[str]:
    """Every line to show for "d". A new file's diff is truncated by the tool, so use its full content."""
    diff = req.get("diff") or ""
    full = (req.get("metadata") or {}).get("full_content")
    if full is None:
        return diff.splitlines()
    header = []
    for line in diff.splitlines():
        header.append(line)
        if line.startswith("+++ "):
            break
    return [*header, *("+" + l for l in full.splitlines())]


def _file_summary(req: dict) -> list[tuple[str, int, int]]:
    full = (req.get("metadata") or {}).get("full_content")
    files = [(n, a, r) for n, a, r in diff_files(req.get("diff") or "")]
    if full is not None and files:
        files = [(files[0][0], len(full.splitlines()), 0)]
    if not files:
        files = [(p, -1, -1) for p in req.get("paths", [])]
    return files


# -- the frontend ------------------------------------------------------------------------------


class Cli:
    def __init__(self, session: Session, events: "queue.Queue[Event]", *, verbose: bool = False,
                 input_fn: Callable[[str], str] = input, sinks: tuple[Callable, ...] = ()):
        self.session = session
        self.q = events
        self.verbose = verbose
        self.input_fn = input_fn
        self.sinks = list(sinks)
        self._buffer: deque = deque()             # events pulled from the queue ahead of dispatch
        self._spinner = _Spinner()
        self._spin_message = "Thinking…"
        self._turn_active = False
        self._last_interrupt: float | None = None
        self._calls: dict[str, Event] = {}        # call_id -> tool_started
        self._group_count: Counter = Counter()
        self._headed: set[int] = set()
        self._sink_error_shown = False

    # -- main loop -----------------------------------------------------------------------------

    def run(self) -> int:
        try:
            self._pump()
            while True:
                try:
                    text = self.input_fn(f"\n{YOU} {_PROMPT_MARK} ").strip()
                except EOFError:
                    print()
                    break
                if not text:
                    continue
                if re.fullmatch(r"/[A-Za-z]+", text):
                    if not self._command(text.lower()):
                        break
                    continue
                self._run_turn(text)
        except (KeyboardInterrupt, _Quit):
            print()                               # move past the prompt line
        finally:
            self._shutdown()
        return 0

    def _command(self, cmd: str) -> bool:
        """Run a slash command. False means quit."""
        if cmd == "/quit":
            return False
        if cmd == "/new":
            self.session.new_conversation()
            self._pump()
        elif cmd == "/usage":
            print(format_usage(self.session.config.model, self.session.usage_totals()))
        else:
            print(_dim(f"Unknown command {cmd}. Commands: {', '.join(SLASH_COMMANDS)}"))
        return True

    def _run_turn(self, text: str) -> None:
        self._last_interrupt = None
        self._calls.clear()
        self._group_count.clear()
        self._headed.clear()
        self.session.start_turn(text)
        self._turn_active = True
        self._spin("Thinking…")
        try:
            while True:
                try:
                    self._pump(wait_for_turn=True)
                    return
                except KeyboardInterrupt:
                    self._interrupt()
        finally:
            self._turn_active = False
            self._spinner.stop()

    def _interrupt(self) -> None:
        """Ctrl+C during a turn: cancel it and go back to the prompt. A second one within 2 s quits."""
        self._spinner.stop()
        now = time.monotonic()
        if self._last_interrupt is not None and now - self._last_interrupt < DOUBLE_INTERRUPT_S:
            raise _Quit()
        self._last_interrupt = now
        self.session.cancel()                     # then _pump drains until the turn_cancelled event is printed

    def _shutdown(self) -> None:
        self._turn_active = False
        self._spinner.stop()
        with suppress(KeyboardInterrupt):
            self.session.close()                  # cancels a running turn; its event is drained below
            self._pump()
            print()
            print(format_usage(self.session.config.model, self.session.usage_totals()))

    # -- event intake --------------------------------------------------------------------------

    def _fill(self) -> None:
        while True:
            try:
                self._buffer.append(self.q.get_nowait())
            except queue.Empty:
                return

    def _pump(self, wait_for_turn: bool = False) -> None:
        """Dispatch queued events. With `wait_for_turn`, keep going until the turn is over and the queue is dry."""
        while True:
            if self._buffer:
                ev = self._buffer.popleft()
            else:
                try:
                    ev = self.q.get(timeout=0.1) if wait_for_turn else self.q.get_nowait()
                except queue.Empty:
                    # Read `busy` first: the terminal event is queued before the session goes idle.
                    if wait_for_turn and (self.session.busy or not self.q.empty()):
                        continue
                    return
            self._dispatch(ev)

    def _dispatch(self, ev: Event) -> None:
        for sink in self.sinks:
            try:
                sink(ev)
            except Exception as e:                # a full disk must not kill the session
                if not self._sink_error_shown:
                    self._sink_error_shown = True
                    self._say(_style(f"  warning: could not write the transcript or event log: {e}", "33"))
        handler = getattr(self, f"_on_{ev.type}", None)
        if handler is not None:
            handler(ev)

    # -- output --------------------------------------------------------------------------------

    def _spin(self, message: str | None = None) -> None:
        if message:
            self._spin_message = message
        self._spinner.start(self._spin_message)

    def _say(self, *lines: str) -> None:
        """Print lines with the spinner out of the way; resume it afterwards while a turn is running."""
        self._spinner.stop()
        for line in lines:
            print(line)
        sys.stdout.flush()
        if self._turn_active:
            self._spin()

    # -- event handlers ------------------------------------------------------------------------

    def _on_session_started(self, ev) -> None:
        c = ev.config
        self._say(_dim(f"agent_v3{_SEP}{c['model']}{_SEP}reasoning {c['reasoning']}{_SEP}approval {c['approval']}"
                       f"{_SEP}web search {'on' if c['web_search'] else 'off'}"),
                  _dim(f"workspace {c['workspace']}"),
                  _dim("Enter a task. /new = new conversation, /usage = totals, /quit = exit. "
                       "Ctrl+C cancels a running turn."))

    def _on_model_round_started(self, ev) -> None:
        self._spin("Thinking…")

    def _on_model_retry(self, ev) -> None:
        self._say(_dim(f"  model call interrupted, retrying in {ev.delay_s:.0f}s (attempt {ev.attempt}): {ev.reason}"))

    def _on_model_round_completed(self, ev) -> None:
        if self.verbose:
            self._say(_dim(f"  round {ev.round}: {round_summary(ev.to_dict(), _SEP)}"))
        if ev.function_calls:
            self._spin("Running tools…")

    def _on_web_action(self, ev) -> None:
        label = "web_search" if ev.kind == "search" else ev.kind
        self._say(f"  {_RESULT_MARK} {label}  {_dim(_clip(ev.detail, 120))}  {_style(_SUCCESS_MARK, '32')} done")

    def _on_tool_started(self, ev) -> None:
        self._calls[ev.call_id] = ev
        self._group_count[ev.group] += 1

    def _on_tool_completed(self, ev) -> None:
        started = self._calls.pop(ev.call_id, None)
        lines = []
        if ev.group not in self._headed:
            self._headed.add(ev.group)
            self._fill()                          # see the rest of this group's starts, if they are queued
            size = self._group_count[ev.group] + sum(
                e.type == "tool_started" and e.group == ev.group for e in self._buffer)
            if size >= 2:
                lines.append(_dim(f"  parallel {_TIMES}{size}"))
        target = started.target if started else ""
        line = f"  {_RESULT_MARK} {ev.name}" + (f"  {_dim(_clip(target, 90))}" if target else "")
        summary = ev.summary or (ev.output.strip().splitlines() or [""])[0]
        mark = _style(_SUCCESS_MARK, "32") if ev.ok else _style(_FAILURE_MARK, "31")
        lines.append(f"{line}  {mark} {summary}")
        if self.verbose:
            args = started.args if started else None
            lines.append(_dim(f"      arguments: {args!r}"))
            lines += [_dim(f"      {l}") for l in (ev.output.splitlines() or ["(no output)"])]
        self._say(*lines)

    def _on_notice(self, ev) -> None:
        self._say(_style(f"  note: {ev.message}", "33") if ev.level == "warning" else _dim(f"  {ev.message}"))

    def _on_turn_completed(self, ev) -> None:
        self._turn_active = False
        self._spinner.stop()
        print(f"\n{AGENT} {_PROMPT_MARK}")
        self._print_markdown(ev.text or "(no answer text)")
        if ev.sources:
            print(f"\n{_style('Sources', '1')}")
            for n, src in enumerate(ev.sources, 1):
                print(f"  {n}. {src['title']}: {_dim(src['url'])}")
        if ev.stop_reason != "done":
            print(_style(f"\n  Stopped early ({ev.stop_reason}); the answer above summarizes where it got to.", "33"))
        print()
        print(_dim("  " + completion_line(ev.stats, _SEP)))
        sys.stdout.flush()

    def _on_turn_cancelled(self, ev) -> None:
        self._turn_active = False
        self._spinner.stop()
        print(f"\n{_style('Cancelled.', '33')}")
        sys.stdout.flush()

    def _on_turn_failed(self, ev) -> None:
        self._turn_active = False
        self._spinner.stop()
        print(f"\n{_style(f'Error ({ev.error_code}):', '1;31')} {ev.message}")
        print(_dim("  The conversation is kept; your next message continues from here."))
        sys.stdout.flush()

    @staticmethod
    def _print_markdown(text: str) -> None:
        if not _TTY:
            print(text)
            return
        from rich.console import Console
        from rich.markdown import Markdown
        Console(width=min(Console().width, 100)).print(Markdown(text, code_theme="monokai"))

    # -- approvals -----------------------------------------------------------------------------

    def _already_resolved(self, request_id: str) -> bool:
        """True if the queue already holds the resolution (a cancel raced the request): do not ask."""
        self._fill()
        return any(e.type == "approval_resolved" and e.request_id == request_id for e in self._buffer)

    def _on_approval_requested(self, ev) -> None:
        req = ev.request
        if self._already_resolved(req["request_id"]):
            return
        self._spinner.stop()
        self._show_request(req)
        decision, feedback = self._read_decision(req)
        # False = no longer pending (stale answer after a cancel); nothing to do.
        self.session.respond_approval(req["request_id"], decision, feedback)
        if self._turn_active:
            self._spin()

    def _show_request(self, req: dict) -> None:
        outside = _style("  (outside the workspace)", "33") if req.get("outside_workspace") else ""
        print(f"\n{_style('Approval needed:', '1;33')} {req['title']} ({req['reason']}){outside}")
        if req["kind"] == "command":
            for line in (req.get("command") or "").splitlines() or [""]:
                print(f"  $ {line}")
            print(_dim(f"  cwd: {req.get('cwd')}{_SEP}timeout {req.get('timeout')}s"))
            return
        files = _file_summary(req)
        width = max(len(n) for n, _, _ in files)
        for name, added, removed in files:
            counts = f"+{added} {_MINUS}{removed}" if added >= 0 else ""
            print(f"  {name.ljust(width)}  {_dim(counts)}")
        lines = _diff_lines(req)
        for line in lines[:DIFF_PREVIEW_LINES]:
            print(_color_diff_line(line))
        if len(lines) > DIFF_PREVIEW_LINES:
            print(_dim(f"{_ELLIPSIS} {len(lines) - DIFF_PREVIEW_LINES} more lines, press d to show all"))

    def _read_decision(self, req: dict) -> tuple[Decision, str | None]:
        has_diff = req["kind"] == "edit"
        options = ("[y] allow  [a] allow for session  [n] reject  " + ("[d] show full diff  " if has_diff else "")
                   + f"{'—' if _TTY else '-'} or type feedback to reject with a message:")
        print(_dim(options))
        while True:
            try:
                answer = self.input_fn(f"  {_style('Approve?', '1;33')} {_PROMPT_MARK} ").strip()
            except EOFError:
                print()
                return Decision.REJECT, None
            low = answer.lower()
            if not answer:
                continue
            if low in ("y", "yes"):
                return Decision.ALLOW, None
            if low in ("a", "allow session"):
                return Decision.ALLOW_SESSION, None
            if low in ("n", "no"):
                return Decision.REJECT, None
            if low == "d" and has_diff:
                for line in _diff_lines(req):
                    print(_color_diff_line(line))
                continue
            return Decision.REJECT, answer


# -- entry point -------------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("agent_v3", description="A local coding agent (terminal frontend).")
    p.add_argument("--model", default=AgentConfig.model)
    p.add_argument("--reasoning", default=AgentConfig.reasoning, choices=REASONING_EFFORTS)
    p.add_argument("--approval", default=AgentConfig.approval, choices=APPROVAL_MODES,
                   help="ask: approve edits and commands; auto-edit: approve commands only; full-auto: approve nothing.")
    p.add_argument("--workspace", type=Path, default=None, help="Folder the agent works in (default: current folder).")
    p.add_argument("--no-web", action="store_true", help="Turn web search off.")
    p.add_argument("--search-context-size", choices=SEARCH_CONTEXT_SIZES, default=AgentConfig.search_context_size)
    p.add_argument("--allow-domain", action="append", metavar="DOMAIN", help="Limit web search to this domain (repeatable).")
    p.add_argument("--max-rounds", type=int, default=AgentConfig.max_rounds)
    p.add_argument("--max-turn-cost", type=float, default=None, metavar="USD", help="Stop a turn after this much spend.")
    p.add_argument("--no-parallel-reads", action="store_true")
    p.add_argument("--no-prune-history", action="store_true")
    p.add_argument("--no-dedupe-reads", action="store_true")
    p.add_argument("--no-lenient-edit", action="store_true")
    p.add_argument("--prompt", type=Path, default=None, help="Use this file instead of the bundled system prompt.")
    p.add_argument("--transcript", type=Path, default=None, help="Append the conversation to this Markdown file.")
    p.add_argument("--events-log", type=Path, default=None, help="Append every event to this JSONL file.")
    p.add_argument("--verbose", action="store_true", help="Show tool arguments and output, and per-round token lines.")
    return p


def config_from_args(args: argparse.Namespace) -> AgentConfig:
    return AgentConfig(
        model=args.model, reasoning=args.reasoning, approval=args.approval,
        workspace=args.workspace or Path.cwd(), web_search=not args.no_web,
        search_context_size=args.search_context_size, web_allowed_domains=args.allow_domain,
        max_rounds=args.max_rounds, max_turn_cost_usd=args.max_turn_cost,
        parallel_reads=not args.no_parallel_reads, prune_history=not args.no_prune_history,
        dedupe_reads=not args.no_dedupe_reads, lenient_edit_match=not args.no_lenient_edit,
        prompt_path=args.prompt)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = config_from_args(args)
    except ValueError as e:
        parser.error(str(e))
    if not config.workspace.is_dir():
        parser.error(f"workspace is not a folder: {config.workspace}")
    if config.prompt_path is not None and not config.prompt_path.is_file():
        parser.error(f"prompt file not found: {config.prompt_path}")

    # Piped output on Windows defaults to a legacy code page; answers and summaries contain Unicode.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure") and (stream.encoding or "").lower().replace("-", "") != "utf8":
            stream.reconfigure(encoding="utf-8", errors="replace")

    writers = []
    if args.transcript:
        writers.append(TranscriptWriter(args.transcript))
    if args.events_log:
        writers.append(EventLogWriter(args.events_log))
    events: queue.Queue = queue.Queue()
    session = Session(config, events.put)         # on_event runs under the session lock: only queue.put
    try:
        return Cli(session, events, verbose=args.verbose, sinks=tuple(writers)).run()
    finally:
        for w in writers:
            w.close()


if __name__ == "__main__":
    raise SystemExit(main())
