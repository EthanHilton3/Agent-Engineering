"""Saved sessions (sessions spec §4, §5.1): the on-disk store, the recorder `Session` writes through, locking.

Layout: `<root>/<session_id>/` holds `events.jsonl` (every event except `text_delta`), `history.jsonl` (one
line per commit or reset), `meta.json` (a listing cache, rebuilt from the two logs when missing or stale)
and `lock` (an OS lock held while the session is open in a process). Nothing here imports from `frontends/`.
"""
from __future__ import annotations

import dataclasses
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import REASONING_EFFORTS, AgentConfig
from .events import Event, event_from_dict, jsonable, now_iso
from .jsonl import append_line, read_jsonl, repair_tail
from .stats import StatsCounter, TurnStats

if os.name == "nt":
    import msvcrt
else:
    import fcntl

FORMAT_VERSION = 1
SESSION_ID_RE = re.compile(r"s_[0-9a-f]{12}")
MIN_REF_CHARS = 4                     # characters after "s_" a prefix must have
TITLE_MAX_CHARS = 60
TERMINAL_EVENTS = frozenset({"turn_completed", "turn_cancelled", "turn_failed"})
EVENTS_FILE, HISTORY_FILE, META_FILE, LOCK_FILE = "events.jsonl", "history.jsonl", "meta.json", "lock"
RESTORABLE_SETTINGS = ("model", "reasoning")       # never "approval" (owner decision, option C)
_REPLACE_TRIES, _REPLACE_PAUSE_S = 5, 0.02
_LOCK_TRIES, _LOCK_PAUSE_S = 5, 0.025      # ~100 ms: outlasts another process's momentary status probe
_O_BINARY = getattr(os, "O_BINARY", 0)


# -- errors and records ------------------------------------------------------------------------

class SessionStoreError(Exception):
    """A problem with a saved session that a frontend reports to the user."""


class SessionNotFound(SessionStoreError):
    pass


class AmbiguousSession(SessionStoreError):
    def __init__(self, ref: str, matches: list[str]):
        self.matches = matches
        super().__init__(f"{ref!r} matches {len(matches)} sessions: {', '.join(matches)}")


class SessionInUse(SessionStoreError):
    def __init__(self, session_id: str, owner_pid: int | None = None):
        self.session_id = session_id
        self.owner_pid = owner_pid
        pid = f" (pid {owner_pid})" if owner_pid else ""
        super().__init__(f"Session {session_id} is open in another agent_v3 process{pid}.")


@dataclass(frozen=True)
class SessionInfo:
    """One listing row."""
    session_id: str
    title: str
    created: str
    updated: str
    turns: int
    cost_usd: float
    model: str
    reasoning: str
    status: str                       # idle | in_use | interrupted | current (the server's open session)


@dataclass(frozen=True)
class InterruptedTurn:
    """A turn whose `turn_started` is logged but which has no history line (§5.3)."""
    turn_id: str
    user_message: str
    events: list                      # this turn's saved event dicts, from its turn_started on


@dataclass
class SavedSession:
    """What a resume needs."""
    info: SessionInfo
    turn_lines: list[dict]            # history.jsonl "turn" lines after the last reset
    all_turn_lines: int
    turn_no: int
    last_seq: int
    totals: dict                      # TurnStats.to_dict() shape
    interrupted: InterruptedTurn | None
    saved_config: dict = field(default_factory=dict)   # {model, reasoning, approval, prune_history} at the last save


def session_title(user_message: str) -> str:
    """The first non-empty line, whitespace collapsed, clipped to 60 characters."""
    for line in user_message.splitlines():
        text = " ".join(line.split())
        if text:
            return text if len(text) <= TITLE_MAX_CHARS else text[: TITLE_MAX_CHARS - 1] + "…"
    return ""


