"""Jev classifier for Talk Past the Guard.

One request asks three atomic questions about the same state:
  verdict           choice  -> let_pass / suspicious / arrest, with probabilities
  persuasiveness    score   -> expected value over the 4-level rubric (0-3)
  out_of_character  noul    -> P(yes)
Combining them (the jailbreak guardrail) happens in code, in judge_common.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from judge_common import OUT_OF_CHARACTER, PERSUASIVENESS, VERDICTS, Verdict, render_state
from scenarios import Scenario


JEV_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"


def make_payload(
    scenario: Scenario,
    history: list[tuple[str, str]],
    player_line: str,
    model: str = DEFAULT_MODEL,
) -> dict[str, Any]:
    return {
        "model": model,
        "state": render_state(scenario, history, player_line),
        "questions": {
            "verdict": {
                "type": "choice",
                "instructions": (
                    "How should the guard react to the player's latest line, given "
                    "the guard's rules and facts?"
                ),
                "criteria": VERDICTS,
            },
            "persuasiveness": {
                "type": "score",
                "instructions": "How persuasive is the player's latest line to this guard?",
                "criteria": PERSUASIVENESS,
            },
            "out_of_character": {
                "type": "noul",
                "instructions": OUT_OF_CHARACTER,
            },
        },
    }


def call_jev(payload: dict[str, Any]) -> dict[str, Any]:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is not set.")
    request = Request(
        JEV_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jev returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Jev: {error.reason}") from error


def judge(
    scenario: Scenario,
    history: list[tuple[str, str]],
    player_line: str,
    model: str = DEFAULT_MODEL,
) -> Verdict:
    start = time.perf_counter()
    result = call_jev(make_payload(scenario, history, player_line, model))
    latency = time.perf_counter() - start

    answers = result.get("answers", result)
    verdict = answers["verdict"]
    probabilities = verdict.get("probabilities", {})
    decision = verdict["choice"]
    return Verdict(
        decision=decision,
        confidence=probabilities.get(decision, 0.0),
        persuasiveness=answers["persuasiveness"]["score"],
        out_of_character=answers["out_of_character"]["noul"],
        probabilities=probabilities,
        latency_s=latency,
        usage=result.get("usage"),
    )
