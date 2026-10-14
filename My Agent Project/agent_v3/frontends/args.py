"""Command-line flags shared by every frontend: the ones that build an `AgentConfig`."""
from __future__ import annotations

import argparse
from pathlib import Path

from ..config import APPROVAL_MODES, REASONING_EFFORTS, SEARCH_CONTEXT_SIZES, AgentConfig


def add_config_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--model", default=AgentConfig.model)
    p.add_argument("--reasoning", default=AgentConfig.reasoning, choices=REASONING_EFFORTS)
    p.add_argument("--approval", default=AgentConfig.approval, choices=APPROVAL_MODES,
                   help="ask: approve edits and commands; auto-edit: approve commands only; full-auto: approve nothing.")
    p.add_argument("--workspace", type=Path, default=None, help="Folder the agent works in (default: current folder).")
    p.add_argument("--no-web", action="store_true", help="Turn web search off.")
    p.add_argument("--search-context-size", choices=SEARCH_CONTEXT_SIZES, default=AgentConfig.search_context_size)
    p.add_argument("--allow-domain", action="append", metavar="DOMAIN", help="Limit web search to this domain (repeatable).")
    p.add_argument("--max-rounds", type=int, default=AgentConfig.max_rounds)
    p.add_argument("--max-turn-cost", type=float, default=None, metavar="USD", help="Stop a turn after this much spend.")
    p.add_argument("--no-parallel-reads", action="store_true")
    p.add_argument("--no-prune-history", action="store_true")
    p.add_argument("--no-dedupe-reads", action="store_true")
    p.add_argument("--no-lenient-edit", action="store_true")
    p.add_argument("--prompt", type=Path, default=None, help="Use this file instead of the bundled system prompt.")


def config_from_args(args: argparse.Namespace) -> AgentConfig:
    return AgentConfig(
        model=args.model, reasoning=args.reasoning, approval=args.approval,
        workspace=args.workspace or Path.cwd(), web_search=not args.no_web,
        search_context_size=args.search_context_size, web_allowed_domains=args.allow_domain,
        max_rounds=args.max_rounds, max_turn_cost_usd=args.max_turn_cost,
        parallel_reads=not args.no_parallel_reads, prune_history=not args.no_prune_history,
        dedupe_reads=not args.no_dedupe_reads, lenient_edit_match=not args.no_lenient_edit,
        prompt_path=args.prompt)
