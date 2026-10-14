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
import json
import logging
import os
import sys
import threading
from pathlib import Path
from typing import BinaryIO, Callable

from ..approvals import Decision
from ..config import AgentConfig
from ..events import Event
from ..model import ModelAdapter
from ..session import Busy, Session
from .args import add_config_args, config_from_args

logger = logging.getLogger("agent_v3.stdio_server")

DECISIONS = tuple(d.value for d in Decision)


class BadRequest(Exception):
    """The client's message is malformed; the text goes back in an `error` line."""


class StdioServer:
    def __init__(self, config: AgentConfig, model: ModelAdapter | None = None, *,
                 stdin: BinaryIO, stdout: BinaryIO):
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
        }
        self.session = Session(config, self.on_event, model=model)    # emits session_started from here

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

    stdin, stdout = claim_stdio()
    return StdioServer(config, model, stdin=stdin, stdout=stdout).serve()


if __name__ == "__main__":
    raise SystemExit(main())
