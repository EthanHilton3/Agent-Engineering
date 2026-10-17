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
from .events import Event, jsonable, now_iso
from .jsonl import append_line, read_jsonl, repair_tail

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
    totals: dict
    prune_history: bool
    model: str
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

    def __init__(self, path: Path):
        self.fd: int | None = os.open(path, os.O_RDWR | os.O_CREAT | _O_BINARY, 0o600)
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
            lock = _FileLock(folder / LOCK_FILE)
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
        """Remove one session's folder. Raises SessionInUse while it is open anywhere."""
        folder = self._existing_dir(session_id)
        try:
            lock = _FileLock(folder / LOCK_FILE)
        except _Locked:
            raise SessionInUse(session_id, self._owner_pid(session_id)) from None
        lock.close()                                    # Windows cannot delete an open file
        shutil.rmtree(folder)

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
        try:
            _FileLock(self.session_dir(sid) / LOCK_FILE).close()
        except _Locked:
            return "in_use"
        except OSError:
            pass                                        # e.g. a read-only folder: nobody can hold it either
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
            totals=_rounded(meta["totals"]), prune_history=bool(meta.get("prune_history", True)), model=info.model,
            interrupted=interrupted,
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
                "user_message": user_message, "text": text, "items": items,
                "record": None if record == items else record}
        self._ensure_files()
        append_line(self._history_f, line, fsync=True)
        self._since_reset = True
        m = self._meta
        m["turns"] += 1
        m["turn_no"] = max(m["turn_no"], _turn_number(turn_id))
        if stats:
            _add_stats(m["totals"], stats)
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
            _add_stats(m["totals"], d.get("stats"))
            if m["active_turn"] == d["turn_id"]:
                m["active_turn"] = None
        else:
            return
        m["updated"] = d["ts"]
        self._write_meta()

    def _write_meta(self) -> None:
        """Replace meta.json atomically. On Windows a reader can block os.replace: retry, then skip (it is a cache)."""
        m = self._meta
        m["cost_usd"] = _cost(m["totals"])
        data = json.dumps({**m, "totals": _rounded(m["totals"])}, ensure_ascii=False, indent=1).encode("utf-8")
        path, tmp = self.dir / META_FILE, self.dir / f".{META_FILE}.tmp"
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | _O_BINARY, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        for attempt in range(_REPLACE_TRIES):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt + 1 < _REPLACE_TRIES:
                    time.sleep(_REPLACE_PAUSE_S)
        try:
            tmp.unlink()
        except OSError:
            pass


# -- helpers -----------------------------------------------------------------------------------

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
            "approval": config.approval, "prune_history": config.prune_history}


def _new_meta(sid: str, config: AgentConfig) -> dict:
    return {"v": FORMAT_VERSION, "session_id": sid, "title": "", "created": "", "updated": "", "turns": 0,
            "cost_usd": 0.0, **_settings(config), "turn_no": 0, "last_seq": 0, "active_turn": None,
            "owner_pid": os.getpid(), "totals": {}}


def _read_meta(folder: Path, sid: str) -> dict | None:
    """meta.json if it is readable and well-formed, else None (the caller rebuilds it from the logs)."""
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
    return meta


def _info(sid: str, meta: dict, status: str) -> SessionInfo:
    return SessionInfo(session_id=sid, title=meta["title"], created=meta["created"], updated=meta["updated"],
                       turns=meta["turns"], cost_usd=float(meta["cost_usd"]), model=str(meta.get("model") or ""),
                       reasoning=str(meta.get("reasoning") or ""), status=status)


def _turn_number(turn_id) -> int:
    m = re.fullmatch(r"t(\d+)", turn_id) if isinstance(turn_id, str) else None
    return int(m.group(1)) if m else 0


def _add_stats(totals: dict, stats) -> None:
    if isinstance(stats, dict):
        for k, v in stats.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                totals[k] = totals.get(k, 0) + v


def _rounded(totals: dict) -> dict:
    """Same rounding as TurnStats.to_dict."""
    return {k: round(v, 6 if k.endswith("_usd") else 3) if isinstance(v, float) else v for k, v in totals.items()}


def _cost(totals: dict) -> float:
    return round(totals.get("model_cost_usd", 0) + totals.get("web_cost_usd", 0), 6)


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


def _logged_stats(events: list[dict], turn_id: str) -> dict:
    """The costs and counts a turn without a terminal event left in the log (its rounds were billed)."""
    s = dict.fromkeys(("rounds", "tool_calls", "web_searches", "web_opens", "web_finds", "input_tokens",
                       "cached_tokens", "output_tokens", "reasoning_tokens"), 0)
    s.update(model_cost_usd=0.0, web_cost_usd=0.0, model_wait_s=0.0, approval_wait_s=0.0)
    web_keys = {"search": "web_searches", "open_page": "web_opens", "find_in_page": "web_finds"}
    for e in events:
        if e.get("turn_id") != turn_id:
            continue
        kind = e.get("type")
        if kind == "model_round_completed":
            s["rounds"] += 1
            for k in ("input_tokens", "cached_tokens", "output_tokens", "reasoning_tokens"):
                s[k] += e.get(k) or 0
            s["model_cost_usd"] += e.get("cost_usd") or 0.0
            s["model_wait_s"] += e.get("duration_s") or 0.0
        elif kind == "tool_started":
            s["tool_calls"] += 1
        elif kind == "web_action" and e.get("kind") in web_keys:
            s[web_keys[e["kind"]]] += 1
        elif kind == "approval_resolved":
            s["approval_wait_s"] += e.get("wait_s") or 0.0
    s["web_cost_usd"] = s["web_searches"] * AgentConfig.web_search_fee_usd
    return s


def _meta_from_logs(sid: str, events: list[dict], lines: list[dict]) -> dict:
    """Rebuild meta.json from the two logs (owner_pid is unknown)."""
    config: dict = {}
    title = created = updated = ""
    turn_no = last_seq = 0
    totals: dict = {}
    ended = set()
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
            _add_stats(totals, e.get("stats"))
            ended.add(turn_id)
            updated = max(updated, ts)
    turn_lines = [line for line in lines if line.get("kind") == "turn"]
    for line in turn_lines:                      # `updated` follows the recorder: turn start and end only
        turn_no = max(turn_no, _turn_number(line.get("turn_id")))
        if line.get("outcome") == "interrupted" and line.get("turn_id") not in ended:
            _add_stats(totals, _logged_stats(events, line["turn_id"]))
            updated = max(updated, str(line.get("ts") or ""))
    interrupted = _interrupted(events, lines)
    prune = config.get("prune_history")
    if not isinstance(prune, bool):              # not in the config summary: a kept `record` means it was off
        prune = not any(line.get("record") is not None for line in turn_lines)
    return {"v": FORMAT_VERSION, "session_id": sid, "title": title, "workspace": str(config.get("workspace") or ""),
            "created": created, "updated": updated, "turns": len(turn_lines), "cost_usd": _cost(totals),
            "model": str(config.get("model") or ""), "reasoning": str(config.get("reasoning") or ""),
            "approval": str(config.get("approval") or ""), "prune_history": prune, "turn_no": turn_no,
            "last_seq": last_seq, "active_turn": interrupted.turn_id if interrupted else None, "owner_pid": None,
            "totals": totals}
