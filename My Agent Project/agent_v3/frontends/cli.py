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
import textwrap
import threading
import time
from collections import Counter, deque
from contextlib import suppress
from dataclasses import replace
from datetime import datetime
from itertools import cycle
from pathlib import Path
from typing import Callable

from ..approvals import Decision
from ..config import APPROVAL_MODES, REASONING_EFFORTS, AgentConfig
from ..events import Event
from ..pricing import PRICING
from ..prompt import APPROVAL_TEXT
from ..session import Busy, Session
from ..sessions import SessionInUse, SessionNotFound, SessionStore, SessionStoreError, config_for_resume
from .args import add_config_args, add_session_args, config_from_args, explicit_settings
from .commands import COMMANDS, format_sessions, reconfigure_utf8
from .eventlog import EventLogWriter
from .formatting import completion_line, fmt_cost, format_usage, round_summary
from .transcript import export_transcript

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
SLASH_COMMANDS = ("/new", "/sessions", "/resume", "/export", "/model", "/reasoning", "/approval", "/usage", "/quit")
ARG_COMMANDS = re.compile(r"/(resume|export|sessions|model|reasoning|approval)(?:\s+(.+))?",
                          re.IGNORECASE)          # these take an argument (§6.2)
SETTINGS = ("model", "reasoning", "approval")     # changeable between turns (§5.6)
CACHE_NOTES = {"model": "the next request starts with a cold cache",
               "reasoning": "the next request starts with a cold cache",        # measured in the S5 smoke test
               "approval": "the system prompt names the mode, so the next request starts with a cold cache"}
FULL_AUTO_WARNING = "Edits and commands now run without asking, except risky commands and anything outside the workspace."
LIST_RECENT = 10                                  # how many sessions a bare /sessions shows
RECAP_ANSWER_LINES = 15


def _style(text: str, code: str) -> str:
    return f"\033[{code}m{text}{_RESET}" if _COLOR else text


def _dim(text: str) -> str:
    return _style(text, "2")