def config_for_resume(launch: AgentConfig, info: SessionInfo, explicit: set[str]) -> AgentConfig:
    """`launch` with each RESTORABLE_SETTINGS field taken from the saved session unless it is in `explicit`."""
    changes = {}
    for name in RESTORABLE_SETTINGS:
        value = getattr(info, name, "")
        if name not in explicit and value and not (name == "reasoning" and value not in REASONING_EFFORTS):
            changes[name] = value
    return dataclasses.replace(launch, **changes)


# -- locking -----------------------------------------------------------------------------------

class _Locked(OSError):
    """The lock is held by another handle (another process, or another open in this one)."""


class _FileLock:
    """Non-blocking exclusive OS lock on one file. The OS releases it when the process dies (§4.6)."""

    def __init__(self, path: Path, *, create: bool = True):
        self.fd: int | None = os.open(path, os.O_RDWR | (os.O_CREAT if create else 0) | _O_BINARY, 0o600)
        try:
            if os.name == "nt":
                msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)
            else:
                fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(self.fd)
            self.fd = None
            raise _Locked(f"{path} is locked") from None

    def close(self) -> None:
        fd, self.fd = self.fd, None
        if fd is None:
            return
        try:
            if os.name == "nt":
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        finally:
            os.close(fd)


# -- store -------------------------------------------------------------------------------------

