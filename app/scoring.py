#!/usr/bin/env python3
"""Rep Coach scoring engine — hybrid, explainable, rubric-as-config.

Two signals, deliberately not all-LLM:
  DETERMINISTIC (in code)  — talk/listen ratio, question counts, next-step booked, monologue length.
  LLM (Claude, structured) — the judgment dimensions, each with VERBATIM evidence quotes + a tip,
                             plus flags and recommendations. Enforced via tool-use so the return
                             is always schema-valid JSON.

Combine → an evaluation record per call (0–100 overall) written to data/evaluations/<call_id>.json.

Usage:
  python scoring.py                       # score every transcript in data/synthetic/
  python scoring.py --call-id R4_disc_001 # score one
  python scoring.py --deterministic-only  # no API calls — just the computed metrics (AC3 hand-check)
"""
import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SYNTH = DATA / "synthetic"
EVAL = DATA / "evaluations"

OPEN_STARTERS = ("what", "how", "why", "when", "who", "where", "which",
                 "tell me", "walk me", "help me understand", "describe", "walk through")

# A next step counts only when scheduling language is tied to a MEETING/TIME — not to pricing,
# shifts, or account setup (e.g. "lock in a rate" / "schedule shifts" must NOT match).
NEXT_STEP_PATTERNS = [
    re.compile(r"\b(schedule|book|set[- ]?up|lock in|hold|find|grab|put|slot)\b[^.?!]{0,40}"
               r"\b(call|meeting|demo|time|chat|conversation|session|follow[- ]?up|sync)\b", re.I),
    re.compile(r"\b(get|put|pop|throw)\b[^.?!]{0,25}\bon (?:the |your |my )?calendar\b", re.I),
    re.compile(r"\b(calendar invite|send (?:you )?an invite|meeting invite)\b", re.I),
    re.compile(r"\b(meet|talk|reconnect|follow up|circle back|reconvene)\b[^.?!]{0,30}"
               r"\b(?:on |next |this )?(monday|tuesday|wednesday|thursday|friday|week|tomorrow)\b", re.I),
]


def has_booked_next_step(rep_text):
    return any(p.search(rep_text) for p in NEXT_STEP_PATTERNS)


# ---- config -----------------------------------------------------------------

def load_rubric():
    return yaml.safe_load((HERE / "rubric.yaml").read_text())


def load_env():
    envfile = HERE / ".env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


# ---- deterministic pass -----------------------------------------------------

def deterministic_metrics(turns, call_type):
    rep = [t["text"] for t in turns if t["speaker"] == "Rep"]
    pro = [t["text"] for t in turns if t["speaker"] == "Prospect"]
    rep_words = sum(len(t.split()) for t in rep)
    pro_words = sum(len(t.split()) for t in pro)
    total = rep_words + pro_words or 1
    talk_ratio = rep_words / total

    rep_questions = open_questions = 0
    for t in rep:
        for q in re.findall(r"[^.?!]*\?", t):        # sentences ending in '?'
            rep_questions += 1
            s = q.strip().lower()
            if any(s.startswith(w) for w in OPEN_STARTERS) or "tell me" in s or "walk me" in s:
                open_questions += 1

    next_step_booked = has_booked_next_step(" ".join(rep))
    monologue_max = max((len(t.split()) for t in rep), default=0)
    return {
        "talk_ratio": round(talk_ratio, 3),
        "rep_questions": rep_questions,
        "open_questions": open_questions,
        "next_step_booked": next_step_booked,
        "monologue_max_words": monologue_max,
    }


def talk_score(ratio, call_type):
    """0–5; discovery expects more listening than a demo/close."""
    ideal = 0.55 if call_type == "discovery" else 0.62
    for bump, sc in [(0.0, 5), (0.10, 4), (0.18, 3), (0.28, 2)]:
        if ratio <= ideal + bump:
            return sc
    return 1


def det_dimension_scores(m, call_type):
    """Deterministic 0–5 signals for the dims that use them."""
    talk = talk_score(m["talk_ratio"], call_type)
    disc = {0: 1, 1: 2, 2: 3, 3: 4}.get(m["open_questions"], 5)   # open-question density
    nxt = 5 if m["next_step_booked"] else 2
    return {"talk_listen_balance": talk, "discovery_quality": disc, "next_step": nxt}


