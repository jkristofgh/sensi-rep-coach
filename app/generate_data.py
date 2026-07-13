#!/usr/bin/env python3
"""Build the reproducible, NDA-safe synthetic dataset for the Rep Coach demo.

Two products, split by whether they need the LLM:

  history  (NO API key)  — deterministic seeded score-history for the trend dashboards.
                           Fixed seed + baked anchor date → identical every run.
  transcripts (API key)  — Claude-generated, speaker-labeled full transcripts to score live.
                           Generated ONCE and committed; the demo then reads the files (stable).

Usage:
  python generate_data.py                      # (re)build data/history.json only
  python generate_data.py --with-transcripts   # also generate transcripts (needs ANTHROPIC_API_KEY)
  python generate_data.py --per-rep 2          # transcripts per rep (default 2)

Everything is written under build/data/. Regeneration is idempotent for history; transcripts are
skipped if they already exist unless --overwrite is passed.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import yaml


def account_for(call_id, accounts):
    """Stable account per call (md5 → pool index), so patches and regens agree."""
    return accounts[int(hashlib.md5(call_id.encode()).hexdigest(), 16) % len(accounts)]

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
SYNTH = DATA / "synthetic"
CT_ABBR = {"discovery": "disc", "demo_close": "demo", "follow_up": "fu"}


# ---- config -----------------------------------------------------------------

def load_cfg():
    personas = yaml.safe_load((HERE / "personas.yaml").read_text())
    rubric = yaml.safe_load((HERE / "rubric.yaml").read_text())
    dims = personas["dimensions"]
    weights = {d["key"]: d["weights"] for d in rubric["dimensions"]}
    # sanity: weights per call type sum to ~1.0 so overall maxes at 100
    for ct in personas["call_types"]:
        s = sum(weights[d][ct] for d in dims)
        if abs(s - 1.0) > 1e-6:
            sys.exit(f"rubric weights for '{ct}' sum to {s:.3f}, expected 1.0")
    return personas, rubric, dims, weights


def clamp(x, lo=0.0, hi=5.0):
    return max(lo, min(hi, x))


def overall_score(dims_scores, weights, call_type):
    """0–100 from per-dimension 0–5 scores using the call-type weights."""
    return round(20 * sum(weights[k][call_type] * v for k, v in dims_scores.items()))


# ---- deterministic history --------------------------------------------------

def build_history(personas, dims, weights):
    meta = personas["meta"]
    rng = random.Random(meta["seed"])
    anchor = date.fromisoformat(meta["anchor_start"])
    lo, hi = meta["calls_per_week"]
    records = []
    for week in range(meta["weeks"]):
        wstart = anchor + timedelta(days=7 * week)
        for rep in personas["reps"]:
            for _ in range(rng.randint(lo, hi)):
                ct = rng.choice(personas["call_types"])
                product = rng.choice(rep["products"])
                scores = {}
                for i, dkey in enumerate(dims):
                    mean = rep["dim_base"][i] + rep["weekly_delta"] * week
                    scores[dkey] = round(clamp(mean + rng.gauss(0, rep["noise"])), 1)
                day = wstart + timedelta(days=rng.randint(0, 4))
                records.append({
                    "rep_id": rep["id"], "rep_name": rep["name"],
                    "date": day.isoformat(), "call_type": ct, "product": product,
                    "overall": overall_score(scores, weights, ct),
                    "dimensions": scores, "kind": "seeded_history",
                })
    records.sort(key=lambda r: (r["date"], r["rep_id"]))
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "history.json").write_text(json.dumps(records, indent=2))
    return records


# ---- Claude-generated transcripts (needs API key) ---------------------------

TRANSCRIPT_PROMPT = """You are generating a REALISTIC but fully SYNTHETIC sales-call transcript for \
an internal enablement demo. No real people or companies. Buyer = a US home-care agency \
owner/operator. Seller = a Sensi.AI rep selling {product}.

Call type: {call_type}. Target rep quality: {quality}.

Write a natural {length}-turn transcript, speaker-labeled with exactly "Rep:" and "Prospect:" at \
the start of each line, alternating naturally (a speaker may take several sentences in one turn). \
Make the quality show through BEHAVIOR, not labels — and CONTROL THE WORD BALANCE between speakers \
exactly as specified below (this is scored):
{quality_notes}

