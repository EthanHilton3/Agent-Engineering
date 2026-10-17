"""Small Jev choice demo for Lecture 2c.

Jev evaluates three candidate release notes and chooses a workflow
disposition: publish, revise, or reject.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"

PULL_REQUEST = """
Pull request: Add CSV export for the project report.

User-facing changes:
- Adds an Export CSV button to the project report page.
- Exports the currently filtered report rows.
- Does not change the existing PDF export.
""".strip()

CANDIDATES = [
    {
        "name": "ready",
        "release_note": (
            "Project reports now support CSV export. Use the new Export CSV button "
            "to download the currently filtered report rows. PDF export is unchanged."
        ),
    },
    {
        "name": "needs-revision",
        "release_note": "You can now export project reports to CSV.",
    },
    {
        "name": "unsupported-claim",
        "release_note": (
            "Project reports now export to CSV and PDF. CSV export includes every "
            "project in the system, even when filters are applied."
        ),
    },
]


def make_payload(candidate: dict[str, str], model: str) -> dict:
    """Build one Jev request with a fixed set of workflow decisions."""
    state = "\n\n".join(
        [
            f"SOURCE CHANGES\n{PULL_REQUEST}",
            f"CANDIDATE RELEASE NOTE\n{candidate['release_note']}",
        ]
    )

    return {
        "model": model,
        "state": state,
        "questions": {
            "disposition": {
                "type": "choice",
                "instructions": "What should happen to these release notes?",
                "criteria": {
                    "publish": "Accurate, complete, and ready to show users.",
                    "revise": "Generally accurate but needs corrections or additions.",
                    "reject": "Contains a material error, unsupported claim, or misleading description.",
                },
            }
        },
    }


def call_jev(payload: dict) -> dict:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        raise RuntimeError("TYPESAFE_API_KEY is not set.")

    request = Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
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


def main(model: str) -> int:
    print("Jev release-note judge demo")
    print(f"Model: {model}")
    print(f"Source changes:\n{PULL_REQUEST}\n")

    for candidate in CANDIDATES:
        print(f"=== {candidate['name']} ===")
        print(f"Release note: {candidate['release_note']}")

        try:
            result = call_jev(make_payload(candidate, model))
        except RuntimeError as error:
            print(f"\nError: {error}", file=sys.stderr)
            return 1

        answer = result.get("answers", result).get("disposition", {})
        print(f"Jev choice: {answer.get('choice', answer)}")
        if "probabilities" in answer:
            print(f"Probabilities: {json.dumps(answer['probabilities'])}")
        print()

    print("The application could use the choice to publish, request edits, or block the release note.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate release notes with Jev choice.")
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Jev model to use (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.model))
