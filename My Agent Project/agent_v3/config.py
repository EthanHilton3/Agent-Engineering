from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

APPROVAL_MODES = ("ask", "auto-edit", "full-auto")
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh")
SEARCH_CONTEXT_SIZES = ("low", "medium", "high")


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

    def __post_init__(self):
        self.workspace = Path(self.workspace).expanduser().resolve()
        if self.prompt_path is not None:
            self.prompt_path = Path(self.prompt_path)
        if self.output_dir is not None:
            self.output_dir = Path(self.output_dir)
        for name, value, allowed in (("approval", self.approval, APPROVAL_MODES),
                                     ("reasoning", self.reasoning, REASONING_EFFORTS),
                                     ("search_context_size", self.search_context_size, SEARCH_CONTEXT_SIZES)):
            if value not in allowed:
                raise ValueError(f"{name} must be one of {', '.join(allowed)}; got {value!r}")
        if self.max_rounds < 1:
            raise ValueError("max_rounds must be at least 1")

    def summary(self) -> dict:
        """The JSON-safe subset sent in `session_started` (plan §7)."""
        return {"model": self.model, "reasoning": self.reasoning, "approval": self.approval,
                "workspace": str(self.workspace), "web_search": self.web_search}
