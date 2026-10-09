from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AgentConfig:
    model: str = "gpt-5.6-luna"            # same default as v2; revisit after benchmarking
    reasoning: str = "none"                 # none|low|medium|high
    workspace: Path = field(default_factory=Path.cwd)
    approval: str = "ask"                   # ask | auto-edit | full-auto
    web_search: bool = True
    search_context_size: str = "medium"     # low|medium|high
    web_allowed_domains: list[str] | None = None
    web_search_fee_usd: float = 0.01        # per *search* action; external pricing, not logic
    max_rounds: int = 40
    max_turn_seconds: int = 1200
    max_turn_cost_usd: float | None = None
    max_parallel_reads: int = 8
    read_max_lines: int = 250
    read_max_chars: int = 16_000
    tool_output_max_chars: int = 12_000
    command_default_timeout: int = 60
    command_max_timeout: int = 600
    # Benchmark ablation switches; all True in normal use.
    parallel_reads: bool = True
    prune_history: bool = True
    dedupe_reads: bool = True
    lenient_edit_match: bool = True
    store: bool = False                     # do not persist responses on OpenAI
    prompt_path: Path | None = None         # override bundled prompt.md
    output_dir: Path | None = None          # default: <workspace>/.agent_v3/outputs
