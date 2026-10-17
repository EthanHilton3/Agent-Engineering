"""Game rules shared by the terminal game and the web server.

Game state (turns, suspicion, outcome) lives here in code. The judges only
decide how the guard reacts to one line at a time.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, Callable

from judge_common import Verdict
from scenarios import GUARD_LINES, Scenario

MAX_TURNS = 5
SUSPICION_LIMIT = 3

ENDINGS = {
    "passed": "You slip past the guard. Success!",
    "arrested": "You've been arrested. Pay the fine or serve your sentence.",
    "turned_away": "The guard has heard enough. You're turned away.",
    "walked_away": "You think better of it and walk away.",
}

Judge = Callable[[Scenario, list[tuple[str, str]], str], Verdict]


def make_judge(kind: str, model: str | None = None) -> tuple[str, Judge]:
    if kind == "gpt":
        from openai import OpenAI

        import judge_gpt

        client = OpenAI()
        model = model or judge_gpt.DEFAULT_MODEL
        return model, lambda s, h, line: judge_gpt.judge(client, s, h, line, model=model)

    import judge_jev

    model = model or judge_jev.DEFAULT_MODEL
    return model, lambda s, h, line: judge_jev.judge(s, h, line, model=model)


@dataclass
class TurnResult:
    reply: str
    verdict: Verdict
    closing_line: str | None = None  # extra guard line when the game ends on patience or time


@dataclass
class GameSession:
    scenario: Scenario
    judge: Judge
    history: list[tuple[str, str]] = field(default_factory=list)
    usages: list[Any] = field(default_factory=list)
    turn: int = 0
    suspicion: int = 0
    outcome: str | None = None

    def take_turn(self, line: str) -> TurnResult:
        if self.outcome:
            raise RuntimeError("This game is already over.")
        self.turn += 1
        verdict = self.judge(self.scenario, self.history, line)
        self.usages.append(verdict.usage)

        # Use the model's own words unless a guardrail overrode its decision.
        if verdict.guard_reply and verdict.decision == verdict.raw_decision:
            reply = verdict.guard_reply
        elif verdict.decision == "suspicious":
            reply = random.choice(self.scenario.hints)
        else:
            reply = random.choice(GUARD_LINES[verdict.decision])
        self.history.append((line, reply))

        closing = None
        if verdict.decision == "let_pass":
            self.outcome = "passed"
        elif verdict.decision == "arrest":
            self.outcome = "arrested"
        else:
            self.suspicion += 1
            # Persistence isn't a crime: running out of patience means turned away.
            if self.suspicion >= SUSPICION_LIMIT:
                self.outcome = "turned_away"
                closing = "Enough of your stories. Be on your way."
            elif self.turn >= MAX_TURNS:
                self.outcome = "turned_away"
                closing = "I've no more time for you. Move along."
        return TurnResult(reply=reply, verdict=verdict, closing_line=closing)