# ---- LLM pass ---------------------------------------------------------------

def build_tool(rubric):
    judged = [d for d in rubric["dimensions"] if d["signal"] in ("llm", "hybrid")]
    dim_props = {
        d["key"]: {
            "type": "object",
            "properties": {
                "score": {"type": "number", "minimum": 0, "maximum": 5,
                          "description": d["description"]},
                "evidence": {"type": "array", "items": {"type": "string"}, "maxItems": 2,
                             "description": "ONE short VERBATIM quote from the transcript (<=25 words)"},
                "tip": {"type": "string", "description": "one concrete coaching tip (one sentence)"},
            },
            "required": ["score", "evidence", "tip"],
        } for d in judged
    }
    flag_types = [f["key"] for f in rubric["flags"]["types"]]
    return [{
        "name": "submit_evaluation",
        "description": "Return the rubric evaluation for this sales call.",
        "input_schema": {
            "type": "object",
            "properties": {
                "dimensions": {"type": "object", "properties": dim_props,
                               "required": list(dim_props)},
                "flags": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"type": {"type": "string", "enum": flag_types},
                                   "evidence": {"type": "string"}},
                    "required": ["type", "evidence"]}},
                "recommendations": {"type": "array", "items": {
                    "type": "object",
                    "properties": {"title": {"type": "string"}, "why": {"type": "string"}},
                    "required": ["title", "why"]}},
                "summary": {"type": "string", "description": "2-3 sentence overall read"},
            },
            "required": ["dimensions", "flags", "recommendations", "summary"],
        },
    }], [d["key"] for d in judged]


def system_prompt(rubric):
    # Everything below is derived from the rubric — role, motion, proof, dimensions, AND flags —
    # so a new team is a new rubric, not new code (this is the templatable seam; see rubric_csqa.yaml).
    judged = [d for d in rubric["dimensions"] if d["signal"] in ("llm", "hybrid")]
    dims = "\n".join(f"- {d['key']}: {d['description']}" for d in judged)
    role = rubric.get("evaluator_role", "sales-enablement")
    flag_lines = "; ".join(f"{f['key']} ({f['description']})" for f in rubric["flags"]["types"])
    return (
        f"You are a senior {role} evaluator for Sensi (Care Intelligence for senior care). Score "
        "the call ONLY on the dimensions below, 0-5 each, and cite VERBATIM quotes from the "
        "transcript as evidence for every score. Be calibrated, not generous: weak handling of a "
        "dimension is a 2, not a 4; a claim with no basis in the reference facts below scores low.\n\n"
        f"Persona: {rubric['persona']['buyer']} — {rubric['persona']['pain']}\n"
        f"Prescribed motion: {' → '.join(rubric['motion']['agenda'])}. "
        f"{rubric['motion']['principle']}\n"
        "Reference facts / published proof (claims should match THESE; flag invented ones):\n  "
        + "; ".join(rubric["proof_wall"]) + "\n\n"
        "Dimensions to score:\n" + dims + "\n\n"
        "Also raise any of these flags where clearly warranted: " + flag_lines + ". And recommend "
        "1-3 micro-content / coaching items tied to the weakest dimensions. Keep it COMPACT: exactly "
        "ONE short verbatim quote per dimension, one-sentence tips, a 2-sentence summary. Call "
        "submit_evaluation with your result."
    )


def llm_pass(transcript, rubric, client, model, attempts=3):
    tools, judged_keys = build_tool(rubric)
    convo = "\n".join(f'{t["speaker"]}: {t["text"]}' for t in transcript["turns"])
    user = (f"Call type: {transcript['call_type']} · Product: {transcript['product']}\n\n"
            f"TRANSCRIPT:\n{convo}")
    last = None
    for i in range(attempts):
        resp = client.messages.create(
            model=model, max_tokens=4096, system=system_prompt(rubric),
            tools=tools, tool_choice={"type": "tool", "name": "submit_evaluation"},
            messages=[{"role": "user", "content": user}])
        if resp.stop_reason == "max_tokens":
            last = "hit max_tokens (output truncated)"
            print(f"    (retry {transcript['call_id']}: {last})")
            continue
        raw = next((b.input for b in resp.content
                    if b.type == "tool_use" and b.name == "submit_evaluation"), None)
        if raw is None:
            continue
        out = _normalize(raw)
        dims = out.get("dimensions")
        bad = [k for k in judged_keys
               if not isinstance(dims, dict)
               or not isinstance(dims.get(k), dict) or "score" not in dims.get(k, {})]
        if isinstance(dims, dict) and not bad:
            return out
        last = f"dimensions malformed/incomplete: {bad}"
        print(f"    (retry {transcript['call_id']}: {last})")
    sys.exit(f"  ! {transcript['call_id']} failed structured output after {attempts} tries ({last})")


