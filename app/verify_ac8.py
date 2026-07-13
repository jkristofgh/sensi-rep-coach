#!/usr/bin/env python3
"""AC8 — the templating proof (Phase-3 hook).

The SAME scoring engine (scoring.py) scores a *support* call using a *different* rubric
(rubric_csqa.yaml) — no engine code change, only config (the rubric) + input (the transcript).
This is the concrete evidence for "a new team = a new rubric, not new code."

Run:  python verify_ac8.py            (needs ANTHROPIC_API_KEY in build/.env)
"""
import json
import os
import sys
from pathlib import Path

import yaml

import scoring

HERE = Path(__file__).resolve().parent
RUBRIC = HERE / "rubric_csqa.yaml"
TRANSCRIPT = HERE / "data" / "csqa" / "CS1_support_001.json"


def main():
    scoring.load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set (build/.env)")
    import anthropic
    client = anthropic.Anthropic()
    model = os.environ.get("REPCOACH_MODEL", "claude-sonnet-5")

    rubric = yaml.safe_load(RUBRIC.read_text())
    t = json.loads(TRANSCRIPT.read_text())

    print(f"Rubric : {rubric['name']}  (evaluator role: {rubric['evaluator_role']})")
    print(f"Call   : {t['call_id']} · {t['call_type']} · {t['product']} · {t['account']}")
    print("Engine : scoring.deterministic_metrics + llm_pass + combine  (UNCHANGED)\n")

    m = scoring.deterministic_metrics(t["turns"], t["call_type"])
    llm = scoring.llm_pass(t, rubric, client, model)
    misses = scoring.verify_quotes(llm, t["turns"])
    rec = scoring.combine(t, rubric, m, llm)

    out = TRANSCRIPT.parent / f"{t['call_id']}_eval.json"
    out.write_text(json.dumps(rec, indent=2))

    print(f"OVERALL: {rec['overall']}/100   (rubric v{rec['rubric_version']}, model {rec['model']})")
    for d in rec["dimensions"]:
        print(f"  {d['label']:<38} {d['score']:>4}/5  · {d['signal']}")
    if rec["flags"]:
        print("  flags  : " + ", ".join(sorted({f["type"] for f in rec["flags"]})))
    print(f"  summary: {rec['summary']}")
    print(f"  → wrote {out.relative_to(HERE)}")

    # AC8 assertions: a well-formed evaluation, produced by the same engine, from a different rubric
    got = {d["key"] for d in rec["dimensions"]}
    want = {d["key"] for d in rubric["dimensions"]}
    assert got == want, f"dimension mismatch: {got} vs {want}"
    assert 0 <= rec["overall"] <= 100, "overall out of range"
    assert all(0 <= d["score"] <= 5 for d in rec["dimensions"]), "a dimension score is out of range"
    for d in rec["dimensions"]:
        if d["signal"] in ("llm", "hybrid"):
            assert d.get("evidence"), f"{d['key']} missing evidence quote"
    print("\n✓ AC8 PASS — same engine scored a support call via rubric_csqa.yaml, zero code change.")
    if misses:
        print(f"  (soft check: {misses} evidence quote(s) not verbatim)")


if __name__ == "__main__":
    main()