class SessionStore:
    """The saved sessions under one root folder. `list`, `resolve` and `load` read without the lock."""

    def __init__(self, root: str | os.PathLike, *, gitignore: str | os.PathLike | None = None):
        self.root = Path(root)
        self.gitignore = Path(gitignore) if gitignore is not None else None   # created with "*" on first save

    @classmethod
    def for_workspace(cls, workspace: str | os.PathLike) -> "SessionStore":
        base = Path(workspace).expanduser().resolve() / ".agent_v3"
        return cls(base / "sessions", gitignore=base / ".gitignore")

    def session_dir(self, session_id: str) -> Path:
        return self.root / session_id

    def events_path(self, session_id: str) -> Path:
        return self.root / session_id / EVENTS_FILE

    def read_events(self, session_id: str, after_seq: int = 0, limit: int | None = None) -> tuple[list[dict], bool]:
        """The saved events with `seq > after_seq`, in log order, at most `limit` of them, and whether that reached
        the end of the log (§7.2 `get_session_events`). Reads without the lock; a torn last line is skipped.

        Raises SessionNotFound for an unknown id or a folder with no event log.
        """
        path = self._existing_dir(session_id) / EVENTS_FILE
        if not path.is_file():
            raise SessionNotFound(f"Session {session_id} has no saved events.")
        events: list[dict] = []
        for d in read_jsonl(path):
            seq = d.get("seq") if isinstance(d, dict) else None
            if not isinstance(seq, int) or isinstance(seq, bool) or seq <= after_seq or d.get("type") == "text_delta":
                continue
            if limit is not None and len(events) >= limit:
                return events, False
            events.append(d)
        return events, True

    def list(self, limit: int | None = None) -> list[SessionInfo]:
        """Every session (or the `limit` newest), newest `updated` first."""
        rows = sorted(self._metas(), key=lambda pair: str(pair[1].get("updated") or ""), reverse=True)
        if limit is not None:
            rows = rows[:limit]
        return [_info(sid, meta, self._status(sid, meta)) for sid, meta in rows]

    def resolve(self, ref: str) -> str:
        """A full id, a unique prefix (at least 4 characters after `s_`, which is optional) or "latest"."""
        ref = ref.strip().lower()
        if ref == "latest":
            rows = self.list(limit=1)
            if not rows:
                raise SessionNotFound("There are no saved sessions in this workspace.")
            return rows[0].session_id
        body = ref[2:] if ref.startswith("s_") else ref
        if len(body) < MIN_REF_CHARS:
            raise SessionNotFound(f"Session reference {ref!r} is too short: "
                                  f"type at least {MIN_REF_CHARS} characters of the id.")
        matches = [sid for sid in self._ids() if sid[2:].startswith(body)]
        if not matches:
            raise SessionNotFound(f"No saved session matches {ref!r}.")
        if len(matches) > 1:
            raise AmbiguousSession(ref, matches)
        return matches[0]

    def load(self, session_id: str) -> SavedSession:
        """Read a saved session without taking its lock."""
        saved, _ = self._load(session_id, probe=True)
        return saved

    def create(self, session_id: str, config: AgentConfig) -> "SessionRecorder":
        """A recorder for a new session. The folder and lock are created at the first `turn_started`."""
        return SessionRecorder(self, session_id, _new_meta(session_id, config), new=True)

    def open(self, session_id: str, config: AgentConfig | None = None) -> tuple[SavedSession, "SessionRecorder"]:
        """Take the session's lock and return it with a recorder that appends to its logs.

        `config` is the resumed session's config; meta.json records its settings from the next save on.
        Raises SessionNotFound or SessionInUse. If the folder cannot be written, the recorder starts disabled.
        """
        folder = self._existing_dir(session_id)
        lock = error = None
        try:
            lock = _take_lock(folder / LOCK_FILE)
        except _Locked:
            raise SessionInUse(session_id, self._owner_pid(session_id)) from None
        except OSError as e:
            error = e
        try:
            if lock is not None:
                for name in (EVENTS_FILE, HISTORY_FILE):
                    repair_tail(folder / name)
            saved, meta = self._load(session_id, probe=False)
        except BaseException:
            if lock is not None:
                lock.close()
            raise
        recorder = SessionRecorder(self, session_id, meta, lock=lock, since_reset=bool(saved.turn_lines))
        if error is not None:
            recorder._disable(error)
        else:
            recorder._safely(recorder._attach, config)
        return saved, recorder

    def delete(self, session_id: str) -> None:
        """Remove one session's folder. Raises SessionInUse while it is open anywhere.

        Everything but the lock file is removed while the lock is held, so no other process can open the session
        halfway through. A lock file or folder that cannot be removed afterwards is left behind: with no logs it
        is no longer a session (not listed, not loadable).
        """
        folder = self._existing_dir(session_id)
        try:
            lock = _take_lock(folder / LOCK_FILE)
        except _Locked:
            raise SessionInUse(session_id, self._owner_pid(session_id)) from None
        try:
            for path in folder.iterdir():
                if path.name != LOCK_FILE:
                    _retry(shutil.rmtree if path.is_dir() else os.unlink, path)
        except OSError as e:
            raise SessionStoreError(f"Could not delete session {session_id}: {e}") from e
        finally:
            lock.close()                                # Windows cannot delete an open file
        try:
            _retry((folder / LOCK_FILE).unlink)         # a status probe in another process can hold it briefly
            folder.rmdir()
        except OSError:
            pass

    # -- internals -----------------------------------------------------------------------------

    def _ids(self) -> list[str]:
        try:
            return sorted(p.name for p in self.root.iterdir() if SESSION_ID_RE.fullmatch(p.name) and p.is_dir())
        except OSError:
            return []

    def _existing_dir(self, session_id: str) -> Path:
        folder = self.session_dir(session_id)
        if not SESSION_ID_RE.fullmatch(session_id or "") or not folder.is_dir():
            raise SessionNotFound(f"No saved session {session_id}.")
        return folder

    def _metas(self) -> list[tuple[str, dict]]:
        out = []
        for sid in self._ids():
            meta = _read_meta(self.session_dir(sid), sid)
            if meta is None:
                logs = self._read_logs(sid)
                meta = _meta_from_logs(sid, *logs) if logs[0] or logs[1] else None
            if meta is not None:
                out.append((sid, meta))
        return out

    def _read_logs(self, sid: str) -> tuple[list[dict], list[dict]]:
        folder = self.session_dir(sid)
        return _read_lines(folder / EVENTS_FILE), _read_lines(folder / HISTORY_FILE)

    def _status(self, sid: str, meta: dict) -> str:
        """Probe the lock without creating it: listing writes nothing."""
        try:
            _FileLock(self.session_dir(sid) / LOCK_FILE, create=False).close()
        except _Locked:
            return "in_use"
        except OSError:
            pass                                        # no lock file, or a read-only folder: nobody holds it
        return "interrupted" if meta.get("active_turn") else "idle"

    def _owner_pid(self, sid: str) -> int | None:
        pid = (_read_meta(self.session_dir(sid), sid) or {}).get("owner_pid")
        return pid if isinstance(pid, int) and not isinstance(pid, bool) else None

    def _load(self, sid: str, *, probe: bool) -> tuple[SavedSession, dict]:
        folder = self._existing_dir(sid)
        events, lines = self._read_logs(sid)
        if not events and not lines:
            raise SessionNotFound(f"Session {sid} has no saved events.")
        rebuilt = _meta_from_logs(sid, events, lines)
        meta = _read_meta(folder, sid)
        if meta is None or meta.get("turns") != rebuilt["turns"]:   # missing, corrupt, or behind the logs
            meta = rebuilt
        else:                                                        # the logs are the source of truth for these
            meta = {**meta, **{k: rebuilt[k] for k in ("turn_no", "last_seq", "active_turn")}}
        last_reset = max((i for i, line in enumerate(lines) if line.get("kind") == "reset"), default=-1)
        interrupted = _interrupted(events, lines)
        status = "interrupted" if interrupted else "idle"
        if probe and self._status(sid, {}) == "in_use":
            status = "in_use"
        info = _info(sid, meta, status)
        saved = SavedSession(
            info=info, turn_lines=[line for line in lines[last_reset + 1:] if line.get("kind") == "turn"],
            all_turn_lines=rebuilt["turns"], turn_no=meta["turn_no"], last_seq=meta["last_seq"],
            totals=meta["totals"].to_dict(), interrupted=interrupted,
            saved_config={"model": info.model, "reasoning": info.reasoning, "approval": str(meta.get("approval") or ""),
                          "prune_history": bool(meta.get("prune_history", True))})
        return saved, meta


