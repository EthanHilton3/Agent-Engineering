"""Talk Past the Guard: a terminal role-play game with a swappable judge.

    python game.py --judge gpt
    python game.py --judge jev --scenario amulet

The rules live in game_engine.py, shared with the web version (server.py).
"""

from __future__ import annotations

import argparse
import random
import sys

from game_engine import ENDINGS, MAX_TURNS, SUSPICION_LIMIT, GameSession, make_judge
from judge_common import Verdict
from scenarios import SCENARIOS
from usage import print_jev_usage, print_usage


def show_debug(verdict: Verdict, show_reasoning: bool):
    note = f" (raw: {verdict.raw_decision})" if verdict.raw_decision != verdict.decision else ""
    print(
        f"   [{verdict.decision}{note} | confidence {verdict.confidence:.2f} | "
        f"persuasion {verdict.persuasiveness:.2f}/3 | out-of-character "
        f"{verdict.out_of_character:.2f} | {verdict.latency_s * 1000:.0f} ms]"
    )
    if verdict.probabilities:
        probs = ", ".join(f"{k} {v:.2f}" for k, v in verdict.probabilities.items())
        print(f"   [probabilities: {probs}]")
    if show_reasoning and verdict.rationale:
        print(f"   [rationale: {verdict.rationale}]")


def play(kind: str, scenario_key: str | None, model: str | None, show_reasoning: bool):
    model, judge = make_judge(kind, model)
    scenario = SCENARIOS[scenario_key] if scenario_key else random.choice(list(SCENARIOS.values()))
    game = GameSession(scenario, judge)

    print(f"\n=== {scenario.title} ===  (judge: {kind}, model: {model})\n")
    print(scenario.setting)
    print(f"Your goal: {scenario.goal}\n")
    print(f"What you know:\n{scenario.player_knows}\n")
    print(f'{scenario.guard}: "{scenario.opening_line}"')

    while not game.outcome:
        print(f"\n(Turn {game.turn + 1}/{MAX_TURNS}, suspicion {game.suspicion}/{SUSPICION_LIMIT})")
        line = input("You: ").strip()
        if not line:
            continue
        if line.lower() in {"quit", "exit"}:
            game.outcome = "walked_away"
            break

        result = game.take_turn(line)
        print(f'\n{scenario.guard}: "{result.reply}"')
        show_debug(result.verdict, show_reasoning)
        if result.closing_line:
            print(f'\n{scenario.guard}: "{result.closing_line}"')

    print(f"\n*** {ENDINGS[game.outcome]} ***\n")

    if kind == "gpt":
        print_usage([(model, u) for u in game.usages if u is not None])
    else:
        print_jev_usage([u for u in game.usages if u])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Talk your way past a guard.")
    parser.add_argument("--judge", choices=["gpt", "jev"], default="gpt")
    parser.add_argument("--scenario", choices=list(SCENARIOS))
    parser.add_argument("--model", help="Override the judge model.")
    parser.add_argument("--show-reasoning", action="store_true", help="Print the GPT judge's rationale.")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # GPT replies use curly quotes
    try:
        play(args.judge, args.scenario, args.model, args.show_reasoning)
    except (KeyboardInterrupt, EOFError):
        print()
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1)
