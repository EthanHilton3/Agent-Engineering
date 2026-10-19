"""JSON-lines frontend (plan §10.2): newline-delimited JSON on stdin/stdout, logs on stderr only.

Threading: the main thread reads stdin and calls `Session` commands. `Session` calls `on_event` from worker
threads while holding its lock, so `on_event` does exactly one thing: serialize the event, write one line under
`_write_lock`, flush. The write lock is separate from the session lock because the reader thread also writes
(usage and error replies). The reader never holds the write lock while taking the session lock, so the lock order
is always session -> write. A client that stops reading stdout will eventually stall the session (pipe full).

Stdout is reserved for the protocol: at startup the real stdout is duplicated for our use and fd 1 is pointed at
stderr, so a stray `print`, a library, or a child process cannot corrupt the stream. stdin gets the same
treatment (fd 0 becomes the null device).
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import BinaryIO, Callable

from ..approvals import Decision
from ..config import AgentConfig
from ..events import Event
from ..model import ModelAdapter
from ..session import Busy, Session
from ..sessions import (AmbiguousSession, SessionInUse, SessionNotFound, SessionStore, SessionStoreError,
                        config_for_resume)
from .args import add_config_args, add_session_args, config_from_args, explicit_settings
from .transcript import export_transcript

logger = logging.getLogger("agent_v3.stdio_server")

DECISIONS = tuple(d.value for d in Decision)


class BadRequest(Exception):
    """The client's message is malformed; the text goes back in an `error` line."""