# -- recorder ----------------------------------------------------------------------------------

class SessionRecorder:
    """Writes one session's events, history and meta (§4.2). Built by `SessionStore.create` / `open`.

    Every call arrives under the Session lock. An OSError (or any other error, so a recorder bug cannot fail a
    turn either) disables the recorder: `error` then names the folder and the problem, and later calls do
    nothing (§5.4). `Session` reports it once.
    """

    def __init__(self, store: SessionStore, session_id: str, meta: dict, *, new: bool = False,
                 lock: _FileLock | None = None, since_reset: bool = False):
        self.store = store
        self.session_id = session_id
        self.dir = store.session_dir(session_id)
        self.error: str | None = None
        self._meta = meta
        self._lock = lock
        self._pending: list[dict] | None = [] if new else None   # a new session buffers until its first turn
        self._events_f = self._history_f = None
        self._since_reset = since_reset          # a turn line exists after the last reset
        self._closed = False

    @property
    def healthy(self) -> bool:
        return self.error is None and not self._closed

    def on_event(self, event: Event) -> None:
        """Append the event (except `text_delta`); update meta.json at turn start and end."""
        if event.type != "text_delta":
            self._safely(self._on_event, event)

    def on_commit(self, *, turn_id: str, outcome: str, user_message: str, text: str, items: list,
                  record: list | None, stats: dict | None = None) -> None:
        """Write and fsync the history line, before the turn's terminal event is emitted.

        `stats` is only for a turn that gets no terminal event (an interrupted turn recovered on resume):
        its logged costs are added to the totals here (§5.3 step 3).
        """
        self._safely(self._on_commit, turn_id, outcome, user_message, text, items, record, stats)

    def on_reset(self) -> None:
        """Write a reset line, but only if a turn line exists since the last one."""
        if self._since_reset:
            self._safely(self._on_reset)

    def close(self) -> None:
        """Close the files, then release the lock. Safe to call twice."""
        if self._closed:
            return
        self._closed = True
        for f in (self._events_f, self._history_f):
            if f is not None:
                try:
                    f.close()
                except OSError:
                    pass
        if self._lock is not None:
            self._lock.close()

    # -- internals -----------------------------------------------------------------------------

    def _safely(self, fn, *args) -> None:
        if not self.healthy:
            return
        try:
            fn(*args)
        except Exception as e:
            self._disable(e)

    def _disable(self, e: Exception) -> None:
        self.error = f"could not save session {self.session_id} to {self.dir}: {e}"

    def _on_event(self, event: Event) -> None:
        d = event.to_dict()
        if self._pending is not None and event.type != "turn_started":
            self._pending.append(d)
            return
        self._ensure_files()
        self._write_event(d)

    def _on_commit(self, turn_id, outcome, user_message, text, items, record, stats) -> None:
        items = jsonable(items)
        record = None if record is None else jsonable(record)
        line = {"v": FORMAT_VERSION, "kind": "turn", "turn_id": turn_id, "outcome": outcome, "ts": now_iso(),
                "model": self._meta.get("model") or "",       # the model whose items these are (restore, §5.2)
                "prune_history": bool(self._meta.get("prune_history", True)),   # for a meta rebuilt from the logs
                "web_search_fee_usd": self._meta.get("web_search_fee_usd"),     # prices its searches in a rebuild
                "user_message": user_message, "text": text, "items": items,
                "record": None if record == items else record}
        self._ensure_files()
        append_line(self._history_f, line, fsync=True)
        self._since_reset = True
        m = self._meta
        m["turns"] += 1
        m["turn_no"] = max(m["turn_no"], _turn_number(turn_id))
        if stats:
            m["totals"].add(TurnStats.from_dict(stats))
        if outcome == "interrupted":             # no terminal event follows, so save the meta now
            if m["active_turn"] == turn_id:
                m["active_turn"] = None
            m["updated"] = line["ts"]
            self._write_meta()

    def _on_reset(self) -> None:
        self._ensure_files()
        append_line(self._history_f, {"v": FORMAT_VERSION, "kind": "reset", "ts": now_iso()}, fsync=True)
        self._since_reset = False

    def _attach(self, config: AgentConfig | None) -> None:
        """An existing session opened by this process: record the owner pid, then the new settings."""
        self._open_logs()
        self._meta["owner_pid"] = os.getpid()
        self._write_meta()
        if config is not None:                   # saved from the next turn on, so a bare open changes nothing
            self._meta.update(_settings(config))

    def _ensure_files(self) -> None:
        if self._pending is None:
            return
        self._create_folder()
        pending, self._pending = self._pending, None
        for d in pending:
            self._write_event(d)

    def _create_folder(self) -> None:
        gitignore = self.store.gitignore
        if gitignore is not None:
            gitignore.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                fd = os.open(gitignore, os.O_WRONLY | os.O_CREAT | os.O_EXCL | _O_BINARY, 0o644)
            except FileExistsError:
                pass                             # never overwrite the user's file
            else:
                with os.fdopen(fd, "wb") as f:
                    f.write(b"*\n")
        self.store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.dir.mkdir(mode=0o700)               # exist_ok=False: a new id never reuses a folder
        self._lock = _FileLock(self.dir / LOCK_FILE)
        self._open_logs()

    def _open_logs(self) -> None:
        self._events_f = _open_append(self.dir / EVENTS_FILE)
        self._history_f = _open_append(self.dir / HISTORY_FILE)

    def _write_event(self, d: dict) -> None:
        append_line(self._events_f, d)
        m = self._meta
        m["last_seq"] = max(m["last_seq"], d["seq"])
        m["created"] = m["created"] or d["ts"]
        if d["type"] == "turn_started":
            m["active_turn"] = d["turn_id"]
            m["turn_no"] = max(m["turn_no"], _turn_number(d["turn_id"]))
            m["title"] = m["title"] or session_title(d["user_message"])
        elif d["type"] in TERMINAL_EVENTS:
            m["totals"].add(TurnStats.from_dict(d.get("stats")))
            if m["active_turn"] == d["turn_id"]:
                m["active_turn"] = None
        elif d["type"] == "config_changed":
            # The later turn lines are tagged with these (restore, §5.2), and a resume restores the last-used model
            # and reasoning (option C). `updated` follows turns only, as in a meta rebuilt from the logs.
            config = d.get("config") or {}
            m.update({k: config[k] for k in ("model", "reasoning", "approval") if isinstance(config.get(k), str)})
            self._write_meta()
            return
        else:
            return
        m["updated"] = d["ts"]
        self._write_meta()

    def _write_meta(self) -> None:
        """Replace meta.json atomically. On Windows a reader can block os.replace: retry, then skip (it is a cache)."""
        m = self._meta
        m["cost_usd"] = m["totals"].cost_usd
        data = json.dumps({**m, "totals": m["totals"].to_dict()}, ensure_ascii=False, indent=1).encode("utf-8")
        path, tmp = self.dir / META_FILE, self.dir / f".{META_FILE}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | _O_BINARY, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            _retry(os.replace, tmp, path)
        except PermissionError:
            try:
                tmp.unlink()
            except OSError:
                pass