Return ONLY the transcript lines. No preamble, no markdown, no headings."""

QUALITY_NOTES = {
    "strong": "- WORD BALANCE (important): the REP should speak only ~45-55% of total words. The "
              "rep asks SHORT questions, then STOPS; the PROSPECT answers in full multi-sentence "
              "paragraphs. Do not let the rep monologue.\n"
              "- Rep opens with 2-3 fresh discovery questions before any product talk.\n"
              "- Ties value to the buyer's levers (billable hours, turnover, length of stay).\n"
              "- Uses only credible Sensi proof (e.g. 35% more billable hours, 2.6x conversion).\n"
              "- Catches and qualifies any buying signal; books a firm, dated next step.",
    "weak":   "- WORD BALANCE (important): the REP should speak ~82-88% of total words. The rep "
              "delivers LONG multi-sentence monologues; the PROSPECT mostly gives SHORT one-line "
              "replies ('okay', 'right', 'sure', 'makes sense'). \n"
              "- Rep skips discovery and jumps to a screen-share in the first turn.\n"
              "- Uses a LEADING close ('would you agree I'm being conservative?').\n"
              "- Invents numbers (a specific $ ROI figure, a survey that doesn't exist).\n"
              "- A key buying signal (owner is selling the business) surfaces late and is NOT qualified.\n"
              "- Manufactured urgency ('offer valid until end of month'); no firm next meeting.",
    "mixed":  "- WORD BALANCE: the REP should speak ~65-72% of total words; the prospect gets real "
              "airtime in a few places but the rep still drives.\n"
              "- Some genuine discovery (not deep); ties value to at least one real buyer lever.\n"
              "- Uses ONLY real, credible Sensi proof (e.g. 35% more billable hours, 2.6x "
              "conversion) — NO invented numbers, NO fabricated case studies.\n"
              "- Handles an objection reasonably; loosely proposes a next meeting but is a bit soft "
              "on locking it ('I'll follow up next week').\n"
              "- No leading closes, no manufactured urgency.",
    "developing": "- WORD BALANCE: the REP should speak ~72-78% of total words.\n"
              "- Attempts discovery but it's shallow — asks 1-2 questions then reverts to pitching.\n"
              "- Uses ONLY real Sensi proof but leans on a single point; MISSES following up on a "
              "buying signal the prospect drops.\n"
              "- Next step is vague ('I'll send some info over'); no meeting is firmly booked.\n"
              "- No fabrication, no leading close, no manufactured urgency — this call is MEDIOCRE, "
              "not unethical, so it should have few or no red-flag behaviors.",
}


def parse_turns(text):
    turns = []
    for line in text.splitlines():
        line = line.strip()
        m = re.match(r"^(Rep|Prospect)\s*:\s*(.+)$", line, re.IGNORECASE)
        if m:
            turns.append({"speaker": m.group(1).title(), "text": m.group(2).strip()})
    return turns


# Curated UNSCORED demo calls — transcripts committed WITHOUT an eval, so the app shows a "Process"
# button and Janos can kick off the whole pipeline live (the manual stand-in for production's
# automated post-call trigger). Spread across archetypes so the default rep (R1) and the manager
# both have unscored calls. Explicit params + baked day offsets → reproducible, and the `_new`
# call-ids don't collide with the scored set.
UNSCORED_DEMO = [
    {"rep": "R1", "call_type": "discovery",  "product": "Platform", "quality": "strong",     "day": 44},
    {"rep": "R3", "call_type": "demo_close",  "product": "Sally",    "quality": "developing", "day": 45},
    {"rep": "R4", "call_type": "discovery",  "product": "Cally",    "quality": "weak",       "day": 46},
    {"rep": "R5", "call_type": "follow_up",   "product": "Olly",     "quality": "mixed",      "day": 47},
]


def gen_unscored(personas, client, model, overwrite):
    """Generate the curated unscored demo transcripts (no eval written — the app scores them live)."""
    SYNTH.mkdir(parents=True, exist_ok=True)
    reps = {r["id"]: r for r in personas["reps"]}
    anchor = date.fromisoformat(personas["meta"]["anchor_start"])
    made = []
    for spec in UNSCORED_DEMO:
        rep = reps[spec["rep"]]
        ct, product, quality = spec["call_type"], spec["product"], spec["quality"]
        call_id = f"{rep['id']}_{CT_ABBR[ct]}_new"
        out = SYNTH / f"{call_id}.json"
        if out.exists() and not overwrite:
            print(f"  skip {call_id} (exists)")
            made.append(call_id)
            continue
        length = 18 if ct == "follow_up" else 26
        prompt = TRANSCRIPT_PROMPT.format(
            product=product, call_type=ct, quality=quality, length=length,
            quality_notes=QUALITY_NOTES[quality])
        print(f"  generating UNSCORED {call_id} ({quality}, {ct}, {product}) …")
        resp = client.messages.create(
            model=model, max_tokens=4000, messages=[{"role": "user", "content": prompt}])
        turns = parse_turns("".join(b.text for b in resp.content if b.type == "text"))
        if len(turns) < 6:
            print(f"    ! only {len(turns)} turns parsed — check output; keeping anyway")
        cdate = anchor + timedelta(days=spec["day"])
        out.write_text(json.dumps({
            "call_id": call_id, "rep_id": rep["id"], "rep_name": rep["name"],
            "product": product, "account": account_for(call_id, personas["accounts"]),
            "call_type": ct, "date": cdate.isoformat(),
            "quality_profile": quality, "kind": "synthetic", "scored": False,
            "turns": turns,
        }, indent=2))
        made.append(call_id)
    return made


def gen_transcripts(personas, per_rep, overwrite):
    try:
        import anthropic
    except ImportError:
        sys.exit("anthropic not installed — `pip install -r requirements.txt` in the build venv.")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY not set — export it (or put it in build/.env) and retry.")

    model = os.environ.get("REPCOACH_MODEL", "claude-sonnet-5")
    client = anthropic.Anthropic()
    SYNTH.mkdir(parents=True, exist_ok=True)
    rng = random.Random(personas["meta"]["seed"] + 1)
    anchor = date.fromisoformat(personas["meta"]["anchor_start"])

    # quality by archetype so the live set mirrors the dashboard story:
    # R1 benchmark · R2 solid · R3 ramping (mediocre, no red flags) · R4 escalation (bad) · R5 improving
    quality_by_rep = {"R1": "strong", "R2": "mixed", "R3": "developing",
                      "R4": "weak", "R5": "mixed"}
    made = []
    for rep in personas["reps"]:
        quality = quality_by_rep.get(rep["id"], "mixed")
        for j in range(per_rep):
            ct = rng.choice(personas["call_types"])
            product = rng.choice(rep["products"])
            call_id = f"{rep['id']}_{CT_ABBR[ct]}_{j+1:03d}"
            out = SYNTH / f"{call_id}.json"
            if out.exists() and not overwrite:
                print(f"  skip {call_id} (exists)")
                made.append(call_id)
                continue
            length = 18 if ct == "follow_up" else 26
            prompt = TRANSCRIPT_PROMPT.format(
                product=product, call_type=ct, quality=quality, length=length,
                quality_notes=QUALITY_NOTES[quality])
            print(f"  generating {call_id} ({quality}, {ct}, {product}) …")
            resp = client.messages.create(
                model=model, max_tokens=4000,
                messages=[{"role": "user", "content": prompt}])
            turns = parse_turns("".join(b.text for b in resp.content if b.type == "text"))
            if len(turns) < 6:
                print(f"    ! only {len(turns)} turns parsed — check output; keeping anyway")
            cdate = anchor + timedelta(days=rng.randint(0, 41))
            out.write_text(json.dumps({
                "call_id": call_id, "rep_id": rep["id"], "rep_name": rep["name"],
                "product": product, "account": account_for(call_id, personas["accounts"]),
                "call_type": ct, "date": cdate.isoformat(),
                "quality_profile": quality, "kind": "synthetic",
                "turns": turns,
            }, indent=2))
            made.append(call_id)
    return made


# ---- main -------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-transcripts", action="store_true",
                    help="also generate Claude transcripts (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--unscored", action="store_true",
                    help="generate the curated UNSCORED demo transcripts (no eval; needs API key)")
    ap.add_argument("--per-rep", type=int, default=2, help="transcripts per rep (default 2)")
    ap.add_argument("--overwrite", action="store_true", help="regenerate existing transcripts")
    args = ap.parse_args()

    # optional: load build/.env so a key there is picked up without exporting
    envfile = HERE / ".env"
    if envfile.exists():
        for line in envfile.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

    personas, rubric, dims, weights = load_cfg()
    records = build_history(personas, dims, weights)

    # quick, human-readable summary so a run is informative
    by_rep = {}
    for r in records:
        by_rep.setdefault(r["rep_id"], []).append(r["overall"])
    print(f"history: {len(records)} records → data/history.json")
    for rep in personas["reps"]:
        vals = by_rep.get(rep["id"], [])
        avg = round(sum(vals) / len(vals)) if vals else 0
        print(f"  {rep['id']} {rep['name']:<16} n={len(vals):<3} avg={avg:<3} — {rep['archetype']}")

    if args.with_transcripts:
        made = gen_transcripts(personas, args.per_rep, args.overwrite)
        print(f"transcripts: {len(made)} → data/synthetic/")
    else:
        print("transcripts: skipped (pass --with-transcripts + an API key to generate)")

    if args.unscored:
        try:
            import anthropic
        except ImportError:
            sys.exit("anthropic not installed — `pip install -r requirements.txt` in the build venv.")
        if not os.environ.get("ANTHROPIC_API_KEY"):
            sys.exit("ANTHROPIC_API_KEY not set — export it (or put it in build/.env) and retry.")
        client = anthropic.Anthropic()
        model = os.environ.get("REPCOACH_MODEL", "claude-sonnet-5")
        made = gen_unscored(personas, client, model, args.overwrite)
        print(f"unscored demo transcripts: {len(made)} → data/synthetic/ (no evals)")


if __name__ == "__main__":
    main()
