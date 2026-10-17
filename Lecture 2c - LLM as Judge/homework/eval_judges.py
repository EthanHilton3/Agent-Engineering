"""Run both judges on the labeled test cases and compare them.

    python eval_judges.py                    # GPT and Jev
    python eval_judges.py --judges gpt       # GPT only (no Jev key needed)
    python eval_judges.py --repeat 3         # repeat GPT to measure consistency
    python eval_judges.py --rationale-last   # A/B the GPT schema order

Results are also written to eval_results/latest.json (change with --out).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter

from scenarios import SCENARIOS
from test_cases import CASES
from usage import print_jev_usage, print_usage


def run(judges: list[str], gpt_model: str, repeat: int, rationale_first: bool):
    gpt_usages, jev_usages, rows = [], [], []
    client = None
    if "gpt" in judges:
        from openai import OpenAI

        client = OpenAI()

    for i, case in enumerate(CASES, 1):
        scenario = SCENARIOS[case.scenario]
        row = {"case": i, "scenario": case.scenario, "line": case.line, "expected": case.expected, "note": case.note}
        print(f"[{i}/{len(CASES)}] {case.scenario}: {case.line[:60]}", file=sys.stderr)

        if "gpt" in judges:
            import judge_gpt

            runs = []
            for _ in range(repeat):
                v = judge_gpt.judge(client, scenario, [], case.line, model=gpt_model, rationale_first=rationale_first)
                gpt_usages.append((gpt_model, v.usage))
                runs.append(v)
            decisions = [v.decision for v in runs]
            majority = Counter(decisions).most_common(1)[0][0]
            row["gpt"] = {
                "decision": majority,
                "all_decisions": decisions,
                "confidence": runs[0].confidence,
                "persuasiveness": runs[0].persuasiveness,
                "out_of_character": runs[0].out_of_character,
                "raw_decision": runs[0].raw_decision,
                "rationale": runs[0].rationale,
                "latency_s": sum(v.latency_s for v in runs) / len(runs),
            }

        if "jev" in judges:
            import judge_jev

            v = judge_jev.judge(scenario, [], case.line)
            if v.usage:
                jev_usages.append(v.usage)
            row["jev"] = {
                "decision": v.decision,
                "probabilities": v.probabilities,
                "confidence": v.confidence,
                "persuasiveness": v.persuasiveness,
                "out_of_character": v.out_of_character,
                "raw_decision": v.raw_decision,
                "latency_s": v.latency_s,
            }
        rows.append(row)
    return rows, gpt_usages, jev_usages


def summarize(rows: list[dict], judges: list[str]):
    print(f"\n{'#':>2}  {'expected':<11}" + "".join(f"{j:<24}" for j in judges) + "note")
    for r in rows:
        cells = ""
        for j in judges:
            d = r[j]
            mark = "ok" if d["decision"] == r["expected"] else "XX"
            cells += f"{mark} {d['decision']:<11} {d['confidence']:.2f}    "
        print(f"{r['case']:>2}  {r['expected']:<11}{cells}{r['note']}")

    print()
    for j in judges:
        correct = sum(r[j]["decision"] == r["expected"] for r in rows)
        latency = sum(r[j]["latency_s"] for r in rows) / len(rows)
        print(f"{j}: {correct}/{len(rows)} match your labels, avg latency {latency * 1000:.0f} ms")
        if j == "gpt":
            flips = sum(len(set(r["gpt"]["all_decisions"])) > 1 for r in rows)
            if len(rows[0]["gpt"]["all_decisions"]) > 1:
                print(f"gpt: {flips} case(s) changed decision across repeats")
    if len(judges) == 2:
        agree = sum(r["gpt"]["decision"] == r["jev"]["decision"] for r in rows)
        print(f"gpt and jev agree on {agree}/{len(rows)}")


if __name__ == "__main__":
    import judge_gpt

    parser = argparse.ArgumentParser(description="Compare the GPT judge and Jev on labeled cases.")
    parser.add_argument("--judges", nargs="+", choices=["gpt", "jev"], default=["gpt", "jev"])
    parser.add_argument("--gpt-model", default=judge_gpt.DEFAULT_MODEL)
    parser.add_argument("--repeat", type=int, default=1, help="Times to run GPT per case.")
    parser.add_argument("--rationale-last", action="store_true", help="Put rationale after the decision in the GPT schema.")
    parser.add_argument("--out", default="eval_results/latest.json")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    rows, gpt_usages, jev_usages = run(args.judges, args.gpt_model, args.repeat, not args.rationale_last)
    summarize(rows, args.judges)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    print(f"\nWrote {args.out}")
    if gpt_usages:
        print_usage(gpt_usages)
    if jev_usages:
        print_jev_usage(jev_usages)
