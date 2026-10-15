"""Plain-text formatting shared by the CLI and the transcript. Works on event/stats dicts, no I/O."""
from __future__ import annotations

from ..tools.files import plural


def fmt_tokens(n: int) -> str:
    return str(n) if n < 1000 else f"{n / 1000:.1f}k"


def fmt_cost(cost: float | None, places: int | None = None) -> str:
    """`$0.031` (3 decimals from a cent up, else 4); pass `places` to force a precision."""
    if cost is None:
        return "$?"
    if places is None:
        places = 3 if cost >= 0.01 else 4
    return f"${cost:.{places}f}"


def round_summary(d: dict, sep: str = " · ") -> str:
    """`41.2k in (39.0k cached) · 812 out (240 reasoning) · 4.1s · $0.0213` from a model_round_completed dict."""
    return sep.join([f"{fmt_tokens(d['input_tokens'])} in ({fmt_tokens(d['cached_tokens'])} cached)",
                     f"{fmt_tokens(d['output_tokens'])} out ({fmt_tokens(d['reasoning_tokens'])} reasoning)",
                     f"{d['duration_s']:.1f}s", fmt_cost(d.get("cost_usd"), 4)])


def turn_cost(stats: dict) -> float:
    return stats.get("model_cost_usd", 0.0) + stats.get("web_cost_usd", 0.0)


def work_summary(stats: dict) -> list[str]:
    """Round / tool-call / web-search counts; everything but rounds is omitted when zero."""
    parts = [plural(stats.get("rounds", 0), "round")]
    if stats.get("tool_calls"):
        calls = plural(stats["tool_calls"], "tool call")
        if stats.get("parallel_groups"):
            calls += f" ({plural(stats['parallel_groups'], 'parallel group')})"
        parts.append(calls)
    if (searches := stats.get("web_searches")):
        parts.append(f"{searches} web search" + ("" if searches == 1 else "es"))
    return parts


def completion_line(stats: dict, sep: str = " · ") -> str:
    """`Completed in 12.4s · 4 rounds · 9 tool calls (2 parallel groups) · $0.031`"""
    return sep.join([f"Completed in {stats.get('elapsed_s', 0.0):.1f}s", *work_summary(stats),
                     fmt_cost(turn_cost(stats))])


def format_usage(model: str, totals: dict) -> str:
    """Session usage block in the shape of v2's `print_usage`, from summed turn stats."""
    t = totals
    model_cost, web_cost = t.get("model_cost_usd", 0.0), t.get("web_cost_usd", 0.0)
    lines = [" Usage ".center(30, "-"), model.center(30, "~"),
             f"Input (tokens): {t.get('input_tokens', 0)}",
             f"Cached (tokens): {t.get('cached_tokens', 0)}",
             f"Output (tokens): {t.get('output_tokens', 0)}",
             f"Reasoning (tokens): {t.get('reasoning_tokens', 0)}",
             f"{model} cost (USD): ${model_cost:.6f}", "~" * 30,
             f"Rounds: {t.get('rounds', 0)}", f"Tool calls: {t.get('tool_calls', 0)}",
             f"Web searches: {t.get('web_searches', 0)}",
             f"Web search cost (USD): ${web_cost:.6f}",
             f"Total cost (USD): ${model_cost + web_cost:.6f}"]
    return "\n".join(lines)