# -- helpers -----------------------------------------------------------------------------------

def _take_lock(path: Path) -> _FileLock:
    """`_FileLock`, retried for ~100 ms: `list()` and `load()` in another process probe locks for a moment."""
    for _ in range(_LOCK_TRIES - 1):
        try:
            return _FileLock(path)
        except _Locked:
            time.sleep(_LOCK_PAUSE_S)
    return _FileLock(path)


def _retry(fn, *args) -> None:
    """Call `fn`, retrying a PermissionError: on Windows another process reading the file blocks it briefly."""
    for _ in range(_REPLACE_TRIES - 1):
        try:
            fn(*args)
            return
        except PermissionError:
            time.sleep(_REPLACE_PAUSE_S)
    fn(*args)


def _open_append(path: Path):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _O_BINARY, 0o600)
    return os.fdopen(fd, "ab")


def _read_lines(path: Path) -> list[dict]:
    try:
        return [d for d in read_jsonl(path) if isinstance(d, dict)]
    except FileNotFoundError:
        return []


def _settings(config: AgentConfig) -> dict:
    return {"workspace": str(config.workspace), "model": config.model, "reasoning": config.reasoning,
            "approval": config.approval, "prune_history": config.prune_history,
            "web_search_fee_usd": config.web_search_fee_usd}


