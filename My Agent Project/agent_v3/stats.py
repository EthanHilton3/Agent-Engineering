"""Turn statistics: `TurnStats` and the counting a turn does from its events.

Shared by the live turn (`session._Turn`) and the saved-session rebuild (`sessions._logged_stats`), so totals
rebuilt from a log equal the ones recorded live.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, fields

from .events import ApprovalResolved, Event, ModelRoundCompleted, ToolStarted, WebAction


@dataclass
class TurnStats:
    rounds: int = 0
    tool_calls: int = 0
    parallel_groups: int = 0
    web_searches: int = 0
    web_opens: int = 0
    web_finds: int = 0
    input_tokens: int = 0
    cached_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    model_cost_usd: float = 0.0
    web_cost_usd: float = 0.0
    elapsed_s: float = 0.0
    model_wait_s: float = 0.0
    tool_wait_s: float = 0.0
    approval_wait_s: float = 0.0

    @classmethod
    def from_dict(cls, data) -> "TurnStats":
        """The known numeric fields of `data` (a `to_dict()`, possibly from disk); anything else is ignored."""
        data = data if isinstance(data, dict) else {}
        return cls(**{f.name: v for f in fields(cls)
                      if isinstance(v := data.get(f.name), (int, float)) and not isinstance(v, bool)})

    def add(self, other: "TurnStats") -> None:
        for f in fields(self):
            setattr(self, f.name, getattr(self, f.name) + getattr(other, f.name))

    def to_dict(self) -> dict:
        out = {}
        for f in fields(self):
            v = getattr(self, f.name)
            out[f.name] = round(v, 6 if f.name.endswith("_usd") else 3) if isinstance(v, float) else v
        return out

    @property
    def cost_usd(self) -> float:
        return round(self.model_cost_usd + self.web_cost_usd, 6)


class StatsCounter:
    """Counts one turn's stats from its events, in order. Time spent in tools and the turn's elapsed time are
    measured by the live turn, not counted here."""

    def __init__(self, web_fee_usd: float):
        self.stats = TurnStats()
        self.web_fee_usd = web_fee_usd
        self._group_sizes: Counter = Counter()

    def observe(self, ev: Event) -> None:
        s = self.stats
        if isinstance(ev, ModelRoundCompleted):
            s.rounds += 1
            s.input_tokens += ev.input_tokens
            s.cached_tokens += ev.cached_tokens
            s.output_tokens += ev.output_tokens
            s.reasoning_tokens += ev.reasoning_tokens
            s.model_cost_usd += ev.cost_usd or 0.0
            s.model_wait_s += ev.duration_s
        elif isinstance(ev, WebAction):
            if ev.kind == "search":
                s.web_searches += 1
                s.web_cost_usd = s.web_searches * self.web_fee_usd
            elif ev.kind == "open_page":
                s.web_opens += 1
            elif ev.kind == "find_in_page":
                s.web_finds += 1
        elif isinstance(ev, ToolStarted):
            s.tool_calls += 1
            self._group_sizes[ev.group] += 1
            s.parallel_groups = sum(1 for n in self._group_sizes.values() if n >= 2)
        elif isinstance(ev, ApprovalResolved):
            s.approval_wait_s += ev.wait_s
