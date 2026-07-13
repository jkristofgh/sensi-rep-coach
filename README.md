# Rep Coach — Seller Enablement Intelligence

**A post-call coaching loop for Sensi.AI's sales org.** Every call is scored against a
Sensi-tuned rubric; the rep gets two concrete fixes, the manager gets a triaged coaching
queue — without an hour of manual review. Built as a take-home for the **GTM AI Enablement
Lead** role.

> **The bet:** Sensi generates rich behavioral signal on every sales call and throws it away.
> There is no closed loop that turns each call into *tracked, improving rep behavior.* That
> measurement vacuum is the single biggest leverage point — so I built the loop that fills it.

*Prepared under NDA · the one real call is anonymized · only synthetic data is sent to the LLM.*

---

## What's here

```
deliverables/            The written work (read the PDFs, or browse the .md inline)
  presentation/          ← the capstone deck — START HERE (presentation.pdf)
  phase1_diagnose/       Diagnosis, decision log, make-vs-buy
  phase2_build/          PRD, design, tool note  (this app is the build)
  phase3_playbook/       Scalability brief — the pattern that compounds
  production_readiness/  What it takes to run for real (orchestration, security, cost)
app/                     The running Streamlit prototype (Rep Coach)
```

**If you only open one thing:** [`deliverables/presentation/presentation.pdf`](deliverables/presentation/presentation.pdf) —
the ~1-hour capstone that ties the three phases together. `presentation_presenter.pdf` is the
sparse talk-track cut of the same deck.

Each phase ships two PDFs: a **detail** report (portrait) and a **summary** deck (landscape).

---

## Run the tool (≈2 minutes)

Requires **Python 3.11+** and an **Anthropic API key** (the live scoring path calls Claude).

```bash
cd app
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then edit .env and add your key:
#   ANTHROPIC_API_KEY=sk-ant-...

streamlit run app.py
```

The app opens in your browser. It runs entirely on **synthetic data + one anonymized real
call** — no Sensi systems are touched.

### What to click
- **Rep persona** → *My Calls*: open a scored call for the full scorecard (per-dimension
  chips, evidence quotes, Coach's next steps); *Trends* shows the score trajectory.
- **Process a call live:** open an **unscored** call → **⚡ Process** → the real engine
  (deterministic metrics + Claude) scores it in seconds and **auto-routes** a (mock) Slack
  nudge + HubSpot scorecard/task. That's the loop closing.
- **Manager persona** → *Calls* (any rep), *Team* (rollup + escalation queue),
  *Measurement* (leading/lagging metrics), *Activity* (every routed action in one feed).

No key handy? The dashboards, scorecards, and Activity feed all render from **pre-computed**
evaluations committed in `app/data/` — only the live **Process** button needs the LLM.

---

## How it works (the short version)

- **Hybrid, explainable scoring** — half the score is deterministic **math** (talk/listen ratio,
  question counts, computed in code); the LLM half scores the softer dimensions and **always
  cites the evidence quote**. Not an LLM guess. See [`app/scoring.py`](app/scoring.py).
- **Rubric-as-config** — [`app/rubric.yaml`](app/rubric.yaml) is call-type-aware, weighted, and
  versioned. **This file is the reusable seam:** a new team = a new rubric, not new code.
- **Proven templating** — [`app/verify_ac8.py`](app/verify_ac8.py) swaps in a CS-QA rubric and
  scores a support call **on the unchanged engine** (the `app/data/csqa/` fixtures), the
  existence proof behind the "one engine → many teams" argument in Phase 3.
- **Adapter seam** — [`app/adapters.py`](app/adapters.py) isolates Slack/CRM behind a Protocol so
  the production swap (HubSpot, Jiminny) is an adapter change, not a rewrite.
- **Built as an agentic SDLC** — vertical slices, each run through implement → verify in the
  running app → adversarial review → iterate to acceptance. The write-up is in
  [`deliverables/phase2_build/tool_note.md`](deliverables/phase2_build/tool_note.md).

## Notes
- **Synthetic data is deliberate** — reproducible, offline, and NDA-safe. `app/generate_data.py`
  regenerates it; the committed set is stable so the demo is identical every launch.
- Live-processed calls are held in session only — they are **not** written to `app/data/`, so the
  committed dataset stays clean and the "process it live" demo re-runs fresh every time.
- `app/render/` is the self-contained PDF renderer (Markdown → portrait report / landscape deck,
  with a render-fidelity self-check) that produced every PDF in `deliverables/`.