def _new_meta(sid: str, config: AgentConfig) -> dict:
    return {"v": FORMAT_VERSION, "session_id": sid, "title": "", "created": "", "updated": "", "turns": 0,
            "cost_usd": 0.0, **_settings(config), "turn_no": 0, "last_seq": 0, "active_turn": None,
            "owner_pid": os.getpid(), "totals": TurnStats()}


def _read_meta(folder: Path, sid: str) -> dict | None:
    """meta.json if it is readable and well-formed (`totals` as a TurnStats), else None (rebuilt from the logs)."""
    try:
        meta = json.loads((folder / META_FILE).read_bytes())
    except (OSError, ValueError):
        return None
    if not isinstance(meta, dict) or meta.get("session_id") != sid or not isinstance(meta.get("totals"), dict):
        return None
    for key, kind in (("turns", int), ("turn_no", int), ("last_seq", int), ("cost_usd", (int, float)),
                      ("title", str), ("updated", str), ("created", str)):
        if not isinstance(meta.get(key), kind) or isinstance(meta.get(key), bool):
            return None
    return {**meta, "totals": TurnStats.from_dict(meta["totals"])}


def _info(sid: str, meta: dict, status: str) -> SessionInfo:
    return SessionInfo(session_id=sid, title=meta["title"], created=meta["created"], updated=meta["updated"],
                       turns=meta["turns"], cost_usd=float(meta["cost_usd"]), model=str(meta.get("model") or ""),
                       reasoning=str(meta.get("reasoning") or ""), status=status)


def _turn_number(turn_id) -> int:
    m = re.fullmatch(r"t(\d+)", turn_id) if isinstance(turn_id, str) else None
    return int(m.group(1)) if m else 0


