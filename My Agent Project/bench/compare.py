"""Print per-task medians for one results file, or compare two and print the gate verdicts (plan §11.5).

    python bench/compare.py v2.jsonl            # medians only
    python bench/compare.py v2.jsonl v3.jsonl   # A = baseline, B = candidate; adds gate verdicts
"""
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

COST_GATED = ["T2", "T3", "T4", "T5", "T8"]


def load(path: str) -> dict[str, list[dict]]:
    by_task = defaultdict(list)
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            by_task[row["task"]].append(row)
    return dict(sorted(by_task.items()))


def med(rows: list[dict], key: str) -> float:
    return statistics.median(row[key] for row in rows)


def turn2_input(rows: list[dict]) -> float | None:
    values = [r["turns"][1]["input_tokens"] for r in rows if len(r.get("turns", [])) > 1]
    return statistics.median(values) if values else None


def print_medians(label: str, data: dict[str, list[dict]]) -> None:
    print(f"\n{label}")
    print(f"{'task':<5}{'pass':>6}{'rounds':>8}{'tools':>7}{'web':>5}{'input':>10}{'cached':>10}{'output':>8}"
          f"{'cost $':>9}{'wall s':>8}")
    total_cost = 0.0
    for task, rows in data.items():
        passed = sum(r["success"] for r in rows)
        total_cost += sum(r["cost_usd"] for r in rows)
        print(f"{task:<5}{f'{passed}/{len(rows)}':>6}{med(rows, 'rounds'):>8.1f}{med(rows, 'tool_calls'):>7.1f}"
              f"{med(rows, 'web_actions'):>5.0f}{med(rows, 'input_tokens'):>10.0f}{med(rows, 'cached_tokens'):>10.0f}"
              f"{med(rows, 'output_tokens'):>8.0f}{med(rows, 'cost_usd'):>9.4f}{med(rows, 'wall_s'):>8.1f}")
    print(f"(medians over runs; total cost of all runs in file: ${total_cost:.4f})")


def verdict(ok: bool | None) -> str:
    return "n/a " if ok is None else ("PASS" if ok else "FAIL")


def print_gates(a: dict[str, list[dict]], b: dict[str, list[dict]]) -> None:
    print("\nGates (B vs A)")
    wins_a = sum(r["success"] for rows in a.values() for r in rows)
    wins_b = sum(r["success"] for rows in b.values() for r in rows)
    print(f"  [{verdict(wins_b >= wins_a)}] successes: B {wins_b} >= A {wins_a}")
    for task in ("T5", "T7"):
        if task in b:
            ok = all(r["success"] for r in b[task])
            print(f"  [{verdict(ok)}] {task} passes in every B run ({sum(r['success'] for r in b[task])}/{len(b[task])})")

    def ratio_gate(name: str, key: str, limit: float, tasks: list[str]) -> None:
        for task in tasks:
            if task not in a or task not in b:
                continue
            ra, rb = med(a[task], key), med(b[task], key)
            ok = rb <= limit * ra if ra else None
            print(f"  [{verdict(ok)}] {name} {task}: B {rb:.3f} vs A {ra:.3f} "
                  f"(ratio {rb / ra:.2f}, limit {limit})" if ra else f"  [n/a ] {name} {task}: A is 0")

    ratio_gate("rounds", "rounds", 0.75, COST_GATED)
    ratio_gate("cost", "cost_usd", 0.75, COST_GATED)
    if "T8" in a and "T8" in b:
        ta, tb = turn2_input(a["T8"]), turn2_input(b["T8"])
        ok = tb <= 0.6 * ta if ta and tb is not None else None
        print(f"  [{verdict(ok)}] T8 turn-2 input tokens: B {tb} vs A {ta} (limit 0.6x)")
    ratio_gate("wall", "wall_s", 0.8, [t for t in b if t in a])
    if "T6" in b:
        ok = all(r["web_actions"] == 0 for r in b["T6"])
        print(f"  [{verdict(ok)}] T6 web actions are 0 in every B run")


def main() -> None:
    paths = sys.argv[1:]
    if len(paths) not in (1, 2):
        raise SystemExit(__doc__)
    data = [load(p) for p in paths]
    for path, d in zip(paths, data):
        print_medians(Path(path).name, d)
    if len(data) == 2:
        print_gates(*data)


if __name__ == "__main__":
    main()
