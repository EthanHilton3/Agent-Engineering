# Eval results

Output from `eval_judges.py`, in the order the runs happened.

| File | What changed | Score |
|---|---|---|
| `1_baseline_gpt-5.6-luna.json` | First rubric, original judge model | GPT 11/15 |
| `2_baseline_gpt-6-sol.json` | Same rubric, bigger model | GPT 12/15 |
| `3_v2-rubric_gpt-6-sol.json` | Narrower arrest rule, player clues, guard hints, confidence gate (3 test lines added) | GPT 17/18 |
| `4_v3-soft-spots_gpt-6-sol.json` | Guard soft spots, turned away instead of arrested (2 test lines added) | GPT 18/20 |
| `5_v3-soft-spots_gpt-vs-jev.json` | Same as v3, both judges side by side | GPT 17/20, Jev 19/20 |

New runs go to `latest.json` unless you pass `--out`.