def _short_when(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return iso[:16]


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


class SessionOpener:
    """Builds the `Session` for `/new` (ref None) and for a resume (a full session id), with the right config:
    a new session gets the launch config; a resumed one gets its saved model and reasoning unless they were
    typed (option C, §5.1). `model_of` supplies the model adapter to reuse (None: build a fresh one)."""

    def __init__(self, store: SessionStore | None, on_event: Callable[[Event], None], launch: AgentConfig,
                 explicit: set[str] | frozenset = frozenset(), model_of: Callable[[], object] | None = None):
        self.store, self.on_event, self.launch, self.model_of = store, on_event, launch, model_of
        self.explicit = set(explicit)

    def remember(self, name: str, value: str) -> None:
        """A setting changed by command (/model, /reasoning, /approval): later sessions start from it (the working
        config), and a resume keeps it instead of restoring the saved one, as if it had been typed (§5.1)."""
        self.launch = replace(self.launch, **{name: value})
        self.explicit.add(name)

    def __call__(self, resume_id: str | None) -> Session:
        config = self.launch
        if resume_id is not None:
            config = config_for_resume(self.launch, self.store.load(resume_id).info, set(self.explicit))
        model = self.model_of() if self.model_of is not None else None
        return Session(config, self.on_event, model=model, store=self.store, resume=resume_id)


class Cli:
    def __init__(self, session: Session, events: "queue.Queue[Event]", *, verbose: bool = False,
                 input_fn: Callable[[str], str] = input, sinks: tuple[Callable, ...] = (),
                 store: SessionStore | None = None, open_session: Callable[[str | None], Session] | None = None,
                 launch_config: AgentConfig | None = None, explicit: set[str] | frozenset = frozenset()):
        self.session = session
        self.q = events
        self.verbose = verbose
        self.input_fn = input_fn
        self.sinks = list(sinks)
        self.store = store
        self.explicit = set(explicit)
        # /new and the default factory use the launch settings, never values a resume restored from disk.
        self.open_session = open_session or SessionOpener(
            store, events.put, launch_config or session.config, self.explicit, lambda: self.session.model)
        self._listed: list[str] = []              # session ids in the order the last listing showed them
        self._buffer: deque = deque()             # events pulled from the queue ahead of dispatch
        self._spinner = _Spinner()
        self._spin_message = "Thinking…"
        self._turn_active = False
        self._last_interrupt: float | None = None
        self._calls: dict[str, Event] = {}        # call_id -> tool_started
        self._group_count: Counter = Counter()
        self._headed: set[int] = set()
        self._sink_error_shown = False
        self._was_saved = False

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
                match = ARG_COMMANDS.fullmatch(text)
                if match or re.fullmatch(r"/[A-Za-z]+", text):
                    cmd, arg = (f"/{match.group(1).lower()}", (match.group(2) or "").strip()) if match else (text.lower(), "")
                    if not self._command(cmd, arg):
                        break
                    continue
                self._run_turn(text)
        except (KeyboardInterrupt, _Quit):
            print()                               # move past the prompt line
        finally:
            self._shutdown()
        return 0

    def _command(self, cmd: str, arg: str = "") -> bool:
        """Run a slash command. False means quit."""
        if cmd == "/quit":
            return False
        if cmd == "/new":
            self._switch(None)
        elif cmd == "/sessions":
            self._cmd_sessions(arg)
        elif cmd == "/resume":
            self._cmd_resume(arg)
        elif cmd == "/export":
            self._cmd_export(arg)
        elif cmd[1:] in SETTINGS:
            self._cmd_setting(cmd[1:], arg)
        elif cmd == "/usage":
            print(format_usage(self.session.config.model, self.session.usage_totals()))
        else:
            print(_dim(f"Unknown command {cmd}. Commands: {', '.join(SLASH_COMMANDS)}"))
        return True

    # -- sessions (§6.2) -----------------------------------------------------------------------

    def _note(self, text: str) -> None:
        self._say(_dim(f"  {text}"))

    def _switch(self, resume_id: str | None) -> bool:
        """Open a new session (None) or resume one, then close the current one. The new one is built first,
        so a failed resume leaves the current session untouched."""
        try:
            new = self.open_session(resume_id)
        except SessionStoreError as e:
            self._say(_style(f"  {e}", "33"))
            return False
        old, self.session = self.session, new
        old.close()
        self._calls.clear()
        self._group_count.clear()
        self._headed.clear()
        self._pump()                              # the new session's opening events: banner and recap
        return True

    def _need_store(self) -> SessionStore | None:
        if self.store is None or not self.session.saved:
            self._note("Sessions are not being saved (--no-save, or saving stopped), so there is nothing to list.")
            return None
        return self.store

    def _list_store(self) -> SessionStore:
        """Listing only reads saved files, so it works under --no-save too (as the server's list_sessions does)."""
        return self.store or SessionStore.for_workspace(self.session.config.workspace)

    def _show_sessions(self, rows) -> None:
        self._listed = [r.session_id for r in rows]
        self._say(*format_sessions(rows, current=self.session.session_id, ascii_only=not _TTY))

    def _cmd_sessions(self, arg: str) -> None:
        if arg.lower() not in ("", "all"):
            self._note("Usage: /sessions [all]")
            return
        rows = self._list_store().list()
        if not rows:
            self._note("No saved sessions yet.")
            return
        shown = rows if arg else rows[:LIST_RECENT]
        self._show_sessions(shown)
        if len(shown) < len(rows):
            self._note(f"{_ELLIPSIS} {len(rows) - len(shown)} more: /sessions all")

    def _cmd_resume(self, arg: str) -> None:
        store = self._need_store()
        if store is None:
            return
        try:
            if not arg:
                rows = store.list()
                if not rows:
                    self._note("No saved sessions yet.")
                    return
                self._show_sessions(rows)
                try:
                    arg = self.input_fn(f"Resume which? [1-{len(rows)}, Enter = stay here] ").strip()
                except EOFError:
                    print()
                    return
                if not arg:
                    return
            sid = self._resolve_choice(store, arg)
        except SessionStoreError as e:
            self._say(_style(f"  {e}", "33"))
            return
        if sid == self.session.session_id:
            self._note(f"Already in session {sid}.")
            return
        self._switch(sid)

    def _resolve_choice(self, store: SessionStore, arg: str) -> str:
        """A list number from the last /sessions (or the full list), else an id, prefix or 'latest'."""
        if arg.isdigit():
            ids = self._listed or [r.session_id for r in store.list()]
            if 1 <= int(arg) <= len(ids):
                return ids[int(arg) - 1]
            if len(arg) < 4:
                raise SessionNotFound(f"There is no session number {arg} (the list has {len(ids)}).")
        return store.resolve(arg)

    def _cmd_export(self, arg: str) -> None:
        store = self._need_store()
        if store is None:
            return
        events = store.events_path(self.session.session_id)
        if not events.is_file():
            self._note("Nothing to export yet: the session is saved from its first message on.")
            return
        out = Path(arg).expanduser() if arg else events.with_name("transcript.md")
        try:
            self._say(_dim(f"  Transcript written to {export_transcript(events, out)}"))
        except OSError as e:
            self._say(_style(f"  could not write the transcript: {e}", "33"))

    # -- settings (§5.6) -----------------------------------------------------------------------

    def _choices(self, name: str) -> list[str]:
        if name == "approval":
            return [_dim(f"    {mode:<9}  {APPROVAL_TEXT[mode]}") for mode in APPROVAL_MODES]
        values = PRICING if name == "model" else REASONING_EFFORTS
        label = "models with known prices" if name == "model" else "levels"
        return [_dim(line) for line in textwrap.wrap(f"{label}: {', '.join(values)}", 100,
                                                     initial_indent="    ", subsequent_indent="      ")]

    def _cmd_setting(self, name: str, arg: str) -> None:
        """`/model`, `/reasoning`, `/approval`: show the value and the choices, or change it for the open session."""
        current = getattr(self.session.config, name)
        if not arg:
            self._say(_dim(f"  {name}: {current}"), *self._choices(name))
            return
        value = arg if name == "model" else arg.lower()
        try:
            changed = self.session.update_config(**{name: value})
        except (ValueError, Busy) as e:
            self._say(_style(f"  {e}", "33"), *self._choices(name))
            return
        remember = getattr(self.open_session, "remember", None)
        if remember is not None:                  # /new and /resume start from it from now on
            remember(name, value)
        if not changed:
            self._note(f"{name} is already {current}")
        self._pump()                              # config_changed prints the confirmation

    def _saved_hint(self) -> str | None:
        """The exit line for a session that was saved and has something in it."""
        if self.store is None or not self._was_saved:
            return None
        sid = self.session.session_id
        if not self.store.events_path(sid).is_file():
            return None
        workspace = self.session.config.workspace
        where = f" --workspace {workspace}" if workspace.resolve() != Path.cwd().resolve() else ""
        return f"Session saved: {sid}{_SEP}resume with: python -m agent_v3{where} --resume {sid[2:]}"

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
            self._was_saved = self.session.saved
            self.session.close()                  # cancels a running turn; its event is drained below
            self._pump()
            print()
            print(format_usage(self.session.config.model, self.session.usage_totals()))
            if (hint := self._saved_hint()) is not None:
                print(_dim(hint))

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
                    self._say(_style(f"  warning: could not write the event log: {e}", "33"))
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
                  _dim("Enter a task. /new = new session, /sessions, /resume, /export, /model, /reasoning, /approval, "
                       "/usage = totals, /quit = exit. Ctrl+C cancels a running turn."),
                  *([_dim(f"Saving this session in {self.store.root} (git-ignored). --no-save turns saving off.")]
                    if self.store is not None and self.session.saved else []))

    def _on_session_resumed(self, ev) -> None:
        cost = ev.totals.get("model_cost_usd", 0.0) + ev.totals.get("web_cost_usd", 0.0)
        last = ev.turns[-1] if ev.turns else None
        active = _short_when(last["ts"]) if last and last.get("ts") else _short_when(ev.created)
        n = ev.turns_total
        lines = [_dim(f"Resumed {ev.session_id}{_SEP}\"{ev.title}\"{_SEP}{n} turn{'' if n == 1 else 's'}{_SEP}"
                      f"{fmt_cost(cost)}{_SEP}last active {active}")]
        config, saved = self.session.config, ev.saved_config
        for name in ("model", "reasoning"):
            if saved.get(name) and getattr(config, name) != saved[name]:
                lines.append(_dim(f"  {name} {getattr(config, name)} (--{name}; saved with {saved[name]})"))
        if saved.get("approval") and config.approval != saved["approval"]:
            lines.append(_dim(f"  approval {config.approval} (saved with {saved['approval']}; "
                              "approval is never restored)"))
        if last is not None:
            lines += [f"\n{YOU} {_PROMPT_MARK} {last['user_message']}"]
            if last.get("text"):
                answer = last["text"].splitlines()
                lines += [f"{AGENT} {_PROMPT_MARK}", *answer[:RECAP_ANSWER_LINES]]
                if len(answer) > RECAP_ANSWER_LINES:
                    lines.append(_dim(f"{_ELLIPSIS} {len(answer) - RECAP_ANSWER_LINES} more lines"))
        self._say(*lines)

    def _on_config_changed(self, ev) -> None:
        lines = []
        for name, change in ev.changes.items():
            note = CACHE_NOTES.get(name)
            lines.append(_dim(f"  {name} {change['to']} (was {change['from']})" + (f"; {note}" if note else "")))
        if ev.history == "pruned":
            lines.append(_dim("  earlier turns continue as their summaries: their full detail belonged to the old model"))
        if ev.changes.get("approval", {}).get("to") == "full-auto":
            lines.append(_style(f"  {FULL_AUTO_WARNING}", "33"))
        if lines:
            self._say(*lines)

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
    p = argparse.ArgumentParser(
        "agent_v3", description="A local coding agent (terminal frontend).",
        epilog="Every session is saved under <workspace>/.agent_v3/sessions/ (git-ignored, plain text, kept until you "
               "delete it). Resume with --continue or --resume REF; `python -m agent_v3 sessions` lists them, "
               "`sessions delete REF` removes one, `export REF` writes a Markdown transcript. --no-save turns saving off.")
    add_config_args(p)
    add_session_args(p)
    p.add_argument("--transcript", default=None, help=argparse.SUPPRESS)       # removed: kept to explain why
    p.add_argument("--events-log", type=Path, default=None, help="Append every event to this JSONL file.")
    p.add_argument("--verbose", action="store_true", help="Show tool arguments and output, and per-round token lines.")
    return p