def _json_objects(s):
    """Extract consecutive top-level JSON objects from a string. The model sometimes crams the
    whole payload as concatenated objects into one string field ({dims}{flags,recs,summary}),
    which trips a plain json.loads on 'Extra data' — raw_decode walks them one at a time."""
    dec = json.JSONDecoder()
    out, i, n = [], 0, len(s)
    while i < n:
        while i < n and s[i].isspace():
            i += 1
        if i >= n:
            break
        try:
            obj, i = dec.raw_decode(s, i)
        except json.JSONDecodeError:
            break
        out.append(obj)
    return out


def _coerce_obj(x):
    """A sub-field may come back as a JSON string or a Python-repr string — parse both."""
    if not isinstance(x, str):
        return x
    for parse in (json.loads, ast.literal_eval):
        try:
            return parse(x)
        except (ValueError, SyntaxError):
            continue
    objs = _json_objects(x)
    return objs[0] if objs else x


def _coerce_score(x):
    """A dimension score to a float in [0, 5]. The model occasionally returns "4/5", a bare
    string, or an out-of-range number; combine() must never crash or let a score inflate the
    overall. Unparseable → 0.0 (a missing score is caught earlier by llm_pass's gate)."""
    if isinstance(x, str):
        x = x.split("/")[0].strip()          # "4/5" -> "4"
    try:
        return max(0.0, min(5.0, float(x)))
    except (TypeError, ValueError):
        return 0.0


def _normalize(inp):
    """Coerce occasional structured-output quirks: string/concatenated sub-objects, scalar evidence."""
    d = dict(inp)
    dims = d.get("dimensions")
    if isinstance(dims, str):
        objs = _json_objects(dims)
        if objs:
            d["dimensions"] = objs[0]                       # first object is the dimensions map
            for o in objs[1:]:                              # scavenge the rest for the other fields
                if isinstance(o, dict):
                    for k in ("flags", "recommendations", "summary"):
                        if k in o:
                            d.setdefault(k, o[k])
    for k in ("flags", "recommendations"):
        if isinstance(d.get(k), str):
            d[k] = _coerce_obj(d[k])
    dims = d.get("dimensions", {})
    if isinstance(dims, dict):
        # Default evidence/tip so combine() can read them unconditionally. (Score is left
        # untouched here so llm_pass's "score present" completeness gate still fires on a
        # dimension the model returned without one — it's coerced/clamped later, in combine.)
        for v in dims.values():
            if not isinstance(v, dict):
                continue
            ev = v.get("evidence")
            if isinstance(ev, str):
                ev = [ev]
            elif not isinstance(ev, list):
                ev = [] if ev is None else [str(ev)]
            v["evidence"] = [str(q) for q in ev]
            v["tip"] = str(v.get("tip") or "")
    d.setdefault("flags", [])
    d.setdefault("recommendations", [])
    d.setdefault("summary", "")
    return d


# ---- combine ----------------------------------------------------------------

def verify_quotes(llm, turns):
    """Soft credibility check: how many evidence quotes are NOT verbatim in the transcript."""
    hay = " ".join(t["text"].lower() for t in turns)
    hay = re.sub(r"\s+", " ", hay)
    misses = 0
    for d in llm["dimensions"].values():
        if not isinstance(d, dict):
            continue
        for q in d.get("evidence", []):
            probe = re.sub(r"\s+", " ", q.lower()).strip(' "\'.')[:60]
            if probe and probe not in hay:
                misses += 1
    return misses