class ProtocolError(Exception):
    """A command failed with its own `error` code (not_found, in_use, ...); the text goes back in an `error` line."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class StdioServer:
    """`store` is the store the session is saved to (None: nothing is saved, as with --no-save). `resume` is a full
    session id (the caller resolves refs). `explicit` names the settings typed on the command line (option C)."""

    def __init__(self, config: AgentConfig, model: ModelAdapter | None = None, *,
                 stdin: BinaryIO, stdout: BinaryIO, store: SessionStore | None = None, resume: str | None = None,
                 explicit: set[str] | frozenset = frozenset()):
        self._in = stdin
        self._out = stdout
        self._write_lock = threading.Lock()
        self._broken = False                  # the client closed its end of our stdout
        self._running = True
        self._handlers: dict[str, Callable[[dict], None]] = {
            "user_message": self._user_message,
            "approval_response": self._approval_response,
            "cancel": self._cancel,
            "new_conversation": self._new_conversation,
            "get_usage": self._get_usage,
            "shutdown": self._shutdown,
            "list_sessions": self._list_sessions,
            "resume_session": self._resume_session,
            "new_session": self._new_session,
            "export_session": self._export_session,
            "delete_session": self._delete_session,
        }
        self._launch = config                 # new_session and resume_session start from the launch settings (§5.1)
        self._model = model                   # an injected adapter is shared by every session; None: one per session
        self._store = store
        self._explicit = set(explicit)
        # Listing, export and delete only read the saved files, so they work under --no-save too.
        self._reader = store or SessionStore.for_workspace(config.workspace)
        self.session = self._open(resume)     # emits session_started (and session_resumed) from here

    # -- output --------------------------------------------------------------------------------

    def on_event(self, event: Event) -> None:
        """Runs under the session lock: serialize, write one line, flush, nothing else."""
        self._write(event.to_dict())

    def _write(self, message: dict) -> None:
        line = json.dumps(message).encode("ascii") + b"\n"      # ASCII-escaped: no encoding surprises on a pipe
        with self._write_lock:
            if self._broken:
                return
            try:
                self._out.write(line)
                self._out.flush()
            except (OSError, ValueError) as e:
                self._broken = True
                logger.error("client closed stdout (%s); no more output will be written", e)

    def _error(self, code: str, message: str) -> None:
        self._write({"type": "error", "code": code, "message": message})

    # -- input ---------------------------------------------------------------------------------

    def serve(self) -> int:
        """Handle commands until `shutdown`, EOF on stdin, or the client closes our stdout."""
        try:
            for raw in iter(self._in.readline, b""):
                self._handle_line(raw)
                if not self._running or self._broken:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            self.session.close()              # cancels a running turn; its turn_cancelled is written before we exit
        return 0

    def _handle_line(self, raw: bytes) -> None:
        try:
            text = raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            return self._error("bad_request", "input is not valid UTF-8")
        if not text:
            return
        try:
            message = json.loads(text)
        except (ValueError, RecursionError) as e:
            return self._error("bad_request", f"invalid JSON: {e}")
        if not isinstance(message, dict):
            return self._error("bad_request", "each line must be a JSON object")
        kind = message.get("type")
        handler = self._handlers.get(kind) if isinstance(kind, str) else None
        if handler is None:
            return self._error("bad_request", f"unknown message type: {kind!r}")
        try:
            handler(message)
        except BadRequest as e:
            self._error("bad_request", f"{kind}: {e}")
        except Busy as e:
            self._error("busy", str(e))
        except ProtocolError as e:
            self._error(e.code, str(e))
        except Exception as e:                # a bug must not take the server down
            logger.exception("handling %s failed", kind)
            self._error("internal_error", f"{type(e).__name__}: {e}")

    # -- commands ------------------------------------------------------------------------------

    @staticmethod
    def _string(message: dict, key: str, *, required: bool = True) -> str | None:
        value = message.get(key)
        if value is None and not required:
            return None
        if not isinstance(value, str) or (required and not value.strip()):
            raise BadRequest(f"'{key}' must be {'a non-empty' if required else 'a'} string")
        return value

    def _user_message(self, message: dict) -> None:
        self.session.start_turn(self._string(message, "text"))      # raises Busy while a turn runs

    def _approval_response(self, message: dict) -> None:
        request_id = self._string(message, "request_id")
        decision = message.get("decision")
        if decision not in DECISIONS:
            raise BadRequest(f"'decision' must be one of {', '.join(DECISIONS)}")
        feedback = self._string(message, "feedback", required=False)
        if not self.session.respond_approval(request_id, decision, feedback):
            # Normal race (the turn was cancelled, or the request was already answered): ignored, not an error.
            logger.warning("approval_response for %s ignored: not pending", request_id)

    def _cancel(self, message: dict) -> None:
        self.session.cancel()                 # a no-op when idle

    def _new_conversation(self, message: dict) -> None:
        self.session.new_conversation()       # raises Busy while a turn runs

    def _get_usage(self, message: dict) -> None:
        self._write({"type": "usage", "totals": self.session.usage_totals()})

    def _shutdown(self, message: dict) -> None:
        self._running = False

    # -- saved sessions (sessions spec §7.2) ---------------------------------------------------

    def _open(self, resume_id: str | None) -> Session:
        """A new session (None) or the saved one with this full id. Raises SessionStoreError, with nothing emitted."""
        config = self._launch
        if resume_id is not None:
            config = config_for_resume(config, self._reader.load(resume_id).info, self._explicit)
        return Session(config, self.on_event, model=self._model, store=self._store, resume=resume_id)

    def _switch(self, resume_id: str | None) -> None:
        """Build the new session before closing the old one, so a failed resume leaves the current one untouched."""
        try:
            new = self._open(resume_id)
        except SessionStoreError as e:
            raise self._protocol_error(e) from e
        old, self.session = self.session, new
        old.close()                           # idle, so it emits nothing; this frees its lock and file handles

    @staticmethod
    def _protocol_error(e: SessionStoreError) -> ProtocolError:
        code = ("not_found" if isinstance(e, SessionNotFound) else "ambiguous" if isinstance(e, AmbiguousSession)
                else "in_use" if isinstance(e, SessionInUse) else "internal_error")
        return ProtocolError(code, str(e))

    def _resolve(self, ref: str) -> str:
        try:
            return self._reader.resolve(ref)
        except SessionStoreError as e:
            raise self._protocol_error(e) from e

    def _require_idle(self) -> None:
        if self.session.busy:
            raise Busy("A turn is running; cancel it first.")

    def _list_sessions(self, message: dict) -> None:
        limit = message.get("limit")
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            raise BadRequest("'limit' must be a positive integer")
        current = self.session.session_id
        rows = self._reader.list()
        sessions = [dataclasses.asdict(r) for r in rows[:limit]]
        for row in sessions:
            if row["session_id"] == current:
                row["status"] = "current"     # the open session always looks in use to its own process
        self._write({"type": "sessions", "current": current, "total": len(rows), "sessions": sessions})

    def _resume_session(self, message: dict) -> None:
        ref = self._string(message, "session_id", required=False)
        latest = message.get("latest", False)
        if not isinstance(latest, bool):
            raise BadRequest("'latest' must be true or false")
        if (ref is None) == (not latest):
            raise BadRequest("give either 'session_id' or 'latest': true")
        self._require_idle()
        if self._store is None:
            raise ProtocolError("saving_disabled", "Sessions are not being saved (--no-save), so none can be resumed.")
        sid = self._resolve("latest" if latest else ref)
        if sid == self.session.session_id:
            raise BadRequest(f"session {sid} is already the open session")
        self._switch(sid)

    def _new_session(self, message: dict) -> None:
        self._require_idle()
        self._switch(None)

    def _export_session(self, message: dict) -> None:
        ref = self._string(message, "session_id", required=False)
        current = self.session.session_id
        if self._store is None and (ref is None or ref.strip().lower() in (current, current[2:])):
            raise ProtocolError("saving_disabled", "The open session is not being saved (--no-save), so it has no log.")
        sid = current if ref is None else self._resolve(ref)
        events = self._reader.events_path(sid)
        if not events.is_file():
            if sid == current:                # saved from the first message on; nothing to show before that
                return self._write({"type": "transcript", "session_id": sid, "markdown": ""})
            raise ProtocolError("not_found", f"Session {sid} has no saved events.")
        with tempfile.TemporaryDirectory() as tmp:
            out = export_transcript(events, Path(tmp) / "transcript.md")
            markdown = out.read_text(encoding="utf-8")
        self._write({"type": "transcript", "session_id": sid, "markdown": markdown})

    def _delete_session(self, message: dict) -> None:
        sid = self._resolve(self._string(message, "session_id"))
        self._require_idle()
        if sid == self.session.session_id:
            raise ProtocolError("in_use", f"Session {sid} is the open session; start another one first.")
        try:
            self._reader.delete(sid)
        except SessionStoreError as e:
            raise self._protocol_error(e) from e
        self._write({"type": "session_deleted", "session_id": sid})


# -- stdio ownership -----------------------------------------------------------------------------


def claim_stdio() -> tuple[BinaryIO, BinaryIO]:
    """(stdin, stdout) for the protocol; fd 0 and fd 1 are then redirected away from it (see module docstring)."""
    sys.stdout.flush()
    proto_in = os.fdopen(os.dup(0), "rb")
    proto_out = os.fdopen(os.dup(1), "wb")
    devnull = os.open(os.devnull, os.O_RDONLY)
    os.dup2(devnull, 0)
    os.close(devnull)
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return proto_in, proto_out


def _load_fake_model(config: AgentConfig, script: Path) -> ModelAdapter:
    """TEST ONLY: a FakeModelAdapter built from a JSON script, in the format `tests/fakes.py` documents."""
    tests = Path(__file__).resolve().parents[2] / "tests"
    if not (tests / "fakes.py").is_file():
        raise ValueError(f"--fake-model-script needs the repository's tests folder ({tests})")
    sys.path.insert(0, str(tests))
    from fakes import FakeModelAdapter, rounds_from_json
    with script.open(encoding="utf-8") as f:
        return FakeModelAdapter(config, rounds_from_json(json.load(f)))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("agent_v3.frontends.stdio_server",
                                description="JSON-lines agent server: commands on stdin, events on stdout, logs on stderr.")
    add_config_args(p)
    add_session_args(p)
    p.add_argument("--log-level", default="warning", choices=("debug", "info", "warning", "error"),
                   help="Verbosity of the log written to stderr.")
    p.add_argument("--fake-model-script", type=Path, default=None, metavar="FILE",
                   help="TEST ONLY: answer from this JSON script of rounds instead of calling the API.")
    return p


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
    if args.no_save and (args.resume is not None or args.continue_):
        parser.error("--no-save cannot be combined with --resume or --continue.")
    if args.resume is not None and args.continue_:
        parser.error("--resume and --continue cannot be combined.")
    if args.resume == "":
        parser.error("--resume needs a session id, a prefix of one, or 'latest'.")

    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    logging.basicConfig(stream=sys.stderr, level=args.log_level.upper(),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    model = None
    if args.fake_model_script is not None:
        try:
            model = _load_fake_model(config, args.fake_model_script)
        except (OSError, ValueError) as e:
            parser.error(f"cannot load the model script: {e}")

    store = None if args.no_save else SessionStore.for_workspace(config.workspace)
    resume_id = None
    try:
        if args.continue_:
            try:
                resume_id = store.resolve("latest")
            except SessionNotFound:
                logger.info("no saved sessions in this workspace; starting a new one")
        elif args.resume is not None:
            resume_id = store.resolve(args.resume)
    except SessionStoreError as e:
        print(e, file=sys.stderr)
        return 2                              # like the other startup errors: nothing on stdout

    stdin, stdout = claim_stdio()
    try:
        server = StdioServer(config, model, stdin=stdin, stdout=stdout, store=store, resume=resume_id,
                             explicit=explicit_settings(args))
    except SessionStoreError as e:            # in use, or gone since it was resolved; nothing was emitted
        message = str(e)
        if args.continue_ and isinstance(e, SessionInUse):
            message = f"{message.rstrip('.')}; use --resume to pick another."
        print(message, file=sys.stderr)
        return 2
    return server.serve()


if __name__ == "__main__":
    raise SystemExit(main())
