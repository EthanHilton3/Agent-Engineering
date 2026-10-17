"""Three-case agent evaluation demo for Lecture 2c.

The demo runs a small tool-using policy agent, then evaluates each answer with:

1. Jev (typed scores and a safe-to-send probability)
2. A generative LLM judge (scores plus a short rationale)

The agent's tool events are real, but they are displayed separately from the
answer evaluation.  This keeps the rubric honest: the current evaluation only
judges the answer, not an invented interpretation of the trace.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import OpenAI

from tools import ToolBox
from usage import print_jev_usage, print_usage


JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"

POLICY = """
Developer API Access Policy
Effective date: September 2026

Free accounts include:
- Access to the Developer API.
- 200 credits for the Playground.
- The ability to create API keys from the Settings page.

API keys are associated with the account that creates them. Users are responsible
for protecting their keys and for activity performed with those keys.

Paid plans may include additional usage, shared access, and support features. Plan
details are described on the applicable plan page.

The service provider may modify plan features, usage allowances, or pricing.
""".strip()


@dataclass(frozen=True)
class TestCase:
    name: str
    question: str


TEST_CASES = (
    TestCase(
        name="straightforward",
        question="Does the free plan include API access?",
    ),
    TestCase(
        name="unsupported-premise",
        question="Can I use the free plan for unlimited production traffic?",
    ),
    TestCase(
        name="multi-part",
        question="Can I add 5 teammates to my free plan for API access, and how do we create keys?",
    ),
)

toolbox = ToolBox()


@toolbox.tool
def search_policy(query: str) -> str:
    """A tiny local policy tool used by the live agent."""
    return f"Policy search results for {query!r}:\n{POLICY}"


def run_agent(
    client: OpenAI,
    case: TestCase,
    usages: list[Any],
    model: str,
) -> tuple[str, list[dict[str, Any]]]:
    """Run the agent and return its answer plus an observable tool trace."""
    instructions = (
        "You answer customer questions using the developer API policy. "
        "Search the policy before answering. Never invent limits or guarantees. "
        "If the policy does not answer the question, say so and recommend escalation. "
        "Give a concise customer-facing answer."
    )
    history: list[Any] = [
        {"role": "system", "content": instructions},
        {"role": "user", "content": case.question},
    ]
    events: list[dict[str, Any]] = []

    while True:
        response = client.responses.create(
            model=model,
            instructions=instructions,
            input=history,
            tools=[tool for tool in toolbox.tools if tool["name"] == "search_policy"],
        )
        usages.append(response.usage)
        history.extend(response.output)

        function_calls = [item for item in response.output if item.type == "function_call"]
        if not function_calls:
            return response.output_text.strip(), events

        for item in function_calls:
            arguments = json.loads(item.arguments)
            tool = toolbox.get_tool_function(item.name)
            if tool is None:
                raise RuntimeError(f"Unknown tool requested by the model: {item.name}")
            result = tool(**arguments)
            events.append(
                {
                    "tool": item.name,
                    "arguments": arguments,
                    "result": result,
                }
            )
            history.append(
                {
                    "type": "function_call_output",
                    "call_id": item.call_id,
                    "output": result,
                }
            )


def jev_payload(case: TestCase, answer: str) -> dict[str, Any]:
    state = "\n\n".join(
        [
            f"QUESTION\n{case.question}",
            f"REFERENCE POLICY\n{POLICY}",
            f"CANDIDATE ANSWER\n{answer}",
        ]
    )
    return {
        "model": JEV_MODEL,
        "state": state,
        "questions": {
            "accuracy": {
                "type": "score",
                "instructions": "Rate the answer against the reference policy.",
                "criteria": [
                    "Contradicts the policy or confidently invents a policy detail",
                    "Partly correct but misses or mishandles an important point",
                    "Mostly correct with a minor omission or imprecision",
                    "Fully correct, complete, and properly qualified",
                ],
            },
            "safe_to_send": {
                "type": "noul",
                "instructions": (
                    "Is this answer safe to send to the customer as written? "
                    "It should be supported by the reference policy, avoid invented "
                    "or misleading claims, and not give unsafe instructions."
                ),
            },
            "helpfulness": {
                "type": "score",
                "instructions": "How helpful and actionable is this answer for the customer?",
                "criteria": [
                    "Not helpful or confusing",
                    "Limited help; important guidance is missing",
                    "Mostly helpful with a minor omission",
                    "Clear, concise, and actionable without additional detail unrelated to the question",
                ],
            },
        },
    }


def call_jev(payload: dict[str, Any], usages: list[dict[str, Any]]) -> dict[str, Any]:
    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        raise RuntimeError("TYPESAFE_API_KEY is not set.")
    request = Request(
        JEV_URL,
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
            if result.get("usage"):
                usages.append(result["usage"])
            return result
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Jev returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Could not reach Jev: {error.reason}") from error


def generative_judge(
    client: OpenAI,
    case: TestCase,
    answer: str,
    usages: list[Any],
    model: str,
) -> dict[str, Any]:
    rubric = (
        "Evaluate the candidate answer against the question and reference policy. "
        "Give accuracy a continuous score from 0.0 to 3.0, using these four "
        "rubric levels as reference points: "
        "(0) contradicts the policy or confidently invents a policy detail; "
        "(1) partly correct but misses or mishandles an important point; "
        "(2) mostly correct with a minor omission or imprecision; "
        "(3) fully correct, complete, and properly qualified. Intermediate decimal "
        "values are encouraged when the answer falls between levels. "
        "Give helpfulness a continuous score from 0.0 to 3.0, using these four "
        "rubric levels as reference points: "
        "(0) not helpful or confusing; "
        "(1) limited help because important guidance is missing; "
        "(2) mostly helpful with a minor omission; "
        "(3) clear, concise, and actionable without additional detail unrelated to the question. "
        "Intermediate decimal values are encouraged when the answer falls between levels. "
        "For safe_to_send, return the probability from 0 to 1 that the answer is "
        "safe to send to the customer as written. This includes being supported by "
        "the reference policy, avoiding invented or misleading claims, and avoiding "
        "unsafe instructions. Use decimal values when appropriate, but do not invent "
        "precision. Include a short rationale explaining the scores. Return JSON only."
    )
    response = client.responses.create(
        model=model,
        input=(
            f"QUESTION\n{case.question}\n\nREFERENCE POLICY\n{POLICY}\n\n"
            f"CANDIDATE ANSWER\n{answer}\n\nRUBRIC\n{rubric}"
        ),
        text={
            "format": {
                "type": "json_schema",
                "name": "evaluation",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "accuracy",
                        "helpfulness",
                        "safe_to_send",
                        "rationale",
                    ],
                    "properties": {
                        "accuracy": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 3.0,
                            "description": "Continuous 0.0-3.0 correctness score. Anchors: 0 contradicts or invents policy; 1 is materially incomplete or partly wrong; 2 is mostly correct with a minor omission; 3 is fully correct and properly qualified. Intermediate values are allowed.",
                        },
                        "helpfulness": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 3.0,
                            "description": "Continuous 0.0-3.0 customer-usefulness score. Anchors: 0 is confusing or unhelpful; 1 lacks important guidance; 2 is mostly helpful with a minor omission; 3 is clear, concise, and actionable without unrelated detail. Intermediate values are allowed.",
                        },
                        "safe_to_send": {
                            "type": "number",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "Probability that the answer is policy-supported, avoids invented or misleading claims and unsafe instructions, and is safe to send as written.",
                        },
                        "rationale": {"type": "string"},
                    },
                },
            }
        },
    )
    usages.append(response.usage)
    return json.loads(response.output_text)


def main(agent_model: str, judge_model: str):
    client = OpenAI()
    print(f"Agent model: {agent_model}")
    print(f"Judge model: {judge_model}")
    print(f"Running {len(TEST_CASES)} test cases. This makes three agent, three Jev, and three judge calls.\n")

    agent_usages: list[Any] = []
    judge_usages: list[Any] = []
    jev_usages: list[dict[str, Any]] = []
    comparison = []
    for case in TEST_CASES:
        print(f"=== {case.name} ===")
        print(f"Question: {case.question}")
        answer, events = run_agent(client, case, agent_usages, agent_model)
        print(f"\nAgent answer:\n{answer}")
        print(f"\nObserved tool events: {len(events)}")
        for event in events:
            print(f"  {event['tool']}({event['arguments']})")

        print("\nBefore seeing the automated evaluations, discuss:")
        print("  Accuracy     0.0-3.0  (0 = contradicts/invents; 1 = partly correct; 2 = mostly correct; 3 = fully correct)")
        print("  Helpfulness  0.0-3.0  (0 = unhelpful; 1 = important guidance missing; 2 = mostly helpful; 3 = clear/actionable)")
        print("  Safe to send 0.0-1.0  (policy-supported, not misleading, no unsafe instructions, and appropriate to send)")
        input("Discuss the likely scores, then press Return to run the judges...")

        jev_result = call_jev(jev_payload(case, answer), jev_usages)
        llm_result = generative_judge(client, case, answer, judge_usages, judge_model)
        jev_answers = jev_result.get("answers", jev_result)
        comparison.append(
            {
                "case": case.name,
                "jev_accuracy": jev_answers["accuracy"].get("score"),
                "llm_accuracy": llm_result["accuracy"],
                "jev_helpfulness": jev_answers["helpfulness"].get("score"),
                "llm_helpfulness": llm_result["helpfulness"],
                "jev_safe_to_send": jev_answers["safe_to_send"].get("noul"),
                "llm_safe_to_send": llm_result["safe_to_send"],
            }
        )

        print("\nJev evaluation:")
        print(json.dumps(jev_answers, indent=2))
        print("\nGenerative judge evaluation:")
        print(json.dumps(llm_result, indent=2))
        print()
        input("Press Return to run the next test case...")
        print()

    print("\n=== Comparison summary ===")
    print(json.dumps(comparison, indent=2))
    print("\nDiscussion: Where did the evaluators agree or disagree, and why?")
    print("\nResponse agent usage:", file=sys.stderr)
    print_usage([(agent_model, usage) for usage in agent_usages])
    print("\nGenerative judge usage:", file=sys.stderr)
    print_usage([(judge_model, usage) for usage in judge_usages])
    print_jev_usage(jev_usages)


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set.")
    if not os.environ.get("TYPESAFE_API_KEY"):
        raise RuntimeError("TYPESAFE_API_KEY is not set.")

    default_agent_model = "gpt-5.6-luna"
    default_judge_model = "gpt-5.6-terra"

    parser = argparse.ArgumentParser(description="Compare Jev with a generative judge on agent answers.")
    parser.add_argument(
        "--agent-model",
        default=default_agent_model,
        help=f"OpenAI model used to produce agent answers (default: {default_agent_model})",
    )
    parser.add_argument(
        "--judge-model",
        default=default_judge_model,
        help=f"OpenAI model used as the generative judge (default: {default_judge_model})",
    )
    args = parser.parse_args()
    main(args.agent_model, args.judge_model)
