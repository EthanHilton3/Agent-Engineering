# Agent V3 — Saved Sessions Spec

*Written 2026-10-16. Extends `agent_v3_claude_plan.md` (called "the v3 spec" below). Section numbers like v3 §8.4 refer to it.*

**How to use this document.** Read the owner decisions and §1–§3 first. Then read only the section for the phase you are implementing (§10). If you are an AI agent implementing this, do one phase per session and run the whole suite before you stop (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`). Do not build anything listed in §12. Do not change `PROTOCOL_VERSION`.

---

## Owner decisions (2026-10-16)

The five open questions from the first draft are settled. The rest of this spec follows them.

- **Retention (was Q1).** Sessions are kept and never deleted automatically or in bulk. There is no `prune` command. The only deletion paths are explicit, one session at a time (`sessions delete REF`, `delete_session`), plus removing the folder by hand. They stay because sessions can contain secrets, so a user must be able to remove one (§9).
- **`--no-save` (was Q2).** Added on both the CLI and the server.
- **`/new` (was Q3).** `/new` always starts a new session (new id and banner), saved unless `--no-save` is set. The CLI has no command that clears history inside a session; there is no `/clear`. The server's `new_conversation` keeps its frozen v1 meaning (clear history, same id, reset line §4.3), and the new `new_session` message gives apps the CLI behaviour.
- **GUI-readiness additions (2026-10-16).** Listing shows every session by default (§4.5). Model, reasoning and approval can be changed between turns without losing the conversation (§5.6, D8). Apps can fetch a saved session's full event log to redraw it (`get_session_events`, §7.2). Listing across workspaces stays out of scope (§12).
- **Settings on resume (was Q4, option C).** A resumed session gets back its saved `model` and `reasoning` unless they are passed on the command line. The approval mode is **never** restored: it is always the launch flag or the default (§5.1).
- **Tool output on disk (was Q5).** Saved in full: every `tool_completed.output`, every tool's arguments and every approval diff, including `metadata.full_content`. The log then shows exactly what the model saw, for debugging and UI replay. Accepted cost: anything sensitive the agent reads, or a command prints, is kept in plain text inside `.agent_v3/sessions/` (§9), which is git-ignored and can be deleted per session, or avoided with `--no-save`.

---

## 1. Goals and non-goals

1. **Every session is saved automatically.** The CLI and the stdio server save every session to disk as it runs. No flag is needed, and a crash loses at most a torn last line.
2. **List and resume.** A user can list past sessions for a workspace and resume one. The model then continues with the same conversation history it would have had if the process had never stopped.
3. **Transcripts on demand.** `--transcript` is removed. A Markdown transcript is rebuilt from the saved event log whenever it is asked for (`/export` and `python -m agent_v3 export`), using `TranscriptWriter`'s existing replay ability.
4. **The core stays UI-agnostic.** Storage lives in a new core module, `agent_v3/sessions.py`, which `Session` uses. Frontends only choose which store to pass in. `cli.py` contains no file-format code.
5. **The protocol changes only additively.** `PROTOCOL_VERSION` stays 1. A v1 client that never sends the new messages, and does not start the server with `--resume` or `--continue`, sees the same event sequence as today. The only difference is the new files on disk.
6. **Settings change mid-session.** `/model`, `/reasoning` and `/approval` (and the server's `set_config`) change the open session between turns. The conversation, session id and log stay the same.
7. **Ready for a GUI.** Everything above is reachable through the stdio protocol, including a saved session's full event log, so an app can list, open, redraw and reconfigure sessions without the CLI.

**Non-goals:** syncing sessions between machines, search inside sessions, branching or forking, model-written titles, and server-side state (`previous_response_id`; v3 §13 still applies). See §12.

---

## 2. Decisions at a glance

| # | topic | decision | where |
|---|---|---|---|
| D1 | location and format | `<workspace>/.agent_v3/sessions/<id>/` holding `events.jsonl` (append-only), `history.jsonl` (append-only, one line per commit) and `meta.json` (a cache, replaced atomically). `.agent_v3/.gitignore` contains `*`. | §4 |
| D2 | restored vs rebuilt | Restored: history, turn counter, `seq`, usage totals. Rebuilt fresh: system prompt, cache key, `FileState`, approval allowances. | §5.2 |
| D3 | interrupted turn | Recovered on resume. The user message plus an "interrupted after: <activity>" note go into history, with the activity rebuilt from the logged events. Logged round costs are added to the totals, and a `notice` is shown. | §5.3 |
| D4 | ids, titles, listing | Ids keep the existing `s_<12 hex>` format, and any unique prefix is accepted. The title is the first user message. Listing reads `meta.json`. Sessions are kept indefinitely. | §4.4, §4.5 |
| D5 | concurrency | One OS-level lock per session (`msvcrt.locking` / `fcntl.flock`) on `<id>/lock`, held while the `Session` is open. The OS releases it when the process dies, so there are no stale lock files. | §4.6 |
| D6 | bench | `Session` saves only when it is given a store. The bench passes none, so it writes nothing, and the workdir and the session list stay clean. | §8 |
| D7 | secrets | Everything the model saw or did is stored as plain text in the workspace and ignored by git. It is never deleted automatically; it is deleted one session at a time with `sessions delete` / `delete_session`, or by removing the folder. `--no-save` turns saving off. | §9 |
| D8 | settings mid-session | `Session.update_config(model=, reasoning=, approval=)`, between turns, **in place**: same id, history, log and lock. It rebuilds the system prompt and cache key when the approval mode changes, clears "allow for session" approvals on an approval change, and emits `config_changed`. | §5.6 |

---

## 3. Architecture and file layout

`Session` writes through a `SessionRecorder`. `_emit` calls `on_event`; `_commit`, `_fail` and `cancel()` call `on_commit` before their terminal event; `new_conversation` calls `on_reset`. The frontends (`cli.py`, `commands.py`, `stdio_server.py`) use `SessionStore` to list, resolve, export and delete sessions, and pass it to `Session`. New and changed files:

```text
agent_v3/
  jsonl.py             NEW   append_line(), read_jsonl() (skips a torn last line), repair_tail()
  sessions.py          NEW   SessionStore, SessionRecorder, SessionInfo, SavedSession, errors, locking
  stats.py             NEW   TurnStats and StatsCounter, shared by session.py and sessions.py (S1–S2 review)
  events.py            +     SessionResumed and ConfigChanged events, event_from_dict()
  session.py           +     store=/resume= parameters, recorder hooks, restore, interrupted-turn recovery, update_config()
  model.py             +     ModelAdapter.set_config()
  frontends/
    eventlog.py        ~     read_events re-exported from jsonl.read_jsonl (EventLogWriter unchanged)
    transcript.py      +     export_transcript(); a repeated session_started becomes a "RESUMED" line
    args.py            +     add_session_args(): --resume [REF], --continue/-c, --no-save
    cli.py             ~     --transcript removed; /sessions [all] /resume /export /model /reasoning /approval; /new = new session; exit hint
    commands.py        NEW   `sessions` and `export` subcommands (dispatched from cli.main)
    stdio_server.py    +     new messages (§7), including set_config and get_session_events; the session object is swappable
tests/
  test_sessions_store.py NEW, test_session_resume.py NEW, test_session_settings.py NEW, test_cli_sessions.py NEW; additions in test_stdio_server.py
```

The core (`sessions.py`, `jsonl.py`) imports nothing from `frontends/`. `read_events` moves to the core as `jsonl.read_jsonl`, and `frontends/eventlog.py` re-exports it under the old name, so existing imports keep working. No new dependencies.

---

## 4. Storage

### 4.1 Location (D1)

**Decision:** sessions live in `<workspace>/.agent_v3/sessions/<session_id>/`.

**Why not a per-user folder** (`~/.agent_v3/sessions/<workspace hash>/`):
- "This workspace" comes for free: `--continue` and `/sessions` are per workspace by construction, with no path hashing or Windows case/symlink normalisation.
- It sits next to `<workspace>/.agent_v3/outputs/` (the full command logs), so one folder holds everything the agent wrote, and deleting the workspace deletes its sessions.
- `.agent_v3` is already in `IGNORED_DIRS`, so `glob_files`, `search_text` and the other walks never surface the agent's own logs.

**Costs and mitigations:**
- **Git.** `.agent_v3/` is ignored only in *this* repo. On first save the store creates `.agent_v3/.gitignore` containing `*`, as `.pytest_cache` does (`O_EXCL`; an existing file is never overwritten).
- **Read-only workspaces.** Saving switches off with one `notice` (§5.4), and the session continues.
- **No listing across workspaces.** Out of scope (§12).

### 4.2 Files in a session folder

| file | written | content | source of truth? |
|---|---|---|---|
| `events.jsonl` | Appended per event, flushed per line (no fsync). | Every event's `to_dict()` **except `text_delta`**, which `turn_completed.text` already contains. The deltas would make the file about 10× larger, and replay does not need them. So `seq` has gaps on disk; on the wire it has none. | yes: transcript, turn summaries, interrupted-turn activity |
| `history.jsonl` | One line per commit, flushed and **fsync'd** before the turn's terminal event is emitted. | §4.3 | yes: what the model is given on resume |
| `meta.json` | Replaced atomically (`os.replace`) at `open()` (new `owner_pid`), at `turn_started`, at each terminal event, and when an interrupted turn is recovered. | §4.4 | **no**: a listing cache, rebuilt from the two logs if it is missing or unreadable |
| `lock` | Created on open. Its content is unused. | §4.6 | — |
| `transcript.md` | Only by `/export` with no path. | Markdown | no |

**Crash safety.**
- Both logs are append-only, so a crash leaves at most a torn last line, which `read_jsonl` skips (already tested for `read_events`). Before appending to an existing log, `repair_tail(path)` truncates it after its last `\n`; otherwise the next line would be glued onto the fragment and corrupted too.
- **Commit order:** history line (fsync) → terminal event → `meta.json`. If the history line is torn or missing, the turn counts as interrupted on resume (§5.3), which is the right outcome. If a history line exists without its `turn_completed`, the turn counts as committed, and its answer comes from the history line.
- **Windows:** `os.replace` onto `meta.json` can fail with `PermissionError` while another process reads it. Retry 5× with a 20 ms pause, then skip; the cache is rebuilt later.

### 4.3 `history.jsonl` lines

```json
{"v": 1, "kind": "turn", "turn_id": "t2", "outcome": "completed", "ts": "2026-10-16T14:03:09.120+00:00",
 "model": "gpt-6-luna", "prune_history": true, "web_search_fee_usd": 0.01,
 "user_message": "Now add a clear() method with a test.", "text": "Added Store.clear() and test_clear.",
 "items": [{"role": "user", "content": "Now add..."}, {"role": "assistant", "content": "Added..."},
           {"role": "developer", "content": "Turn record: read store.py; edited store.py (+3 −0) ..."}],
 "record": null}
{"v": 1, "kind": "reset", "ts": "2026-10-16T14:10:00.000+00:00"}
```

- `outcome` is one of `completed`, `cancelled`, `failed` or `interrupted`. `items` is exactly what `Session` appended to `self.history` at that commit.
- **Per-line settings** (S2 and the S1–S2 review). Each turn line records the settings it was made under:
  - `model` decides on restore whether this line's `items` may go back in full (§5.2).
  - `prune_history` and `web_search_fee_usd` let a `meta.json` rebuilt from the logs report the right setting and price searches with the session's fee.
  - A line without these fields falls back to `SessionInfo.model`, `prune_history=True` and `AgentConfig`'s default fee.
- `record` is the pruned triple (user / assistant / turn-record developer note). It is `null` when it equals `items`, which is always the case with `prune_history=True` and for cancel, fail and interrupted. With `prune_history=False`, `items` holds the whole turn: reasoning items with `encrypted_content`, `function_call`/`function_call_output` pairs and `web_search_call` items. `record` then holds the pruned form, so a resume can fall back to it (§5.2).
- `reset` is written by `new_conversation()`, and only if a turn line exists since the last reset. A resume restores only the lines after the last `reset`. Export shows everything.

### 4.4 `meta.json`, ids and titles (D4)

```json
{"v": 1, "session_id": "s_3f9a1c0b7d2e", "title": "Fix the failing test in test_store.py",
 "workspace": "C:\\work\\app", "created": "2026-10-15T16:58:02.114+00:00", "updated": "2026-10-15T17:20:41.530+00:00",
 "turns": 3, "cost_usd": 0.0123, "model": "gpt-6-luna", "reasoning": "medium", "approval": "ask",
 "prune_history": true, "web_search_fee_usd": 0.01,
 "turn_no": 3, "last_seq": 214, "active_turn": null, "owner_pid": 41236,
 "totals": {"rounds": 14, "tool_calls": 22, "...": "every TurnStats key"}}
```

- **Id.** The existing `s_` + 12 hex (48 bits) is kept, and the folder is created with `exist_ok=False`. Users type any unique prefix of at least 4 characters after `s_` (e.g. `--resume 3f9a`), the literal `latest`, or a list number from `/sessions` (CLI only). Why not a timestamp id: listings sort by `updated` anyway, and short random prefixes are easier to type.
- **Title.** Taken from the first `turn_started.user_message`: the first non-empty line, whitespace collapsed, clipped to 60 characters with `…`. It is never changed. Model-written titles would cost a request (§12).
- **Created lazily** at the first `turn_started`; until then the recorder buffers events (normally just `session_started`), so opening the CLI and quitting leaves nothing on disk. `cost_usd` = `model_cost_usd + web_cost_usd`; `turns` counts every turn line, across resets.

### 4.5 Listing and retention

`SessionStore.list()` reads each `meta.json` (O(sessions) small files), sorts by `updated`, newest first, and returns **every** session unless a `limit` is given. `status` is `in_use` if the lock cannot be taken, else `interrupted` if `active_turn` is set, else `idle`. In the server, the open session reports `current`.

CLI listing format (non-TTY uses ASCII and no colour, as everywhere else):

```text
  #  id            updated           turns    cost  title
  1  s_3f9a1c0b7d  2026-10-15 17:20      3  $0.012  Fix the failing test in test_store.py
  2  s_77e0d41a9c  2026-10-14 09:02      1  $0.003  What's the default timeout?  (interrupted)
```

**Listing everything.** `/sessions` shows the 10 most recent and ends with `… 14 more: /sessions all` when there are more. `/sessions all` and the `sessions` subcommand show every session (`--limit N` caps the subcommand). The server's `list_sessions` without `limit` returns all of them, and its reply carries `total`.

**Retention:** sessions are kept indefinitely. Nothing is deleted automatically, and there is no bulk or age-based delete. A typical session is 50 KB–2 MB, so growth is slow. Deletion is explicit and per session (§9).

### 4.6 Concurrency (D5)

**Decision:** a session can be open in at most one process.
- `SessionStore.open()` and `create()` open `<id>/lock` and take a non-blocking exclusive OS lock: `msvcrt.locking(fd, LK_NBLCK, 1)` on Windows, `fcntl.flock(fd, LOCK_EX | LOCK_NB)` on POSIX. The handle is kept until `Session.close()`.
- **Retry.** `open()` and `delete()` try the lock 5 times, 25 ms apart (about 100 ms), before giving up. This outlasts a momentary status probe from `list()` or `load()` in another process (below). A session that really is open therefore takes about 100 ms to report.
- Failure raises `SessionInUse(session_id, owner_pid)`, where `owner_pid` comes from `meta.json` and is shown only for information.
- **Status probes are read-only.** `list()` and `load()` find `in_use` by briefly locking an *existing* `lock` file; a missing `lock` file means "not in use", and nothing is created.

**Why OS locks rather than a pid file:** the OS releases the lock when the process dies, even on a hard kill, so there is never a stale lock to clean up. Checking whether a pid is alive is unsafe on Windows, where `os.kill(pid, 0)` calls `TerminateProcess`. Both lock kinds also conflict between two handles in the *same* process (Windows locks are per handle; `flock` is per open file description), so the conflict can be tested in-process.

**Other cases:**
- Two new sessions in one workspace never conflict, because they have different folders.
- `--continue` when the latest session is in use exits with "session s_… is open in another agent_v3 process (pid N); use --resume to pick another". It does not quietly pick an older session.
- `list`, `export` and `load` read without the lock. The logs are append-only, so a reader sees a consistent prefix.
- **`delete` order.** It takes the lock, so an in-use session cannot be deleted. It removes every file except `lock` *while still holding the lock*, so no other process can open the session halfway through. Then it releases the lock and removes `lock` and the folder.
  - That last step is best effort: a folder left holding only `lock` has no logs, so it is neither listed nor loadable.
  - A failure while the lock is held raises `SessionStoreError` naming the session, not a raw `OSError`.

---

## 5. Core changes

### 5.1 `sessions.py` and `Session` interfaces

```python
class SessionStoreError(Exception): ...
class SessionNotFound(SessionStoreError): ...
class AmbiguousSession(SessionStoreError): ...        # .matches: list[str]
class SessionInUse(SessionStoreError): ...            # (session_id, owner_pid: int | None)

@dataclass(frozen=True)
class SessionInfo:                                    # one listing row
    session_id: str; title: str; created: str; updated: str; turns: int; cost_usd: float
    model: str; reasoning: str                        # reasoning: needed by config_for_resume (S1)
    status: str                                       # idle | in_use | interrupted | current

@dataclass
class SavedSession:                                   # what a resume needs
    info: SessionInfo
    turn_lines: list[dict]                            # history.jsonl "turn" lines after the last reset
    all_turn_lines: int
    turn_no: int; last_seq: int; totals: dict         # totals: TurnStats.to_dict() shape
    interrupted: "InterruptedTurn | None"             # turn_id, user_message, events: list[dict]
    saved_config: dict                                # {model, reasoning, approval, prune_history} at the last save
    # The model lives in info.model and saved_config only (S1–S2 review removed the duplicate fields).

class SessionStore:
    def __init__(self, root: Path, *, gitignore: Path | None = None): ...  # for_workspace passes .agent_v3/.gitignore
    @classmethod
    def for_workspace(cls, workspace: Path) -> "SessionStore": ...
    def list(self, limit: int | None = None) -> list[SessionInfo]: ...
    def resolve(self, ref: str) -> str: ...           # id | unique prefix | "latest" -> full id
    def load(self, session_id: str) -> SavedSession: ...           # read-only, no lock, creates no files
    def create(self, session_id: str, config: AgentConfig) -> "SessionRecorder": ...   # folder + lock at first turn_started
    def open(self, session_id: str, config: AgentConfig | None = None
             ) -> tuple[SavedSession, "SessionRecorder"]: ...      # takes the lock (with retry, §4.6); `config` is
                                                                   # the resumed config, saved from the next turn on
    def delete(self, session_id: str) -> None: ...    # SessionInUse if locked; order in §4.6
    def session_dir(self, session_id: str) -> Path: ...
    def events_path(self, session_id: str) -> Path: ...
    def read_events(self, session_id: str, after_seq: int = 0,
                    limit: int | None = None) -> tuple[list[dict], bool]: ...  # saved events with seq > after_seq; (events, done)

RESTORABLE_SETTINGS = ("model", "reasoning")       # never "approval"

def config_for_resume(launch: AgentConfig, info: SessionInfo, explicit: set[str]) -> AgentConfig:
    """`launch` with each RESTORABLE_SETTINGS field taken from the saved session unless it is in `explicit`."""

class SessionRecorder:                                # every call arrives under the Session lock
    def on_event(self, event: Event) -> None: ...     # skips text_delta; updates meta at turn start/end
    def on_commit(self, *, turn_id, outcome, user_message, text, items, record,
                  stats: dict | None = None) -> None: ...  # stats: only for a recovered interrupted turn (§5.3)
    def on_reset(self) -> None: ...
    def close(self) -> None: ...                      # flush, close files, release the lock
    error: str | None; healthy: bool                  # how Session learns of a failure (§5.4)
```

`agent_v3/stats.py` holds `TurnStats` (with `from_dict()` and a `cost_usd` property) and `StatsCounter(web_fee_usd).observe(event)`. `session._Turn` subclasses `StatsCounter`, and the meta rebuild replays logged events through the same counter, so live and rebuilt totals are identical. `from agent_v3.session import TurnStats` still works.

```python
class Session:
    def __init__(self, config, on_event, model=None, *, registry=None,
                 store: SessionStore | None = None,   # None: nothing is saved (bench, tests, embedding)
                 resume: str | None = None): ...      # a full id (frontends resolve refs first); needs store
    @property
    def saved(self) -> bool: ...                      # True while a recorder is attached and healthy
    def update_config(self, *, model: str | None = None, reasoning: str | None = None,
                      approval: str | None = None) -> dict: ...  # between turns (Busy otherwise); §5.6
```

- `Session(..., store=s, resume=id)` raises `SessionNotFound` or `SessionInUse` **before emitting anything**, so a frontend can report the error and fall back without a stray `session_started`.
- **A `Session` object belongs to one saved session for its whole life.** `/resume`, `/new` and `new_session` close the current object and build a new one. This keeps `session_id` immutable inside `Session`, so existing code and tests that assume it is fixed stay correct.
- **Settings on resume (option C).**
  - Frontends call `config_for_resume(launch_config, info, explicit)` before `Session(..., resume=id)`, so `Session` itself still uses the config it is given. `explicit` is the set of `--model` / `--reasoning` flags typed on the command line (§6.1), plus any setting changed with `/model`, `/reasoning` or `set_config` earlier in this process.
  - Saved `model` and `reasoning` come back unless typed. Every other setting, **approval mode included**, comes from the launch flags or the defaults. So a session saved in `full-auto` resumes in `ask` unless `--approval full-auto` is typed again; nothing from disk can make the agent more permissive.
  - The workspace must match the store's. `session_resumed.saved_config` reports the saved `model`, `reasoning`, `approval` and `prune_history`, so a frontend can point out differences.
  - `/new` and `new_session` use the **working config**: the launch flags and defaults plus any settings changed by command in this process (§5.6), but never values restored from disk by a resume.

### 5.2 What is restored and what is rebuilt (D2)

| state | on resume | why |
|---|---|---|
| `session_id` | restored | The same folder and log continue. |
| history | **Restored** from the turn lines after the last reset: `[fresh system message] + items…`. Decided **per line** (S2): a line's `items` go back only when the current config has `prune_history=False` **and** the line's `model` equals the current model; otherwise its `record` is used. | Pruned items (user/assistant/developer) are plain messages, valid for any model. Encrypted reasoning items are tied to a model. Mixing them across models, or re-entering full traffic into a pruning session, is the risky case, and the pruned form is always valid. |
| system prompt | **rebuilt** (`build_system_prompt(config)`) | The Environment block has the date, approval mode, git status and the `python -m` hint, and all of these can change between runs. A stale prompt that claims `full-auto` while running `ask` would mislead the model. |
| `prompt_cache_key` | **rebuilt** from the new prompt | It is a hash of workspace + prompt + tools (v3 Phase 5b). The same day and config give the same key and a warm cache for the restored prefix. A new day gives a cold first round, about one cold round's cost, the same as any new session. |
| `_turn_no` | restored (`turn_no`, including an interrupted turn) | Turn ids stay unique within the log (t4 follows t3). The transcript and the interrupted-turn detection rely on this. |
| `_seq` | restored (`last_seq` = max `seq` in `events.jsonl`, not the meta cache) | `seq` stays strictly increasing per `session_id`, on disk and on the wire (§7.3). |
| usage totals | **restored** from `meta.totals`, or summed from the terminal events if the meta is missing | `usage_totals()`, `/usage` and the exit block describe the session, and the session continues. The listing's cost uses the same numbers. |
| `FileState` (read hashes) | **reset to empty** | Files may have changed between runs, and the model only has a record of what it read, not the content. `write_file(overwrite=true)` already returns `CONFLICT "Read the current file before overwriting it."` without a hash. `edit_files` matches against the current text. This matches `new_conversation()` (v3 Phase 2 log). |
| approval allowances (`ALLOW_SESSION`) | **not restored** | v3 §8.6: they "never persist across sessions". A resume is a new process and a new trust decision. |
| model, reasoning | **restored** unless typed on the command line (option C) | The session continues the way it was running. A typed flag still wins. |
| approval mode | **launch flag or default, never restored** | A permissive mode is never re-enabled from disk without the user typing it. |
| executor guard memory, read dedupe | fresh | They are per turn already. |
| approval request ids (`ap_N`), tool group ids | restart at 1 | They are per process. On disk, `ap_1` can occur once per attach. The transcript pops each id at its `approval_resolved`, so repeats are harmless. |

### 5.3 A turn that was running when the process died (D3)

**Detection.** A turn is interrupted if its `turn_started` is in `events.jsonl` but `history.jsonl` has no turn line with that `turn_id`. `meta.active_turn` is only a hint, used for the `interrupted` status in listings.

**Recovery**, done in `Session.__init__` when resuming, before `session_started`:
1. Rebuild the turn's activity by replaying its logged events through a fresh `_Turn` (`_Turn.observe` already consumes events; `events.event_from_dict(d)` turns a dict back into an `Event` with `EVENT_TYPES[d["type"]]`). This gives `activity()`, such as "read store.py; edited store.py (+3 −1); ran `python -m pytest` (exit 1)", and the turn's stats from its logged `model_round_completed` events.
2. Append to history `{"role": "user", ...}` and `{"role": "developer", "content": "Turn interrupted (the agent process stopped) after: <activity>. Files may have changed since; re-read before editing."}` (capped at 600 characters, like the other notes). Write it as a turn line with `outcome: "interrupted"`.
3. Add the turn's logged round and web costs to the totals. They were billed, so they are not dropped.
4. After `session_started` and `session_resumed`, emit `notice` (`warning`, code `turn_interrupted`): "Turn t4 was interrupted when the agent stopped. Its partial work is noted in the history." Because it is a normal event, it also goes into `events.jsonl` and therefore into exported transcripts.

**Side effects that were in flight:** a write that was in progress completed atomically or not at all (`os.replace`). An edit that finished without a logged `tool_completed` is missing from the note, which the "re-read" wording covers. On Windows, a running command's process tree died with the agent (the Job Object has `KILL_ON_JOB_CLOSE`); on POSIX its children can survive (§13). A pending approval was never answered, so its action never ran. The turn is not retried automatically; the user decides what to do next.

### 5.4 Recorder hooks inside `Session`

- `_emit`: after stamping and `turn.observe`, call `recorder.on_event(event)` **before** `on_event`, so an event the frontend has seen is already on disk.
- `_commit`, `_fail`, `cancel()`: compute `new_items` once, `self.history += new_items`, call `recorder.on_commit(...)`, **then** emit the terminal event (§4.2 order). `new_conversation()` calls `recorder.on_reset()`; `close()` calls `recorder.close()`.
- **Failure policy.** Any exception from the recorder (not only `OSError`, S2) is caught inside `SessionRecorder`. It disables the recorder and sets `error`, and `Session` emits one `notice` (`warning`, code `session_save_failed`, "Saving stopped: … The session continues unsaved."). `saved` becomes False. A failing disk never fails a turn (the CLI's sink rule in v3 Phase 3, applied to the core).
- **Where the notice appears** (S1–S2 review). `_emit` is the only place that reports it, right after the event being delivered. So a failed history line is reported just **after** the turn's terminal event. On resume, a failure at `open()` or during recovery is held until after `session_started`, `session_resumed` and any `turn_interrupted` notice, so those stay adjacent (§5.5, §7.3).
- **Cost under the lock.** One `write` + `flush` per event and one `fsync` per turn. This happens under the session lock, like the server's pipe write. A slow disk slows event delivery, which is accepted (§13).

### 5.5 New events `session_resumed` and `config_changed`

Emitted once, right after `session_started`, only when a `Session` was built with `resume=`. `session_started` itself is unchanged, and `EVENT_TYPES` gains `session_resumed`.
```python
@dataclass(frozen=True, kw_only=True)
class SessionResumed(Event):
    type: ClassVar[str] = "session_resumed"
    title: str
    created: str
    turns_total: int                 # every turn line, across resets
    turns: list                      # last ≤20 restored turns: {turn_id, user_message, outcome, text, ts}
    totals: dict                     # restored usage totals (TurnStats shape)
    history: str                     # "full" | "pruned": which form was restored (§5.2)
    restored_items: int              # history items given to the model, excluding the system message
    interrupted_turn: str | None     # turn_id recovered by §5.3, else null
    saved_config: dict               # {model, reasoning, approval, prune_history} at the last save

@dataclass(frozen=True, kw_only=True)
class ConfigChanged(Event):          # §5.6; EVENT_TYPES gains "config_changed"
    type: ClassVar[str] = "config_changed"
    changes: dict                    # {"approval": {"from": "ask", "to": "auto-edit"}}; {} if nothing changed
    config: dict                     # config.summary() + tools after the change, same shape as session_started.config
    history: str                     # "unchanged" | "pruned" (step 4 of §5.6 applied)
```

### 5.6 Changing settings mid-session (D8)

**Decision:** `Session.update_config` changes the **open** session in place, between turns only. The session id, history, log and lock stay the same.

**Why in place rather than closing and resuming:**
- A GUI gets one small `config_changed` event instead of a second `session_started` and `session_resumed` to redraw.
- `seq` simply continues, and the lock is never released, so another process can't grab the session in between.

**`update_config(model=, reasoning=, approval=)`**, under the session lock:
- **Preconditions.** It raises `Busy` while a turn runs and `ValueError` for an invalid reasoning level or approval mode. Model names are not validated; an unknown price already triggers the existing "cost is not tracked" notice.
- **Return value.** `{field: [old, new]}` for each field that changed; `{}` if nothing changed.

Steps:
1. `self.config = dataclasses.replace(self.config, **changes)`. `__post_init__` validates it.
2. `self.model.set_config(self.config)`. This is a new `ModelAdapter` method: `model`, `reasoning` and the cost lookup read it from the next request on. If the adapter built its own OpenAI client, the client is rebuilt when the reasoning level's timeout tier changes (`request_timeout`). `dropped_params` is kept. `FakeModelAdapter` inherits the method.
3. **If the approval mode changed:**
   - The gateway gets a new `ApprovalPolicy(mode)`, which clears "allow for session" approvals. A new mode is a new trust decision, the same rule as a resume.
   - The system prompt names the approval mode, so it is rebuilt (`build_system_prompt`), `history[0]` is replaced, and `cache_key` is recomputed.
4. **If the model changed and history holds full turns** (`prune_history=False`): history becomes `[system] + pruned records`, because encrypted reasoning items belong to the old model (§5.2). To make this possible, `Session` keeps `_pruned_history` in step with `history` at every commit and on restore.
5. Emit `config_changed`. The recorder updates `meta.json` (`model`, `reasoning`, `approval`), so a later resume restores the last-used model and reasoning (option C). It still never restores the approval mode.

**Cache effects:**
- A model change always starts cold, since the server's cache is per model.
- An approval change alters the prompt and key, so the next round starts cold (about $0.02 at sol rates).
- A reasoning-only change keeps the prompt and key. Whether the server reuses the cache across effort levels is unverified; the Phase S5 smoke test measures it.

**Safety.** Switching to `full-auto` is an explicit user action. The CLI prints a yellow line: "Edits and commands now run without asking, except risky commands and anything outside the workspace." The always-ask patterns and the outside-workspace rule apply in every mode, as before.

**Not changeable mid-session:** `workspace`, `web_search`, `prune_history` and the remaining fields. They change the tool list or the shape of history; use `/new` with flags instead. The executor keeps its original config reference; it reads only the limit fields, which never change.

---

## 6. CLI (`frontends/cli.py`, `frontends/commands.py`)

### 6.1 Flags and subcommands

- **Removed:** `--transcript`, kept as a hidden argument that exits 2 with "--transcript was removed: sessions are saved automatically. Use /export or `python -m agent_v3 export latest -o FILE`." **Kept:** `--events-log` (the only log with `text_delta`, for UI development) and `--verbose`.
- **New, from `add_session_args`, shared with the server:** `--resume [REF]` (an id, prefix or `latest`; without REF the CLI prints the list and asks "Resume which? [1–N, Enter = new session]", while the server requires REF); `--continue` / `-c`, the same as `--resume latest`, which starts a new session with a dim note if there are none; and `--no-save`, which cannot be combined with either (exit 2).
- **Detecting typed flags (option C).** In `add_config_args`, `--model` and `--reasoning` get `default=None`, and their help text names the real default. `config_from_args` fills `AgentConfig`'s defaults when they are None, so its result is unchanged. A new `explicit_settings(args) -> set[str]` returns the names that were typed. Both frontends keep that set for `config_for_resume`.
- `cli.main(argv)` sends `argv[0] in {"sessions", "export"}` to `commands.main`. Everything else parses as today, so `python -m agent_v3 --workspace X` is unchanged.

```text
python -m agent_v3 sessions [--workspace W] [--limit N]               list (§4.5 format)
python -m agent_v3 sessions delete REF [REF ...] [--workspace W]       refuses in-use sessions
python -m agent_v3 export REF [-o PATH] [--workspace W]                Markdown to stdout, or to PATH
```

Errors (`SessionNotFound`, `AmbiguousSession` listing the matches, `SessionInUse`) print to stderr and exit 2.

### 6.2 Slash commands

- **Matching.** `^/(resume|export|sessions|model|reasoning|approval)(?:\s+(.+))?$` takes an optional argument. The bare-word rule `^/[A-Za-z]+$` is unchanged for `/new`, `/usage`, `/quit` and unknown words (hint). So `/new file please` still goes to the model.
- `/sessions` prints the 10 most recent sessions (the current one marked `*`), plus `… N more: /sessions all` if there are more. `/sessions all` prints every session.
- **Settings (§5.6).**
  - `/model [NAME]`, `/reasoning [LEVEL]` and `/approval [MODE]` work between turns.
  - Without an argument, each prints the current value and the choices: models from `PRICING`, the reasoning levels, and the approval modes with their one-line meanings.
  - With an argument, each calls `session.update_config` and prints a dim confirmation, e.g. `model gpt-5.6-sol (was gpt-6-luna); the next request starts with a cold cache`.
  - `/approval full-auto` also prints the yellow warning. An invalid value prints the choices and changes nothing.
  - The change carries over to `/new` (working config, §5.1).
- `/resume [N|REF]` works only between turns (the only time the prompt is shown); without an argument it behaves like `--resume` without REF. It closes the current `Session`, drains its queue, and builds the resumed one through `Cli`'s `open_session` factory. The recap is one dim line, `Resumed s_3f9a1c0b7d · "Fix the failing test…" · 3 turns · $0.012 · last active 2026-10-15 17:20`, plus a dim line for each setting that differs from the saved one (e.g. `model gpt-6-luna (--model; saved with gpt-5.6-sol)`, `approval ask (saved with full-auto; approval is never restored)`), then the last exchange (`You ›` message, `Agent ›` answer clipped to 15 lines). Resuming the current session is a no-op with a note.
- `/export [PATH]` writes the transcript to PATH, or to `<session folder>/transcript.md` by default, and prints the path. The file is always rebuilt from scratch from `events.jsonl` (§6.3).
- `/new` closes the session and opens a new one (new id, new banner), saved unless `--no-save` is set. It never clears history in place, and there is no `/clear`. The CLI no longer calls `Session.new_conversation()`; the method stays for the server's v1 `new_conversation`.
- **Exit.** After the usage block, when the session was saved and had at least one turn, print `Session saved: s_3f9a1c0b7d · resume with: python -m agent_v3 --resume 3f9a1c0b7d`.
- **Sink warning text.** The CLI's sink-failure warning becomes "could not write the event log". Only `--events-log` is a sink now; session saving reports through the core's `session_save_failed` notice.
- `Cli.__init__` gains `store: SessionStore | None = None` and `open_session: Callable[[str | None], Session] | None = None`. When `open_session` is None, the default builds `Session(current.config, queue.put, model=current.model, store=store)`, with `resume=` for `/resume`. So `run_cli(...)` in the tests keeps working, and `/new` starts a new session there too.

### 6.3 Export (`frontends/transcript.py`)

```python
def export_transcript(events_path: Path, out_path: Path) -> Path:
    """Replay events.jsonl through a TranscriptWriter into a temp file, then os.replace onto out_path."""
```

A second `session_started` (a later attach) writes `> RESUMED 2026-10-16 09:12 (model=…, reasoning=…, approval=…)` instead of another `# Transcript` header. `session_resumed` is ignored, and the interrupted-turn notice shows as `> NOTICE (warning, turn_interrupted): …`. An interrupted turn shows its `**USER:**` and tool lines with no footer, which is accurate. The usage block sums every terminal event, so it covers the whole session. `config_changed` writes `> SETTINGS: model gpt-6-luna → gpt-5.6-sol; approval ask → auto-edit`.

---

## 7. stdio server (additive protocol changes)

### 7.1 Startup

The server takes `--resume REF`, `--continue` and `--no-save` (§6.1). It saves by default. Saved `model`/`reasoning` are restored unless passed as flags, and approval never is (§5.1); the same applies to `resume_session`. With `--resume` or `--continue`, the first line is still `session_started`, with the saved `session_id` and `seq = last_seq + 1`, followed by `session_resumed`. `--resume` with an unknown or in-use REF exits 2 with an empty stdout, like the existing startup errors.

### 7.2 New client → server messages

All of these except `list_sessions`, `export_session` and `get_session_events` need an idle session (otherwise `error`/`busy`). Replies that are not events (`sessions`, `transcript`, `session_deleted`, `session_events`) have no `seq`, like `usage`.

| type | fields | effect and replies |
|---|---|---|
| `list_sessions` | `limit` (int, optional; omitted = all) | Reply `sessions`: `{current, total, sessions: [SessionInfo…]}`, newest first. Allowed at any time. |
| `resume_session` | `session_id` (id or prefix), **or** `latest: true` | Closes the current session (it is already saved), then emits `session_started` and `session_resumed` for the chosen one, plus `notice turn_interrupted` if §5.3 applied. Errors: `not_found`, `ambiguous`, `in_use`, `saving_disabled`. Resuming the current session gives `error`/`bad_request`. |
| `new_session` | none | Closes the current session and starts a new one (`session_started`, new id, `seq` 1). `new_conversation` keeps its v1 meaning (reset line, same id). |
| `export_session` | `session_id` (optional; default current) | Reply `transcript`: `{session_id, markdown}`. Allowed at any time (the log is append-only). Errors: `not_found`, `ambiguous`, `saving_disabled` (current session, `--no-save`). |
| `delete_session` | `session_id` (id or prefix; required) | Reply `session_deleted`: `{session_id}`. Deleting the current or another process's session gives `in_use`. |
| `set_config` | `model`, `reasoning`, `approval` (each an optional string; at least one) | §5.6. Emits the event `config_changed`, even when nothing changed (`changes: {}`), so a client always gets an answer. Errors: `busy`, `bad_request` (no fields, wrong type, invalid level or mode). |
| `get_session_events` | `session_id` (optional; default current), `after_seq` (int, default 0), `limit` (int, default 500, max 2000) | Reply `session_events`: `{session_id, events, next_after_seq, done}`. These are the saved events with `seq > after_seq`, in order, without `text_delta`; page by passing `next_after_seq` back. Allowed at any time. Errors: `not_found`, `ambiguous`, `saving_disabled`. |

New `error` codes: `not_found`, `ambiguous`, `in_use`, `saving_disabled`. v1 already requires clients to treat unknown codes generically.

```json
{"type": "list_sessions"}
{"type": "sessions", "current": "s_9c1d2e3f4a5b", "total": 2, "sessions": [{"session_id": "s_9c1d2e3f4a5b", "title": "Rename Store.remove", "created": "2026-10-16T09:00:01.002+00:00", "updated": "2026-10-16T09:04:40.311+00:00", "turns": 1, "cost_usd": 0.0011, "model": "gpt-6-luna", "status": "current"}, {"session_id": "s_3f9a1c0b7d2e", "title": "Fix the failing test in test_store.py", "created": "2026-10-15T16:58:02.114+00:00", "updated": "2026-10-15T17:20:41.530+00:00", "turns": 3, "cost_usd": 0.0123, "model": "gpt-6-luna", "status": "interrupted"}]}

{"type": "resume_session", "session_id": "3f9a"}
{"type": "session_started", "session_id": "s_3f9a1c0b7d2e", "turn_id": null, "seq": 215, "ts": "2026-10-16T09:05:12.480+00:00", "protocol_version": 1, "config": {"model": "gpt-6-luna", "reasoning": "medium", "approval": "ask", "workspace": "C:\\work\\app", "web_search": true, "tools": ["list_dir", "..."]}}
{"type": "session_resumed", "session_id": "s_3f9a1c0b7d2e", "turn_id": null, "seq": 216, "ts": "...", "title": "Fix the failing test in test_store.py", "created": "2026-10-15T16:58:02.114+00:00", "turns_total": 4, "turns": [{"turn_id": "t3", "user_message": "Run the tests again", "outcome": "completed", "text": "All 18 tests pass.", "ts": "2026-10-15T17:19:58.000+00:00"}, {"turn_id": "t4", "user_message": "Now refactor report.py", "outcome": "interrupted", "text": "", "ts": "2026-10-16T09:05:12.470+00:00"}], "totals": {"rounds": 14, "tool_calls": 22, "model_cost_usd": 0.0113, "web_cost_usd": 0.01, "...": "..."}, "history": "pruned", "restored_items": 11, "interrupted_turn": "t4", "saved_config": {"model": "gpt-6-luna", "reasoning": "medium", "approval": "ask", "prune_history": true}}
{"type": "notice", "session_id": "s_3f9a1c0b7d2e", "turn_id": null, "seq": 217, "ts": "...", "level": "warning", "code": "turn_interrupted", "message": "Turn t4 was interrupted when the agent stopped. Its partial work is noted in the history."}

{"type": "resume_session", "latest": true}
{"type": "error", "code": "in_use", "message": "Session s_3f9a1c0b7d2e is open in another agent_v3 process (pid 41236)."}

{"type": "new_session"}
{"type": "session_started", "session_id": "s_51be09d7c3aa", "turn_id": null, "seq": 1, "...": "..."}

{"type": "export_session"}
{"type": "transcript", "session_id": "s_51be09d7c3aa", "markdown": "\n---\n\n# Transcript 2026-10-16 09:06 (model=gpt-6-luna, ...)\n\n**USER:** ..."}

{"type": "delete_session", "session_id": "s_77e0"}
{"type": "session_deleted", "session_id": "s_77e0d41a9c55"}

{"type": "set_config", "model": "gpt-5.6-sol", "approval": "auto-edit"}
{"type": "config_changed", "session_id": "s_51be09d7c3aa", "turn_id": null, "seq": 42, "ts": "...", "changes": {"model": {"from": "gpt-6-luna", "to": "gpt-5.6-sol"}, "approval": {"from": "ask", "to": "auto-edit"}}, "config": {"model": "gpt-5.6-sol", "reasoning": "medium", "approval": "auto-edit", "workspace": "C:\\work\\app", "web_search": true, "tools": ["list_dir", "..."]}, "history": "unchanged"}

{"type": "get_session_events", "session_id": "3f9a", "after_seq": 0, "limit": 500}
{"type": "session_events", "session_id": "s_3f9a1c0b7d2e", "events": [{"type": "session_started", "seq": 1, "...": "..."}, {"type": "turn_started", "turn_id": "t1", "seq": 2, "user_message": "Fix the failing test in test_store.py", "...": "..."}], "next_after_seq": 214, "done": true}
```

### 7.3 Rules added to the Protocol v1 reference (v3 §10.2)

- **More than one `session_started`.** A `session_started` line may appear again, but **only** in response to `resume_session` or `new_session`. It opens a new session context: later events carry its `session_id`. A client that never sends those messages never sees a second one.
- **`seq` per session.** `seq` is strictly increasing with no gaps per `session_id` on the wire. A resumed session continues its saved numbering, so its first `seq` is greater than 1 (§5.2). A client that tracks `seq` should reset its expectation at each `session_started`.
- **Recap event.** `session_resumed` directly follows the `session_started` of a resumed session.
- **Settings changes.** `config_changed` appears only between turns, in reply to `set_config`. Its `config` replaces what the client learned from `session_started.config`.
- **Redrawing a saved session.** `get_session_events` returns saved events with their original `seq` (with gaps where `text_delta` was dropped). To open the current session, fetch pages until `done`, then apply live events with a higher `seq`. Live events and fetched events share the numbering, so duplicates are easy to drop.
- **Usage after a resume.** `get_usage` after a resume returns totals for the whole saved session, including earlier processes.

**Implementation.** `StdioServer` gains `store` and `resume` keyword arguments that default to None, so the existing in-process tests construct it unchanged. Replacing `self.session` happens on the reader thread while the session is idle. The old session is closed first, which releases its lock and file handles, so its events cannot interleave with the new session's.

---

## 8. Benchmark harness (D6)

**Decision:** the bench does not change. `run_v3` builds `Session(config, on_event)` with no store, so nothing is saved, and it keeps writing its own `bench/results/events/*.jsonl` (with `text_delta`, as today).

**Why not save bench runs**, in the workdir or a separate store: `bench/tasks.py` `SKIPPED_DIRS` does not include `.agent_v3`, so session files in the workdir would show up in `files_changed` and fail T2's "only `store.py` changed" check. Fixed workdirs are deleted after each run anyway, and the bench's event logs already hold everything a saved session would. If it is ever wanted, `store=SessionStore(RESULTS / "sessions")` works, which is why `SessionStore` takes a root folder rather than a workspace.

**Guard:** a test asserts that a store-less `Session` creates no `.agent_v3/sessions`, and one T6 run on luna (about $0.001) confirms that `files_changed` is unchanged.

---

## 9. Secrets and deletion (D7)

**Stored, as plain UTF-8 under `<workspace>/.agent_v3/sessions/`:**
- every user message, answer and turn record (paths read and edited, commands with exit codes);
- every tool's arguments (including the full `content` of `write_file` and every `old_text`/`new_text`), every tool's model-facing output (file contents up to the read caps, command output up to 12k characters), and approval diffs with `metadata.full_content` (owner decision: full output is kept);
- web search queries and URLs;
- with `prune_history=False`, whole turns in `history.jsonl`, including reasoning as `encrypted_content` (only OpenAI can decrypt it);
- metadata: model, approval mode, workspace path, timestamps, costs, owner pid.

**Not stored:** the API key and environment variables (the config summary never includes them; a test checks that `meta.json` and `session_started.config` hold no key), and approval allowances. Nothing new goes to OpenAI: `store=False` is unchanged.

**Protections:** `.agent_v3/.gitignore` = `*` (§4.1). On POSIX, files are created `0o600` and folders `0o700`; on Windows they inherit the workspace ACL. `IGNORED_DIRS` keeps session files out of `glob_files` and `search_text`, though an explicit `read_file` still works. `--no-save` turns saving off.

**Deletion** (never automatic, never in bulk): `python -m agent_v3 sessions delete REF…` in the CLI, `delete_session` in the server, or by hand: delete `<workspace>/.agent_v3/sessions/<id>/` or the whole `.agent_v3/` folder. Nothing else references a session, so deleting by hand is safe while no agent is running. Deletion removes files; it does not securely overwrite them.

v3 §13's "no secret redaction" still applies. The CLI `--help` epilog and the banner's third line say where sessions are saved.

---

## 10. Implementation phases

Each phase ends with the whole suite green on Windows and a log entry at the bottom (date, what was done, deviations).

**Files.** Each phase lists the files it may create or change. Paths are relative to `My Agent Project/`, and `tests/` files are always allowed for that phase's own tests. If a phase seems to need a file outside its list, stop and record why in the log entry rather than editing it. The bench (`bench/`) is never changed.

### Phase S1 — Storage (~350 LOC + ~300 LOC tests)
- `jsonl.py`, `sessions.py` (store, recorder, `SavedSession` loading, locking, delete), `events.event_from_dict`, and the `read_events` re-export. No `Session` change yet. Tests: `tests/test_sessions_store.py`.
- **Files:** new `agent_v3/jsonl.py` and `agent_v3/sessions.py` (including `config_for_resume`); `agent_v3/events.py` (`event_from_dict` only); `agent_v3/frontends/eventlog.py` (the re-export only); new `tests/test_sessions_store.py`. **Not** `session.py` or any other frontend.
- **Exit:** store tests green, including a subprocess that holds a lock and is killed, after which `open()` succeeds.

### Phase S2 — Core integration (~200 LOC + ~350 LOC tests)
- `Session(store=, resume=)`, recorder hooks (§5.4), restore (§5.2), interrupted-turn recovery (§5.3), `SessionResumed`. Tests: `tests/test_session_resume.py` and the `test_core_misc.py` update.
- **Files:** `agent_v3/session.py`, `agent_v3/events.py` (`SessionResumed`), `agent_v3/sessions.py` (fixes found while integrating), new `tests/test_session_resume.py`, `tests/test_core_misc.py` (event-type set only). **Not** `frontends/` (no CLI or server wiring yet) or `model.py`. The smoke script goes in the scratchpad, not the repo.
- **Live smoke test** (luna, about $0.01, a scratch script as in v3 Phase 2). (1) Run a two-turn session with `prune_history=True`, close it, resume it in a **new process**, and ask "what did I ask first?". (2) Do the same with `prune_history=False`, web search on and a tool call in each turn. This checks that encrypted reasoning items and `msg_`/`fc_`/`ws_` ids from an earlier process are accepted. If (2) is rejected, change §5.2 to always restore `record` and log the deviation.
- **Exit:** tests green, smoke test recorded, and one bench T6 run with `files_changed` unchanged.

### Phase S3 — CLI and export (~250 LOC + ~250 LOC tests)
- `args.add_session_args`, `cli.py` (§6.1, §6.2), `commands.py`, `transcript.export_transcript` and the `RESUMED` line (`__main__.py` unchanged). Point v3 §4 (flag list) and §10.1/§10.3 at this spec in one line each.
- **Files:** `agent_v3/frontends/args.py` (`add_session_args`, `explicit_settings`, `--model`/`--reasoning` defaults), `agent_v3/frontends/cli.py`, new `agent_v3/frontends/commands.py`, `agent_v3/frontends/transcript.py`, new `tests/test_cli_sessions.py`, `tests/test_frontends.py` (the one warning string), and `agent_v3_claude_plan.md` (the one-line pointers). Includes the listing behaviour of §4.5 for the CLI. **Not** `session.py`, `sessions.py` (beyond small bug fixes, which must be logged) or `stdio_server.py`.
- Manual checks (needs a person at a console): quit, then `--continue` continues the conversation; kill the terminal mid-turn, then `--continue` shows the interrupted notice; with two terminals, `--continue` in the second reports `in use`; `/export` output reads like the old `--transcript`; non-TTY `/sessions` has no ANSI.
- **Exit:** tests green, manual checklist handed over.

### Phase S4 — stdio server (~120 LOC + ~200 LOC tests)
- §7 messages, startup flags, swappable session, error codes. Append the §7.3 rules and the message table to v3 §10.2 "Protocol v1 reference" (additive; `PROTOCOL_VERSION` stays 1).
- **Files:** `agent_v3/frontends/stdio_server.py`, `tests/test_stdio_server.py` (additions only; the 19 existing tests stay byte-for-byte unchanged), and `agent_v3_claude_plan.md` §10.2 (append only). Includes `list_sessions` returning all with `total` (§4.5). `args.py` only if S3 left a server flag unwired. **Not** `session.py`, `sessions.py` or `cli.py`.
- **Exit:** the new protocol tests pass, and **all 19 existing `test_stdio_server.py` tests pass unmodified**. That is the compatibility proof.

### Phase S5 — Settings mid-session and GUI additions (~200 LOC + ~300 LOC tests)
- Core: `Session.update_config`, `_pruned_history`, `ModelAdapter.set_config`, `ConfigChanged`, `SessionStore.read_events`.
- CLI: `/model`, `/reasoning`, `/approval`, and the transcript `SETTINGS` line.
- Server: `set_config`, `get_session_events`.
- The "list everything" behaviour (§4.5) belongs with S3/S4, which build the listing.
- **Files:** `agent_v3/session.py`, `agent_v3/model.py` (`set_config` only), `agent_v3/events.py` (`ConfigChanged`), `agent_v3/sessions.py` (`read_events`, meta update), `agent_v3/frontends/cli.py`, `agent_v3/frontends/transcript.py` (`SETTINGS` line), `agent_v3/frontends/stdio_server.py`, new `tests/test_session_settings.py`, additions to `tests/test_cli_sessions.py` and `tests/test_stdio_server.py`, `tests/test_core_misc.py` (event-type set), and `agent_v3_claude_plan.md` §10.2 (append only). **Not** `approvals.py` (a new `ApprovalPolicy` object is enough) or the tools.
- Tests: `tests/test_session_settings.py` and the additions in §11.2.
- **Live smoke test** (about $0.01):
  - On one session, change reasoning `medium` → `low` and record `cached_tokens` on the next round (does the cache survive an effort change?).
  - Change approval `ask` → `auto-edit`.
  - Change the model between two cheap models, with `prune_history` on and then off.
  - Each next turn must be accepted and must still answer "what did I ask first?".
- **Exit:** tests green, smoke test recorded, the 19 original stdio tests unmodified, and v3 §10.2 updated with `set_config`, `get_session_events` and their rules.

Estimated total: about 1,120 LOC of implementation and 1,400 of tests.

---

## 11. Tests

### 11.1 Existing tests that change

| test | change |
|---|---|
| `test_core_misc.py::test_event_types_cover_the_protocol` | Add `"session_resumed"` (S2) and `"config_changed"` (S5) to the expected set. |
| `test_frontends.py::test_cli_survives_a_failing_sink` | The expected text becomes "could not write the event log" (§6.2). |

Nothing else changes. `test_session.py`, `test_approvals.py`, `test_executor.py` and the tool tests build sessions without a store, so they save nothing. The other `test_frontends.py` tests build `Cli` without a factory; none of them uses `/new`, and the `eventlog` imports work through the re-export. The `test_stdio_server.py` subprocesses now save into their temp workspaces, but those tests only check named files and never list the folder. The bench passes no store. `test_config_from_args_maps_flags` is unchanged: `config_from_args` still returns the defaults when `--model`/`--reasoning` are omitted.

### 11.2 New tests

**`test_sessions_store.py` (S1):**
- Lazy creation: no folder before the first `turn_started`; `.agent_v3/.gitignore` created once, never overwritten.
- `text_delta` is not written; lines are readable while the file is open. The history line exists before the terminal event reaches a recording sink.
- A torn last line in either log is skipped on load, and `repair_tail` makes the next append valid.
- A missing or corrupt `meta.json` is rebuilt from the logs (title, turns, cost, totals, last_seq match).
- Listing order, `limit`, and the `idle` / `in_use` / `interrupted` statuses.
- Refs: full id, unique prefix, `latest`, ambiguous (lists matches), not found, prefix under 4 characters rejected.
- Locks: a second `open()` in-process and a lock held by a subprocess both give `SessionInUse`; after the subprocess is killed, `open()` succeeds.
- `delete` refuses an in-use session and removes only the named session's folder.
- A reset line is written only after a turn line, and `load` returns only the turn lines after it. An unwritable folder disables the recorder without raising.

**`test_session_resume.py` (S2)**, using `FakeModelAdapter.requests`:
- A store-less `Session` creates no `.agent_v3/sessions` (the bench guarantee).
- Two turns, close, resume: same `session_id`; `session_started` then `session_resumed`; `seq` continues from the log's maximum; the next turn is `t3`; `usage_totals()` includes the earlier turns; the next request's input is `[new system, u1, a1, rec1, u2, a2, rec2, u3]`.
- Resuming with another approval mode gives a prompt naming the new mode and the same cache key as a fresh session with that config.
- An overwrite of a file read before the resume gets `CONFLICT` until it is re-read. An `ALLOW_SESSION` command is asked again after the resume.
- With `prune_history=False` on both sides and the same model, the full items are restored (`history == "full"`); with a different model, the record is restored (`"pruned"`). Cancelled and failed turns come back with their notes.
- Interrupted turn (t3 has `turn_started`, tool events and a round, but no history line): the note lists the edit and command; `notice turn_interrupted` follows `session_resumed`; the totals include t3's cost; a second resume does not recover it again.
- After `new_conversation()`, a resume restores only the turns after the reset.
- A recorder raising `OSError` gives exactly one `session_save_failed`, the turn still completes, and `saved` is False.
- Resuming an in-use session raises `SessionInUse` with `on_event` never called. `SessionResumed` survives `json.dumps`. No `meta.json` field or `session_started.config` value contains `OPENAI_API_KEY`'s value.

**`test_cli_sessions.py` (S3):**
- `--transcript` exits 2 with the hint, and so does `--no-save` with `--resume`.
- Option C: a session saved with `gpt-5.6-sol`/`high`/`full-auto` resumed with no flags runs on sol/high in `ask`; with `--model X` it runs on X and keeps `high`; with `--approval full-auto` it runs in `full-auto`. The recap names each difference. `/new` after that resume uses the launch config. `explicit_settings` and `config_for_resume` also get direct unit tests.
- `/resume 2` and `/export out.md` are commands; `/new file please` goes to the model. `/sessions` marks the current session.
- `/resume N` prints the recap, and the next request carries the history. `/new` starts a new id with or without a factory (the default factory reuses the fake model), never calls `new_conversation()`, and `/clear` prints the unknown-command hint.
- `/export` writes to the session folder by default, and its output equals a direct `TranscriptWriter` replay. A log with two `session_started` lines gives one header and one `> RESUMED` line.
- Subcommands: `export latest` (stdout and `-o`), `sessions` (lists all by default; `--limit`), `sessions delete`. The exit hint appears only for a saved session with turns.
- `/sessions` with 14 sessions shows 10 and the `… 4 more` line; `/sessions all` shows 14.
- (S5) `/model`, `/reasoning` and `/approval` without an argument print the current value and the choices. With one they confirm the change, and `/approval full-auto` warns. An invalid value changes nothing. `/new` after `/model X` runs on X.

**`test_session_settings.py` (S5):**
- `update_config` raises `Busy` during a turn and `ValueError` for an invalid level or mode; unchanged values return `{}` and still emit `config_changed` with `changes: {}`.
- Model change: the next request uses the new model and its cost uses the new rates. With `prune_history=False`, history becomes the pruned form (`history: "pruned"`); with pruning on it is untouched.
- Approval change: the prompt names the new mode, `cache_key` changes, an earlier `ALLOW_SESSION` is asked again, and `auto-edit` stops asking for workspace edits.
- Reasoning change: the request's effort changes while the prompt and `cache_key` do not; an injected client is not rebuilt.
- `config_changed` is logged and `meta.json` updated; a later resume restores the changed model/reasoning but not the approval.
- `read_events` paging: `after_seq`, `limit`, `done`, no `text_delta`, and a torn last line skipped.

**`test_stdio_server.py` additions (S4, S5):**
- `list_sessions` after a turn shows one `current` row.
- Server A runs a turn and shuts down; server B with `--resume <id>` sends `session_started` with the same id and `seq` > 1, then `session_resumed`.
- Runtime `resume_session` (in-process, requests checked through the fake). Errors: `busy` during a turn, `not_found`, `ambiguous`, `in_use` (held by another live server), and `bad_request` for the current session.
- `new_session` gives a new id with `seq` 1. `export_session` returns markdown with the `**USER:**` line. `delete_session` gives `in_use` for the current session, otherwise `session_deleted`, and the session leaves the list.
- With `--no-save` there is no sessions folder; `resume_session` gives `saving_disabled`; `list_sessions` still works.
- `list_sessions` without `limit` returns every session, with `total`.
- (S5) `set_config` gives `config_changed`, and the next turn's request uses the new model. It gives `busy` during a turn, and `bad_request` with no fields or an invalid mode.
- (S5) `get_session_events` pages through another saved session (`next_after_seq`, `done`), defaults to the current session, gives `not_found` for an unknown ref, and gives `saving_disabled` under `--no-save`.

---

## 12. Out of scope

- Listing or resuming across workspaces, and a per-user session folder. A GUI with a project picker would need a per-user index; revisit when the GUI is designed. Saving bench runs (§8).
- Changing settings during a running turn, and changing `workspace`, `web_search` or `prune_history` mid-session (§5.6).
- Model-written or editable titles, search, tags; forking, rewinding or undoing file changes; retrying an interrupted turn automatically.
- Automatic, age-based or bulk deletion (owner decision), secure overwrite on delete, encryption at rest, secret redaction (v3 §13).
- Server-side state (`previous_response_id`, the Conversations API) and `store=True`.
- Cleaning up `.agent_v3/outputs/` logs. `sessions delete` does not touch them; a later spec can tie them to sessions by `call_id`.
- A writer thread for disk writes (§13 says when it would be needed).

---

## 13. Known risks

| risk | mitigation |
|---|---|
| The API rejects encrypted reasoning items or item ids from an earlier process or day (`prune_history=False` resume). | The S2 live smoke test checks it. The fallback is to always restore the pruned `record`, which is already stored on every line. Pruning is on by default, so normal use never hits this. |
| Disk I/O under the session lock stalls event delivery on a slow or network disk. | One flush per event and one fsync per turn. If a user reports it, move the recorder behind a queue and writer thread (the order stays the same because the queue is FIFO). |
| `os.replace` on `meta.json` fails on Windows while another process reads it. | 5 retries; the meta is only a cache and is rebuilt from the logs. |
| A torn tail glues the next append onto a fragment. | `repair_tail` before the first append, with a test. |
| POSIX: an interrupted turn's command children survive the agent process. | Documented. The interrupted note tells the model files may have changed. The POSIX path is untested, as in v3 Phase 1. |
| Clients that assume the first `seq` is 1, or that there is one `session_id` per connection. | This only happens after a client opts in (`--resume`/`--continue` flags or the new messages). The §7.3 rules document it, and the 19 existing protocol tests must pass unmodified. |
| Session files contain secrets and live inside the project folder. | `.gitignore` = `*`, POSIX `0o600`, `IGNORED_DIRS`, per-session delete, `--no-save`, and the banner says where sessions go (§9). |
| A resumed session's first round is a cold cache miss because the date in the prompt changed. | Accepted: one cold round per resume (about $0.02 at gpt-5.6-sol rates, per v3 Phase 3b). Same-day resumes with the same config get the same cache key. |
| Users run `--continue` while the session is open elsewhere and expect it to work. | A clear `in use` error names the pid and suggests `--resume`. |
| A mid-session change makes the next round cold (model or approval change; maybe reasoning). | Accepted; the CLI says so. Phase S5 measures the reasoning case. |
| A mid-session model change with `prune_history=False` loses the full turn detail from history. | Documented in `config_changed.history = "pruned"`. The event log still has everything. |
| `get_session_events` re-reads the log for each page (O(log size) per page). | Logs are a few MB at most. Add a seq→offset index only if a GUI reports slow loading. |

---

## Implementation log

*(Append one entry per phase: date, summary, deviations from spec.)*

### Phase S1 — Storage (2026-10-17)

**Built.**
- `agent_v3/jsonl.py` (new): `append_line(file, obj, fsync=)` (UTF-8 bytes, bare `\n`, flush, optional fsync), `read_jsonl(path)` (skips blank and undecodable lines, including a torn multi-byte character), `repair_tail(path)` (truncates after the last `\n`, reading backwards in 4 KB chunks).
- `agent_v3/sessions.py` (new): the errors, `SessionInfo`, `InterruptedTurn`, `SavedSession`, `session_title`, `RESTORABLE_SETTINGS`, `config_for_resume`, `SessionStore` (`for_workspace`, `list`, `resolve`, `load`, `create`, `open`, `delete`, `events_path`, `session_dir`), `SessionRecorder` (`on_event`, `on_commit`, `on_reset`, `close`, plus `error`/`healthy`), and the `msvcrt.locking` / `fcntl.flock` lock. Meta is rebuilt from the logs when it is missing, corrupt or stale.
- `agent_v3/events.py`: `event_from_dict()` only.
- `agent_v3/frontends/eventlog.py`: `read_events` is now `from ..jsonl import read_jsonl as read_events`. `EventLogWriter` is unchanged.
- `tests/test_sessions_store.py` (new, 25 tests): covers everything in the §11.2 S1 list, plus `event_from_dict` round trips, `repair_tail` edge cases, a stale meta, `open()` owner/settings handling and `config_for_resume`. The lock test runs a real subprocess that holds the lock and gets hard-killed (`Popen.kill`); after that, `open()` succeeds. While the child is alive, `SessionInUse.owner_pid == child.pid`.

**Tests.** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`: **294 passed, 1 skipped** (was 270; +24 new; the skip is the POSIX-only permissions test on Windows). No existing test changed.

**Size.** `sessions.py` is about 640 lines, against the ~350 estimated. The extra lines are the meta rebuild (`_meta_from_logs`, `_logged_stats`, `_read_meta` validation) and the docstrings. `jsonl.py` is about 55 lines, the tests about 500.

**Deviations from the spec, with reasons.**
1. **`SessionInfo` gains `reasoning`.** `config_for_resume(launch, info, explicit)` has to restore the saved reasoning, and the §5.1 `SessionInfo` had no field for it. This is additive for the S4 `list_sessions` rows.
2. **`SavedSession` gains `saved_config`** (`{model, reasoning, approval, prune_history}` at the last save). S2 needs it for `session_resumed.saved_config`, and the §5.1 fields could not supply `approval`.
3. **`SessionStore(root, *, gitignore=None)`.** The constructor takes an optional path for the `.gitignore`, and `for_workspace` passes `<ws>/.agent_v3/.gitignore`. A store built on a bare root (the bench-style `SessionStore(RESULTS / "sessions")` from §8) then writes no `.gitignore` outside `.agent_v3`.
4. **`SessionStore.open(session_id, config=None)`.** `open` takes the resumed config. Without it, `meta.json` would keep the old `model`/`reasoning` after `--resume --model X`, so the listing would be wrong and the next resume would restore the wrong model (option C says "saved" means last used). The new settings are written to meta from the next save (`turn_started`) on, so opening a session and quitting changes nothing. S2 should pass the config it resumes with.
5. **`open()` rewrites `meta.json` immediately with the new `owner_pid`.** §4.2 writes meta only at turn start and end. Without the early write, `SessionInUse` would name the pid of the previous, dead owner until the first turn.
6. **`on_commit(..., stats=None)`.** The extra argument is used only for a recovered interrupted turn, which has no terminal event to carry its stats (§5.3 step 3). The recorder adds it to `meta.totals`. S2 should pass the replayed `_Turn.stats.to_dict()`. `SavedSession.totals` does **not** include a pending interrupted turn's cost; the recovery adds it.
7. **When meta is used.** `load()` uses `meta.json` only if it is well-formed **and** its `turns` equals the number of turn lines. Otherwise, for example after a crash between the history line and the meta write, it rebuilds from the logs. `turn_no`, `last_seq` and `active_turn` always come from the logs (§5.2). `list()` uses meta as it is and rebuilds only when meta is missing or corrupt.
8. **Rebuilt totals include recovered interrupted turns.** For a turn line with `outcome: "interrupted"` and no terminal event, the rebuild sums its logged rounds, tool starts and web actions (`_logged_stats`). The web fee isn't saved, so the rebuild uses `AgentConfig`'s default `web_search_fee_usd`.
9. **`meta.json` also stores `approval`.** The §4.4 example omits it, but §5.6 step 5 says the recorder updates it and S2 needs it for `saved_config`. It is never restored (`RESTORABLE_SETTINGS`).
10. **`prune_history` when meta is rebuilt** is inferred, because `config.summary()` does not include it: any non-null `record` means it was off, and otherwise it is assumed on. A `prune_history=False` session that only has cancelled or failed turns is inferred as on. That case is harmless because those lines' `record` is null and their `items` are already the pruned form.
11. **Refs.** The `s_` prefix is optional and matching ignores case. A prefix under 4 characters raises `SessionNotFound` with a "too short" message rather than a separate error class, so the frontends' three-error handling (§6.1) and the server's `not_found` code cover it.
12. **`event_from_dict`** ignores unknown keys, so logs from newer versions still load. It raises `ValueError` for an unknown `type` rather than a bare `KeyError`.
13. **Not built in S1: `SessionStore.read_events` (paging).** §5.1 lists it, but Phase S5 owns it ("`SessionStore.read_events`" in its core list and `sessions.py (read_events, …)` in its Files line). Meta updates on `config_changed` are also left for S5.
14. **How the recorder reports failure.** §5.4 does not say how `Session` learns about a failure. The recorder exposes `error: str | None` (it names the session, the folder and the `OSError`) and `healthy`. S2's `Session.saved` can be `recorder is not None and recorder.healthy`, and it emits `session_save_failed` once when `error` first becomes set. A disabled recorder keeps its lock until `close()`.
15. **`open()` on a folder where the lock file cannot be created** (an `OSError` other than a lock conflict, such as a read-only folder) returns the `SavedSession` with a recorder that starts disabled, instead of raising. A session in a read-only workspace can still be resumed, and it reports `session_save_failed`.
16. **Known side effect of status probing.** `list()` and `load()` take each session's lock for a moment to compute `in_use`, as §4.5 specifies. An `open()` in another process at exactly that moment could get a spurious `SessionInUse`. I accepted this; S3/S4 could retry `open()` once after a short pause if it ever shows up.

**Files.** Only the files on the S1 Files line were changed. Nothing outside it was needed.

**Notes for S2.**
- `InterruptedTurn.events` starts with the turn's `turn_started`.
- `record: null` in a turn line means "equal to `items`", so restore must fall back to `items`.
- Call `recorder.close()` only after the last event has been emitted.

### Phase S2 — Core integration (2026-10-17)

**Built.**
- `agent_v3/session.py`: `Session(..., store=None, resume=None)` and the `saved` property. With `resume=`, `store.open(resume, config)` runs first, so `SessionNotFound` / `SessionInUse` are raised before anything is emitted; `resume` without a store raises `ValueError`. The construction moved into `_setup()`. If it raises after the lock was taken, the recorder is closed again, so a failed attempt never keeps the session locked.
- Recorder hooks (§5.4), all under `_lock`: `_emit` calls `recorder.on_event` after stamping and `observe`, before `on_event`. `_commit`, `_fail` and `cancel()` build the turn's items once, extend `history`, call `on_commit` (`_save_commit`), then emit the terminal event. `new_conversation()` calls `on_reset`. `close()` closes the recorder after `cancel()` and the executor shutdown. `_commit` always builds the pruned triple and passes it as `record`; with `prune_history=False`, `items` is the full turn. History is built exactly as before.
- Restore (§5.2, `_restore`): `_seq = last_seq`, `_turn_no = turn_no`, totals from `saved.totals`, and history = fresh system message + the turn lines after the last reset. The system prompt, cache key, `FileState` and `ApprovalPolicy` are built fresh by `_setup`, so none of them is restored.
- Interrupted-turn recovery (§5.3, `_recover_interrupted`): the logged events are replayed through a fresh `_Turn` via `event_from_dict`, and lines that do not parse are skipped. The user message and the "Turn interrupted (the agent process stopped) after: …" note (capped at 600) are appended. The turn's stats are added to the totals and passed as `on_commit(..., outcome="interrupted", stats=…)`. After `session_started` and `session_resumed`, a `notice` (`warning`, `turn_interrupted`) is emitted.
- `agent_v3/events.py`: `SessionResumed`, added to `EVENT_TYPES`.
- `agent_v3/sessions.py`: two integration fixes (deviations 1 and 3).
- `tests/test_session_resume.py` (new, 14 tests): everything in the §11.2 S2 list. It also checks that every saved event is on disk before the frontend sees it, and that the history line is there at `turn_completed`. It checks that a failing fsync is reported before the terminal event, that a construction failure releases the lock, and that full turns come back only to the model that made them (deviation 1). Three deliberate code mutations each failed a test, so the tests can catch these regressions: frontend before disk, ignoring the per-line model, and not restoring `seq`.
- `tests/test_core_misc.py`: `"session_resumed"` added to the event-type set (the only existing test changed).

**Tests.** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`: **308 passed, 1 skipped** (was 294; +14 new; the skip is still the POSIX-only permissions test).

**Live smoke test** (gpt-6-luna, reasoning `low`, `full-auto`, temp workspaces; each step a separate process; script in the session scratchpad, not the repo). Total **$0.0118**.
1. `prune_history=True`, no web: "favourite colour is teal" and "17 * 3" (answer `51`), close, then resume in a new process and ask "What did I ask you first?". Answer: "My favourite colour is teal. Reply with just: noted." `session_resumed.history = "pruned"`, `restored_items = 6`. The resumed round had **1631 of 1672 input tokens cached**: same day and same config give the same cache key, so the cache was warm across processes. Cost $0.0002.
2. `prune_history=False`, web search on: t1 `glob_files` + `read_file`; t2 one web search + `glob_files` + `run_command`. Resumed in a new process: `history = "full"`, 14 restored items holding `reasoning` (with `encrypted_content`), `function_call`/`function_call_output`, `web_search_call` and `message` items, with `rs_`/`fc_`/`ws_`/`msg_` ids from the earlier process. **The API accepted them.** The answer quoted the first message exactly, with 6441 of 6584 input tokens cached. Cost $0.0115, mostly the $0.01 search fee. §5.2 is unchanged; the "always restore `record`" fallback was not needed.

**Bench T6** (`run_bench.py --agent v3 --runs 1 --tasks T6 --label s2guard`, gpt-6-luna, medium): **PASS**, rounds 2, tools 3, web 0, $0.0008, **`files_changed=[]`**. That matches the earlier T6 runs (`[]`), so a store-less `Session` writes nothing into the workdir. Results: `bench/results/20261017-122218_v3_s2guard.jsonl` and `bench/results/events/20261017-122218_v3_s2guard_T6_r1.jsonl`.

**Deviations from the spec, with reasons.**
1. **Turn lines record their model, and restore decides per line** (`sessions.py`: `"model"` in each `kind: "turn"` line, taken from the recorder's meta). §5.2 decides once per session from `SavedSession.model`, the model at the last save. That breaks for a mixed session. Example: a session that keeps full turns runs t1–t2 on model A, then is resumed with `--model B` (t1–t2 restored pruned) and runs t3 full on B. On the next resume with B, the session-level rule would send A's encrypted reasoning items from t1–t2 to B. The per-line rule restores a line's `items` only when `prune_history` is off and the line's model equals the current model, and uses `record` otherwise. Lines without `model` (none outside tests) fall back to `SavedSession.model`. Known edge: after A → resume B → resume A, t1–t2 come back full to A (valid, more detail than the B process had) and t3 comes back pruned. **For S5:** the recorder must update `meta["model"]` on `config_changed` (already in S5's list), or the lines after a mid-session model change are tagged with the old model.
2. **`session_resumed.history`** is `"full"` when at least one restored turn went back in its full form (`items` used where `record` exists), else `"pruned"`. A pruning session therefore reports `"pruned"`, and a full session resumed on another model, or with pruning on, also reports `"pruned"`.
3. **`SessionRecorder._safely` catches `Exception`, not only `OSError`.** A recorder bug, or a non-JSON value somewhere, now becomes one `session_save_failed` notice instead of an exception inside `_commit`, which would crash the turn and leave history uncommitted. This is the "a recorder error must never fail a turn" rule.
4. **When `session_save_failed` is emitted** (§5.4 does not say). It comes right after the event whose write failed has been delivered, so `seq` order holds. When the history line (`on_commit`) fails, it comes before the terminal event. When the recorder starts disabled (an unwritable folder at `open()`) or fails during interrupted-turn recovery, it comes right after `session_started`. The message is `Saving stopped: <recorder.error>. The session continues unsaved.`, where `recorder.error` names the session id, folder and OS error.
5. **`SessionResumed` field defaults.** `title`, `created` and `turns_total` are required; the rest have defaults (`history="pruned"`, empty lists/dicts, `None`), so `event_from_dict` accepts a shorter line from a future version. `turns_total` and `turns` include a recovered interrupted turn (outcome `interrupted`, `ts` = recovery time), since it is now a turn line in history.
6. **Recovered-turn details.** The replay uses the config's `web_search_fee_usd`, while S1's meta rebuild uses the default fee; they are equal unless the fee is overridden. It also counts `parallel_groups`, which the rebuild does not. `on_commit(outcome="interrupted")` writes `meta.json` at once, so a resume that recovers a turn records the resumed config's model and reasoning even if the user quits without a turn. S1's "a bare open changes nothing" still holds when nothing is recovered.
7. **Restored totals can differ in the last rounded digit.** `meta.totals` sums the rounded per-turn stats, while an unbroken process sums raw floats and rounds once. So a float field can differ by about 0.001 (time fields) after a resume. Counts and costs (rounded to 6 places) match. The tests compare with a tolerance.
8. **The workspace is not checked against the store** (§5.1, "the workspace must match the store's"). A store can live under any root (§8), so `Session` cannot tell. S3/S4 build the store with `for_workspace(config.workspace)`, which makes the two match.

**Files.** Only files on the S2 Files line were changed: `agent_v3/session.py`, `agent_v3/events.py`, `agent_v3/sessions.py` (deviations 1 and 3), the new `tests/test_session_resume.py`, and `tests/test_core_misc.py` (event-type set). Nothing in `frontends/`, `model.py` or `bench/` code changed. The bench run only added its two result files.

**Notes for S3.**
- Build the store with `SessionStore.for_workspace(config.workspace)` and pass `resume=` a full id (`store.resolve(ref)` first). Catch `SessionStoreError` around `Session(...)`; nothing has been emitted when it is raised.
- Frontends that ignore unknown event types already cope with `session_resumed`. The CLI renderer and `TranscriptWriter` will need a case for it (and for the `turn_interrupted` and `session_save_failed` notices).

### S1–S2 review (2026-10-17)

A `/code-review high` of `agent-v3-sessions` against `master` found 8 issues. All 8 are fixed, and one owner addition (an `open()` retry) is built. Each regression test below was run against the S2 code (HEAD `session.py` and `sessions.py`) and failed there for the reason given.

**Findings.**
1. **Rebuilt totals dropped a committed turn that had no terminal event** (`_meta_from_logs`). Only `interrupted` lines had their logged stats added, so a crash between the history line's fsync and `turn_completed` lost that turn's billed rounds from the totals for good. *Fix:* the rebuild now walks the turn lines in commit order. Each line adds its terminal event's stats, or `_logged_stats` when it has none. This is also the order the live recorder adds them in. *Test:* `test_a_commit_without_its_terminal_event_keeps_its_costs_when_meta_is_rebuilt` (old: `rounds, tool_calls == (2, 2)`, not `(3, 3)`).
2. **`delete()` released the lock before `rmtree`.** *Fix:* every file except `lock` is removed while the lock is held (each unlink retried on Windows `PermissionError`). Then the lock is released, and `lock` and the folder are removed best-effort: a folder left with only `lock` has no logs, so it is not listed and not loadable. A failure while the lock is held raises `SessionStoreError` naming the session, not a raw `OSError`. *Test:* `test_delete_removes_the_logs_before_it_releases_the_lock` opens the session at the moment the lock is released and expects `SessionNotFound` (old: the open succeeded, and on Windows `rmtree` then failed with `PermissionError` on `events.jsonl`).
3. **`prune_history` was guessed when meta.json was rebuilt.** *Fix (owner decision):* every turn line now records `prune_history`, the same way as the per-line `model` from S2. The rebuild takes it from the last turn line, or `True` if no line has it (no turn line yet, or a line written before this change). `session_started.config` and `config.summary()` are unchanged. This replaces S1 deviation 10. *Test:* `test_a_rebuilt_meta_takes_prune_history_from_the_last_turn_line`: a `prune_history=False` session whose only turn failed rebuilds as `False`, and after a resume with pruning on and one more turn it rebuilds as `True` (old: `True` in the first case).
4. **and 7. Save-failure notice placement.** *Fix (owner decision):* `_emit` is now the only caller of `_report_save_failure`; the calls in `_save_commit` and `new_conversation` are gone. On resume, `Session.__init__` emits `session_started`, `session_resumed` and the `turn_interrupted` notice with `_hold_save_failure` set, and clears it for the last of them. So a failure at `open()` or during recovery is reported after the whole group (§5.5, §7). *Test:* `test_a_save_failure_on_resume_is_reported_after_the_resume_events` covers a failing fsync during recovery (`started, resumed, notice(turn_interrupted), notice(session_save_failed)`) and a lock file that cannot be opened (`started, resumed, notice(session_save_failed)`). Old order: `started, notice(save_failed), resumed`. **Behaviour change:** when a turn's history line fails, the notice now comes right *after* its terminal event, not before. This replaces S2 deviation 4. `test_a_failing_fsync_is_reported_before_the_terminal_event` is renamed `…_right_after_the_terminal_event` and its expected order is swapped.
5. **`_logged_stats` re-implemented the stat counting.** *Fix:* new `agent_v3/stats.py` (88 lines) holds `TurnStats`, which gains `from_dict()` and a `cost_usd` property, and `StatsCounter(web_fee_usd).observe(event)`. `_Turn` subclasses `StatsCounter` and adds only its activity tracking. `_logged_stats(events, turn_id, web_fee_usd)` replays the turn's logged dicts through `event_from_dict` and a `StatsCounter`, the same way recovery does, so `parallel_groups` is counted. `meta["totals"]` is now a `TurnStats` in memory and `to_dict()` on disk, which removes `_add_stats`, `_rounded` and `_cost`. `session.py` imports `TurnStats` from `stats`, so `from agent_v3.session import TurnStats` still works. **The web fee is saved:** each turn line also records `web_search_fee_usd` (from `meta`, which now stores it with the other settings), and the rebuild prices a line's searches with that fee. Without it a rebuild cannot know a non-default fee, because `config.summary()` does not include it. Lines without the fee fall back to `AgentConfig`'s default. This replaces S1 deviation 8 and S2 deviation 6. *Test:* `test_totals_rebuilt_from_the_logs_equal_the_live_ones` recovers a turn with a search at fee 0.05 and a two-call parallel group, then deletes meta.json and expects identical totals (old: `web_cost_usd` 0.01, and no `parallel_groups`).
6. **Listing created `lock` files.** *Fix:* `_FileLock(path, create=False)` is used by `_status`. A missing lock file means "not in use", and nothing is written. `open()` still creates it. *Test:* `test_listing_and_loading_never_create_a_lock_file` checks `list()`, `load()` and `resolve("latest")` on a folder without `lock` (old: the file was recreated).
8. **`SavedSession.model` and `.prune_history` removed.** Only `info` and `saved_config` remain. `_restore` falls back to `saved.info.model` for a turn line without a `model` tag. The one test that read the removed fields now reads `info.model` (`saved_config` was already checked).

**Owner addition: `open()` retries a lock conflict.** `_take_lock` tries `_FileLock` 5 times, 25 ms apart (about 100 ms), before `SessionInUse`. This outlasts a `list()`/`load()` status probe from another process, so S1 deviation 16's spurious `SessionInUse` is fixed. `delete()` uses the same retry. A session that really is open now takes about 100 ms to report `SessionInUse`. *Test:* `test_open_waits_out_a_momentary_status_probe` holds a probe lock released after 30 ms, then checks that a held lock still fails after ≥ 70 ms (old: `SessionInUse` at once).

**Tests.** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`: **315 passed, 1 skipped** (was 308; +7 new: 5 in `test_sessions_store.py`, now 30, and 2 in `test_session_resume.py`, now 16; the skip is still the POSIX-only permissions test). Changed existing tests: the fsync notice-order test (finding 4), `test_load_restores_counters_and_turn_lines` (finding 8), and `test_missing_or_corrupt_meta_is_rebuilt_from_the_logs`, which passes the fee to `_logged_stats`.

**Size.** `sessions.py` is **661 lines** (was 645): stats helpers moved out, while the delete, lock-retry and line-tag code came in. `session.py` is 486 (was 537), and `stats.py` is new at 88.

**Files.** `agent_v3/session.py`, `agent_v3/sessions.py`, the new `agent_v3/stats.py`, `tests/test_sessions_store.py`, `tests/test_session_resume.py`. `events.py` and `jsonl.py` needed no change. Not committed.

**Spec text now out of date** (left as written; this entry overrides it): §4.3's line example lacks `model`, `prune_history` and `web_search_fee_usd`. §4.6 says `delete` "closes the handle and removes the folder". §5.1's `SavedSession` lists `prune_history` and `model`. *(Updated 2026-10-17: §3, §4.2, §4.3, §4.4, §4.6, §5.1, §5.2 and §5.4 now describe the code as built after S1, S2 and this review.)*

### Phase S3 — CLI and export (2026-10-17)

**Built.**
- `frontends/args.py`: `--model` and `--reasoning` now default to `None` (their help text names the real default). `config_from_args` fills the `AgentConfig` defaults, so its result is unchanged. New `explicit_settings(args)` returns the typed ones of `{"model", "reasoning"}`. New `add_session_args(p)`: `--resume [REF]` (`nargs="?"`, bare = `""`), `--continue` / `-c` (dest `continue_`) and `--no-save`. The server already calls `add_config_args`, so it picks up the new defaults without a change (it does not call `add_session_args` yet; that is S4).
- `frontends/transcript.py`: `export_transcript(events_path, out_path)` replays the log into `<out>.tmp` and `os.replace`s it onto `out_path`, so the file is always rebuilt from scratch. A second `session_started` writes `> RESUMED <date> (model=…, reasoning=…, approval=…)` instead of a second header, and the usage block's model follows the latest `session_started`. `session_resumed` has no handler (ignored). The `turn_interrupted` and `session_save_failed` notices go through the existing `> NOTICE` line.
- `frontends/commands.py` (new): `python -m agent_v3 sessions [--workspace] [--limit N]`, `sessions delete REF [REF …]`, `export REF [-o PATH] [--workspace]`, plus `format_sessions()` (the §4.5 listing, shared with `/sessions`) and `reconfigure_utf8()`. Errors go to stderr with exit 2.
- `frontends/cli.py`:
  - `--transcript` is a hidden argument that exits 2 with the hint. `--no-save` with `--resume`/`--continue` exits 2. The `--help` epilog says where sessions are saved.
  - `main()` sends `sessions` and `export` to `commands.main`. Otherwise it builds `SessionStore.for_workspace(config.workspace)` (None with `--no-save`) and resolves `--continue` / `--resume REF` / `--resume` (list and ask) with `store.resolve`. It builds the session through `SessionOpener`, catching `SessionStoreError` around it. An unknown or in-use ref prints to stderr and exits 2 (`--continue` adds "use --resume to pick another"). `--continue` with no sessions prints a dim note and starts a new one.
  - New `SessionOpener(store, on_event, launch, explicit, model_of)`: a new session gets the launch config; a resumed one gets `config_for_resume(launch, store.load(id).info, explicit)`. `Cli.__init__` gains `store`, `open_session`, `launch_config` and `explicit`. With no `open_session` the default is a `SessionOpener` that reuses the current session's model adapter (so `run_cli(...)` tests work); `main` passes one that builds a fresh adapter per session.
  - Commands: `/sessions [all]` (10 newest, then `… N more: /sessions all`), `/resume [N|REF]`, `/export [PATH]`, and `/new`, which now always opens a new session. The CLI never calls `new_conversation()`; `/clear` is the unknown-command hint, which lists the new commands. The `/resume|/export|/sessions` match takes an optional argument; the bare-word rule is unchanged, so `/new file please` goes to the model.
  - `_on_session_resumed` prints the recap line, one dim line for each setting that differs from the saved one, and the last exchange (answer clipped to 15 lines). The banner's hint line lists the new commands, and a fourth dim line says where the session is saved (only when saving is on). Exit: after the usage block, `Session saved: <id> - resume with: python -m agent_v3 [--workspace W] --resume <id without s_>`, only for a session that was saved and has an events file.
  - The sink warning now reads "could not write the event log".
- `agent_v3_claude_plan.md`: one-line pointers at the run command (§3), the flag list (§4), §10.1 and §10.3.
- `tests/test_cli_sessions.py` (new, 34 tests) covers the whole §11.2 S3 list except the S5 item: the `--transcript` and `--no-save` exits; option C through `main()` (restored model and reasoning, approval never, typed flags winning, the recap naming each difference, `/new` using the launch config); `explicit_settings` and `config_for_resume` units; `--resume` without REF, `--continue` (with and without sessions, and in use); `/resume N` with the history in the next request; `/new` with and without a factory and never calling `new_conversation`; `/clear`; `/export` to the default path and a given path, equal to a direct `TranscriptWriter` replay; the `RESUMED` line; the three subcommands; `/sessions` with 14 sessions (10, `… 4 more`, then all 14); the interrupted notice; the exit hint; `--no-save` leaving no `.agent_v3`.
- `tests/test_frontends.py`: the one warning string.

**Tests.** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`: **349 passed, 1 skipped** (was 315; +34, all new; the skip is still the POSIX-only permissions test). No parametrize used. No existing test changed except the warning string.

**Deviations from the spec, with reasons.**
1. **`/model`, `/reasoning` and `/approval` are not built.** §6.2's regex lists them, but §10 puts them in S5 (they need `update_config`). Today they fall to the bare-word rule (unknown-command hint) or, with an argument, go to the model like any text. S5 should add them to `ARG_COMMANDS`.
2. **`/resume` with no argument: Enter stays in the current session**, not "new session" (that is `--resume` at startup, where there is nothing to stay in). Ending the current session by pressing Enter would surprise a user who typed `/resume` by mistake. `/new` already does that.
3. **The new session is built before the old one is closed** (`_switch`). A failed `/resume` (in use, not found) then leaves the current session untouched. The old session's usage block is not printed at a switch; the exit block covers the session that is open at the end.
4. **List numbers.** `/resume N` indexes the last listing printed in this process (`/sessions` shows 10, `/sessions all` shows all), or the full list when none was printed. A digit string longer than 3 characters that is out of range is tried as an id prefix, since `1234` can also be hex.
5. **Banner.** §9 says the banner's third line names where sessions go; the third line already holds the command hint, so the saving note is a fourth dim line, shown only when the session is being saved.
6. **Listing ids** show the first 12 characters (`s_` plus 10 hex) as in §4.5's example. Any shown prefix resolves. The current session is marked `*` in the first column; only the other sessions get `(interrupted)` / `(in use)`, since the open session always looks in use to its own process. Non-TTY output uses `...` for `…` (the title's clip mark and the `… N more` line), so the §11.2 "`… 4 more`" text is `... 4 more` under test.
7. **Exit hint.** It uses the output separator (` - ` on non-TTY), adds `--workspace W` when the workspace is not the current folder, and is decided from `saved` read **before** `close()` (a closed recorder reports unhealthy) plus the existence of `events.jsonl`.
8. **Small additions.** `--resume` and `--continue` together exit 2. `commands.reconfigure_utf8()` replaces the inline loop in `cli.main` (same behaviour, shared by the subcommands). `main` passes `input_fn=input` so tests can patch `builtins.input`. `format_sessions` lives in `commands.py` because `formatting.py` is outside the S3 Files line.
9. **Notices.** `session_save_failed` and `turn_interrupted` need no special case in the CLI or `TranscriptWriter`: the existing generic notice handlers already print and log them.
10. **`sessions.py`, `session.py`, `stats.py`, `stdio_server.py` and `bench/` were not touched.** No bug found in `sessions.py`.

**Not tested here (needs a person at a console):** TTY colour and spinner behaviour with the new lines, Ctrl+C during a resumed turn, and killing the terminal mid-turn. See the manual checklist in the hand-over message.

**Files.** `agent_v3/frontends/args.py`, `cli.py`, `transcript.py`, new `commands.py`, new `tests/test_cli_sessions.py`, `tests/test_frontends.py` (one string), `agent_v3_claude_plan.md` (four one-line pointers), and this log. Not committed.

### S3 follow-up fixes (2026-10-17)

Found while running the S3 manual checklist (piped and in a real console; all checks passed, about $0.003 of API calls). Three fixes in `frontends/cli.py` and `frontends/commands.py`:
1. **`/sessions` under `--no-save` lists the saved sessions** instead of "nothing to list". `--no-save` only stops writing, as the server's `list_sessions` does (§7.2). The CLI builds a read-only `SessionStore.for_workspace(...)` for listing when it has no saving store; listing creates no files. `/resume` and `/export` still refuse under `--no-save`.
2. **The `--continue` "in use" error** no longer reads "…(pid N).; use --resume…"; it is now "…(pid N); use --resume to pick another."
3. **The listing's cost column** uses `fmt_cost` (4 decimals below $0.01, so `$0.0003` instead of `$0.000`) and is one character wider; the header moved with it.

Tests: `test_commands_without_saving_say_so` no longer expects `/sessions` to refuse; the header assertion in `test_listing_format_flags_and_ascii` and the in-use message test were updated; 3 tests added. Each new or changed assertion fails on the S3 code. **352 passed, 1 skipped.**

Not changed, noted for later: subcommands must come first (`python -m agent_v3 sessions --workspace X`; `--workspace X sessions` is rejected, as §6.1 specifies). Every reopen of a session, even one only to export it, adds a `> RESUMED` line to its transcript. Rich Markdown joins single line breaks in answers (pre-existing v3 behaviour).

### Phase S4 — stdio server (2026-10-19)

**Built.**
- `frontends/stdio_server.py`:
  - `StdioServer(config, model=None, *, stdin, stdout, store=None, resume=None, explicit=frozenset())`. The extra arguments all default, so the 19 original tests construct it as before. `store=None` means "not saved" (`--no-save`, and every in-process test); `resume` is a full id.
  - `_open(resume_id)` builds a `Session` the way `cli.SessionOpener` does: a resume reads `config_for_resume(launch, load(id).info, explicit)`, a new session gets the launch config, and an injected model adapter is reused for every session (`None`: each `Session` builds its own). `_switch` builds the new session first, then swaps and closes the old one, so a failed `resume_session` leaves the current session untouched.
  - New messages: `list_sessions`, `resume_session`, `new_session`, `export_session`, `delete_session`. New error codes `not_found`, `ambiguous`, `in_use`, `saving_disabled`, raised through a small `ProtocolError(code, message)` that `_handle_line` turns into an `error` line.
  - `list_sessions` returns every session with `total` (`limit` only slices). The row is `dataclasses.asdict(SessionInfo)` (so it carries `reasoning`) with the open session's `status` set to `current`. `export_session` replays the log through `export_transcript` into a temp folder and returns the text.
  - Start-up: `add_session_args` is wired into `build_parser`. `main` builds `SessionStore.for_workspace(...)` (None with `--no-save`), resolves `--continue` / `--resume REF` with `store.resolve`, and passes `explicit_settings(args)`. A resolve error or a `SessionStoreError` from `Session(...)` prints to stderr and exits 2 with nothing on stdout; the `--continue` in-use message adds "use --resume to pick another" as the CLI does. `--continue` with no saved session starts a new one (logged at info level).
- `agent_v3_claude_plan.md` §10.2: appended a "Saved sessions" block after the "Rules a client can rely on" list (start-up flags, the five-row message table, examples, the new error codes and the §7.3 rules). Nothing above it was edited.
- `tests/test_stdio_server.py`: 13 tests appended (and nothing else touched: `git diff` shows 376 added lines, 0 removed). Subprocess tests share one workspace through a `start_in` fixture; the rest drive `StdioServer` in-process (`InProc`) so `FakeModelAdapter.requests` shows what a resumed session sends. They cover everything marked S4 in §11.2: the `current` row, `--resume` from a second server (same id, `seq` > 1, `session_resumed` directly after, `t2` next, totals continue), `--continue`, the start-up exits, runtime resume (the next request carries the old history and not the other session's), `busy` / `not_found` / `ambiguous` / `in_use` / `bad_request` with the current session unchanged, `new_session` vs `new_conversation`, `export_session`, `delete_session`, `--no-save` (nothing new on disk, `saving_disabled`, listing and exporting still work), and `list_sessions` without a limit.

**Tests.** `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests -q`: **365 passed, 1 skipped** (was 352; +13, all new; the skip is still the POSIX-only permissions test). The 19 original stdio tests pass unmodified. No parametrize used. The full suite now takes about 90 s (the subprocess tests dominate).

**Deviations and decisions the spec did not settle.**
1. **Switch order.** §7.3 says the old session is closed first. The server builds the new session first and then closes the old one (the CLI's rule, and the brief for this phase), so a failed resume changes nothing. The old session is idle, so `close()` emits nothing, and the two sessions' events still cannot interleave. The two sessions are open together for a moment, which is harmless: different folders, different locks.
2. **`--no-save` and the store.** The server keeps two stores: the saving one (None under `--no-save`) and a reading one (`store or SessionStore.for_workspace(...)`), as the CLI's S3 follow-up does. `list_sessions`, `delete_session` and `export_session` of another session therefore work under `--no-save`; `resume_session` and `export_session` of the open session give `saving_disabled`. `new_session` works and starts another unsaved session. In-process servers built without a store behave the same way.
3. **`export_session` of the open session before its first turn** returns `markdown: ""` rather than an error: the session is saved, it just has no log yet.
4. **Edge cases in `resume_session`.** Giving both `session_id` and `latest`, neither, or a non-boolean `latest` is `bad_request`. `latest: true` is resolved like any ref, so when the open session is the newest saved one it gives `bad_request` ("already the open session") rather than silently resuming an older one. The idle check comes before the `saving_disabled` check. `delete_session` resolves the ref first, then checks idle.
5. **`list_sessions`** rejects a `limit` that is not a positive integer (`bad_request`; `0`, negatives, strings, floats and booleans). The reply carries `reasoning` on each row, because `SessionInfo` has it since S1.
6. **A store failure other than the three named ones** (for example a `delete` that cannot remove a file) is reported as `internal_error` with the store's message. The spec has no code for it, and `internal_error` is already part of v1.
7. **The §10.2 block leaves out the S5 parts.** The "settings changes" and "redrawing a saved session" rules and the `set_config` / `get_session_events` rows are not written yet, since those messages do not exist; S5 appends them. The `session_resumed` example in the table is abbreviated, like the other examples there.
8. **`SessionOpener` is not imported from `cli.py`** (it would pull in the terminal UI and `rich`); `_open` repeats its few lines. `args.py` needed no change: S3 had already added `add_session_args` and `explicit_settings`. `--resume` without REF, and `--resume` together with `--continue`, exit 2 at start-up.

**Files.** `agent_v3/frontends/stdio_server.py`, `tests/test_stdio_server.py` (additions only), `agent_v3_claude_plan.md` §10.2 (append only), and this log. `session.py`, `sessions.py`, `cli.py`, `args.py` and `bench/` were not touched. Not committed.