def _interrupted(events: list[dict], lines: list[dict]) -> InterruptedTurn | None:
    """The last started turn, if history.jsonl has no line for it (§5.3)."""
    committed = {line.get("turn_id") for line in lines if line.get("kind") == "turn"}
    starts = [i for i, e in enumerate(events) if e.get("type") == "turn_started"]
    if not starts:
        return None
    start = events[starts[-1]]
    turn_id = start.get("turn_id")
    if not isinstance(turn_id, str) or turn_id in committed:
        return None
    return InterruptedTurn(turn_id=turn_id, user_message=str(start.get("user_message") or ""),
                           events=[e for e in events[starts[-1]:] if e.get("turn_id") == turn_id])


def _logged_stats(events: list[dict], turn_id: str, web_fee_usd: float) -> dict:
    """The stats a turn without a terminal event left in the log (its rounds were billed), counted as live."""
    counter = StatsCounter(web_fee_usd)
    for d in events:
        if d.get("turn_id") == turn_id:
            try:
                counter.observe(event_from_dict(d))
            except (TypeError, ValueError):
                continue                         # a line from another version; the rest still counts
    return counter.stats.to_dict()


def _line_setting(line: dict | None, name: str, kind, default):
    """A setting tagged on a turn line, or `default` for a line without it (or no line)."""
    value = (line or {}).get(name)
    return value if isinstance(value, kind) and (kind is bool or not isinstance(value, bool)) else default


def _meta_from_logs(sid: str, events: list[dict], lines: list[dict]) -> dict:
    """Rebuild meta.json from the two logs (owner_pid is unknown). Totals are summed in commit order, as live."""
    config: dict = {}
    title = created = updated = ""
    turn_no = last_seq = 0
    ended: dict = {}                             # turn_id -> its terminal event's stats
    for e in events:
        seq, ts, turn_id = e.get("seq"), str(e.get("ts") or ""), e.get("turn_id")
        if isinstance(seq, int):
            last_seq = max(last_seq, seq)
        created = created or ts
        turn_no = max(turn_no, _turn_number(turn_id))
        kind = e.get("type")
        if kind in ("session_started", "config_changed") and isinstance(e.get("config"), dict):
            config.update(e["config"])
        elif kind == "turn_started":
            title = title or session_title(str(e.get("user_message") or ""))
            updated = max(updated, ts)
        elif kind in TERMINAL_EVENTS:
            ended[turn_id] = e.get("stats")
            updated = max(updated, ts)
    totals = TurnStats()
    turn_lines = [line for line in lines if line.get("kind") == "turn"]
    for line in turn_lines:                      # `updated` follows the recorder: turn start and end only
        turn_id = line.get("turn_id")
        turn_no = max(turn_no, _turn_number(turn_id))
        if turn_id in ended:
            totals.add(TurnStats.from_dict(ended[turn_id]))
        else:                                    # interrupted, or the process died between commit and terminal event
            fee = _line_setting(line, "web_search_fee_usd", (int, float), AgentConfig.web_search_fee_usd)
            totals.add(TurnStats.from_dict(_logged_stats(events, turn_id, fee)))
            updated = max(updated, str(line.get("ts") or ""))
    last_line = turn_lines[-1] if turn_lines else None
    interrupted = _interrupted(events, lines)
    return {"v": FORMAT_VERSION, "session_id": sid, "title": title, "workspace": str(config.get("workspace") or ""),
            "created": created, "updated": updated, "turns": len(turn_lines), "cost_usd": totals.cost_usd,
            "model": str(config.get("model") or ""), "reasoning": str(config.get("reasoning") or ""),
            "approval": str(config.get("approval") or ""),
            "prune_history": _line_setting(last_line, "prune_history", bool, True),
            "web_search_fee_usd": _line_setting(last_line, "web_search_fee_usd", (int, float),
                                                AgentConfig.web_search_fee_usd),
            "turn_no": turn_no, "last_seq": last_seq, "active_turn": interrupted.turn_id if interrupted else None,
            "owner_pid": None, "totals": totals}
