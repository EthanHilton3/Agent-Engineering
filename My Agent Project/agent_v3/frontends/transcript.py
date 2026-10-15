"""Transcript (plan §10.3): an event consumer that appends v2-compatible Markdown, plus one line per round.

It accepts event objects or the dicts from an event log, so a transcript can be rebuilt from a recorded session.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .formatting import fmt_cost, format_usage, round_summary, turn_cost, work_summary

_SUMMED = ("rounds", "tool_calls", "parallel_groups", "web_searches", "web_opens", "web_finds", "input_tokens",
           "cached_tokens", "output_tokens", "reasoning_tokens", "model_cost_usd", "web_cost_usd", "elapsed_s")


def _short(value, limit: int = 80) -> str:
    """Shorten long tool arguments (like a whole file's content), as v2 did."""
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + "...'"


def _first_line(text: str) -> str:
    lines = (text or "").strip().splitlines()
    return lines[0] if lines else ""


class TranscriptWriter:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.model = ""
        self.totals: dict = {k: 0 for k in _SUMMED}
        self._calls: dict[str, dict] = {}          # call_id -> tool_started
        self._requests: dict[str, dict] = {}       # request_id -> approval request
        self._started = False
        self._closed = False
        self._file = None                          # opened on the first line, so an unused writer creates no file

    # -- public --------------------------------------------------------------------------------

    def write(self, event) -> None:
        d = event if isinstance(event, dict) else event.to_dict()
        handler = getattr(self, f"_on_{d.get('type')}", None)
        if handler is not None and not self._closed:
            handler(d)

    __call__ = write

    def close(self) -> None:
        """Append the usage block (once) and close the file."""
        if self._closed:
            return
        if self._started:
            self._log("```\n" + format_usage(self.model, self.totals) + "\n```")
        self._closed = True
        if self._file is not None:
            self._file.close()

    # -- helpers -------------------------------------------------------------------------------

    def _log(self, text: str) -> None:
        if self._file is None:
            self._file = self.path.open("a", encoding="utf-8")
        self._file.write(text + "\n")
        self._file.flush()                         # the transcript is readable while the session runs

    def _add_stats(self, stats: dict) -> None:
        for k in _SUMMED:
            self.totals[k] += stats.get(k, 0) or 0

    @staticmethod
    def _footer(stats: dict) -> str:
        parts = [f"{stats.get('elapsed_s', 0.0):.2f} seconds", *work_summary(stats), fmt_cost(turn_cost(stats))]
        return f"*({', '.join(parts)})*\n"

    # -- events --------------------------------------------------------------------------------

    def _on_session_started(self, d: dict) -> None:
        cfg = d.get("config", {})
        self.model = cfg.get("model", "")
        self._started = True
        try:
            when = datetime.fromisoformat(d["ts"]).astimezone()
        except (KeyError, ValueError):
            when = datetime.now()
        self._log(f"\n---\n\n# Transcript {when:%Y-%m-%d %H:%M} (model={self.model}, "
                  f"reasoning={cfg.get('reasoning')}, approval={cfg.get('approval')}, "
                  f"web_search={cfg.get('web_search')}, workspace={cfg.get('workspace')})\n")

    def _on_turn_started(self, d: dict) -> None:
        self._log(f"**USER:** {d['user_message']}\n")

    def _on_tool_started(self, d: dict) -> None:
        self._calls[d["call_id"]] = d

    def _on_tool_completed(self, d: dict) -> None:
        started = self._calls.pop(d["call_id"], None)
        args = started["args"] if started else None
        if isinstance(args, dict):
            shown = ", ".join(f"{k}={_short(v)}" for k, v in args.items())
        else:
            shown = "" if args is None else _short(args)
        result = d.get("summary") or _first_line(d.get("output", ""))
        if not d.get("ok"):
            result = f"FAILED ({d.get('error_code')}): {result}"
        self._log(f"> TOOL: `{d['name']}({shown})` -> {_short(result, 120)}\n")

    def _on_web_action(self, d: dict) -> None:
        label = "web_search" if d["kind"] == "search" else d["kind"]
        self._log(f"> TOOL: `{label}({d['detail']})`\n")

    def _on_model_round_completed(self, d: dict) -> None:
        self._log(f"> ROUND {d['round']} · {round_summary(d)}\n")

    def _on_model_retry(self, d: dict) -> None:
        self._log(f"> RETRY round {d['round']} (attempt {d['attempt']}, in {d['delay_s']:.1f}s): {d['reason']}\n")

    def _on_notice(self, d: dict) -> None:
        self._log(f"> NOTICE ({d['level']}, {d['code']}): {d['message']}\n")

    def _on_approval_requested(self, d: dict) -> None:
        req = d["request"]
        self._requests[req["request_id"]] = req

    def _on_approval_resolved(self, d: dict) -> None:
        req = self._requests.pop(d["request_id"], {})
        what = req.get("command") or ", ".join(req.get("paths", []))
        feedback = f" — {d['feedback']}" if d.get("feedback") else ""
        self._log(f"> APPROVAL: {req.get('title', d['request_id'])} ({what if len(what) <= 80 else what[:80] + '...'}) "
                  f"-> {d['decision']} (by {d['by']}){feedback}\n")

    def _on_turn_completed(self, d: dict) -> None:
        stats = d.get("stats", {})
        self._add_stats(stats)
        out = f"**AGENT:** {d['text']}\n\n{self._footer(stats)}"
        if d.get("stop_reason", "done") != "done":
            out += f"\n> STOPPED EARLY: {d['stop_reason']}\n"
        self._log(out)
        if d.get("sources"):
            self._log("**Sources:**\n" + "\n".join(
                f"{n}. [{s['title']}]({s['url']})" for n, s in enumerate(d["sources"], 1)) + "\n")

    def _on_turn_cancelled(self, d: dict) -> None:
        stats = d.get("stats", {})
        self._add_stats(stats)
        self._log(f"**CANCELLED** by the user.\n\n{self._footer(stats)}")

    def _on_turn_failed(self, d: dict) -> None:
        stats = d.get("stats", {})
        self._add_stats(stats)
        self._log(f"**FAILED** ({d['error_code']}): {d['message']}\n\n{self._footer(stats)}")