def _pick_session(store: SessionStore) -> str | None:
    """`--resume` without REF: list the sessions and ask. None means a new session."""
    rows = store.list()
    if not rows:
        print(_dim("No saved sessions in this workspace; starting a new one."))
        return None
    print("\n".join(format_sessions(rows, ascii_only=not _TTY)))
    while True:
        try:
            answer = input(f"Resume which? [1-{len(rows)}, Enter = new session] ").strip()
        except EOFError:
            print()
            return None
        if not answer:
            return None
        try:
            if answer.isdigit() and 1 <= int(answer) <= len(rows):
                return rows[int(answer) - 1].session_id
            return store.resolve(answer)
        except SessionStoreError as e:
            print(_style(f"  {e}", "33"))


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if argv and argv[0] in COMMANDS:
        from .commands import main as commands_main
        return commands_main(argv)
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.transcript is not None:
        parser.error("--transcript was removed: sessions are saved automatically. "
                     "Use /export or `python -m agent_v3 export latest -o FILE`.")
    if args.no_save and (args.resume is not None or args.continue_):
        parser.error("--no-save cannot be combined with --resume or --continue.")
    if args.resume is not None and args.continue_:
        parser.error("--resume and --continue cannot be combined.")
    try:
        config = config_from_args(args)
    except ValueError as e:
        parser.error(str(e))
    if not config.workspace.is_dir():
        parser.error(f"workspace is not a folder: {config.workspace}")
    if config.prompt_path is not None and not config.prompt_path.is_file():
        parser.error(f"prompt file not found: {config.prompt_path}")

    reconfigure_utf8()
    store = None if args.no_save else SessionStore.for_workspace(config.workspace)
    explicit = explicit_settings(args)
    events: queue.Queue = queue.Queue()
    # on_event runs under the session lock: only queue.put. A fresh model adapter per session (model_of=None).
    opener = SessionOpener(store, events.put, config, explicit)
    try:
        resume_id = None
        if store is not None and args.continue_:
            try:
                resume_id = store.resolve("latest")
            except SessionNotFound:
                print(_dim("No saved sessions in this workspace; starting a new one."))
        elif store is not None and args.resume == "":
            resume_id = _pick_session(store)
        elif store is not None and args.resume is not None:
            resume_id = store.resolve(args.resume)
        session = opener(resume_id)               # nothing has been emitted if this raises
    except SessionStoreError as e:
        message = str(e)
        if args.continue_ and isinstance(e, SessionInUse):
            message = f"{message.rstrip('.')}; use --resume to pick another."
        print(message, file=sys.stderr)
        return 2

    writers = [EventLogWriter(args.events_log)] if args.events_log else []
    try:
        return Cli(session, events, verbose=args.verbose, input_fn=input, sinks=tuple(writers), store=store,
                   open_session=opener, launch_config=config, explicit=explicit).run()
    finally:
        for w in writers:
            w.close()


if __name__ == "__main__":
    raise SystemExit(main())