def combine(transcript, rubric, det_metrics, llm):
    ct = transcript["call_type"]
    det = det_dimension_scores(det_metrics, ct)
    try:
        weights = {d["key"]: d["weights"][ct] for d in rubric["dimensions"]}
    except KeyError as e:
        raise ValueError(f"rubric '{rubric.get('name', '?')}' has no weight for call_type "
                         f"{ct!r} on dimension {e}") from None
    wsum = sum(weights.values())
    if abs(wsum - 1.0) > 0.01:
        raise ValueError(f"rubric '{rubric.get('name', '?')}' weights for call_type {ct!r} "
                         f"sum to {wsum:.3f}, not 1.0 — the overall score would be mis-scaled")
    dims_out, score_by_key = [], {}
    for d in rubric["dimensions"]:
        k, sig = d["key"], d["signal"]
        if sig == "deterministic":
            score = det[k]
            evidence = [f"rep talk {det_metrics['talk_ratio']:.0%} of the call"]
            tip = ("Aim for more listening — open with questions and let the buyer talk."
                   if score <= 3 else "Healthy talk/listen balance — keep it up.")
        elif sig == "hybrid":
            lo = llm["dimensions"][k]
            score = round((_coerce_score(lo["score"]) + det[k]) / 2, 1)
            evidence, tip = lo["evidence"], lo["tip"]
        else:  # llm
            lo = llm["dimensions"][k]
            score = round(_coerce_score(lo["score"]), 1)
            evidence, tip = lo["evidence"], lo["tip"]
        score_by_key[k] = score
        dims_out.append({"key": k, "label": d["label"], "score": score,
                         "weight": weights[k], "signal": sig,
                         "evidence": evidence, "tip": tip})

    base = 20 * sum(weights[k] * score_by_key[k] for k in weights)
    penalty = min(rubric["flags"]["penalty_cap"],
                  len(llm["flags"]) * rubric["flags"]["penalty_per_flag"])
    overall = max(0, min(100, round(base - penalty)))

    return {
        "call_id": transcript["call_id"], "rep_id": transcript["rep_id"],
        "rep_name": transcript.get("rep_name"), "product": transcript["product"],
        "account": transcript.get("account"),
        "call_type": ct, "date": transcript.get("date"),
        "rubric_version": rubric["version"], "model": os.environ.get("REPCOACH_MODEL", "claude-sonnet-5"),
        "overall": overall, "penalty": penalty,
        "deterministic": det_metrics,
        "dimensions": dims_out,
        "flags": llm["flags"], "recommendations": llm["recommendations"],
        "summary": llm["summary"],
    }


# ---- main -------------------------------------------------------------------

def score_one(path, rubric, client, model, det_only):
    t = json.loads(path.read_text())
    m = deterministic_metrics(t["turns"], t["call_type"])
    if det_only:
        print(f'{t["call_id"]:<14} talk={m["talk_ratio"]:.0%} q={m["rep_questions"]} '
              f'open={m["open_questions"]} next_booked={m["next_step_booked"]} '
              f'mono={m["monologue_max_words"]}w')
        return None
    llm = llm_pass(t, rubric, client, model)
    misses = verify_quotes(llm, t["turns"])
    rec = combine(t, rubric, m, llm)
    EVAL.mkdir(parents=True, exist_ok=True)
    (EVAL / f'{t["call_id"]}.json').write_text(json.dumps(rec, indent=2))
    warn = f"  ⚠ {misses} non-verbatim quote(s)" if misses else ""
    print(f'{rec["call_id"]:<14} overall={rec["overall"]:<3} '
          f'flags={len(rec["flags"])} recs={len(rec["recommendations"])}{warn}')
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--call-id", help="score a single transcript")
    ap.add_argument("--deterministic-only", action="store_true", help="no API calls")
    args = ap.parse_args()
    load_env()
    rubric = load_rubric()

    paths = ([SYNTH / f"{args.call_id}.json"] if args.call_id
             else sorted(SYNTH.glob("*.json")))
    if not paths or not paths[0].exists():
        sys.exit("no transcripts found — run generate_data.py --with-transcripts first")

    client = model = None
    if not args.deterministic_only:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ANTHROPIC_API_KEY not set (build/.env)")
        import anthropic
        client = anthropic.Anthropic()
        model = os.environ.get("REPCOACH_MODEL", "claude-sonnet-5")

    for p in paths:
        score_one(p, rubric, client, model, args.deterministic_only)


if __name__ == "__main__":
    main()
