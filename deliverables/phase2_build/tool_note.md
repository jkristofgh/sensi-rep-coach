# Rep Coach — Tool Note

**Phase 2 · Build** · Janos Kristof · *the companion note to the running app in `build/`*

> **One line.** Rep Coach scores every sales call against a Sensi-tuned rubric, hands the rep two
> specific fixes for the next call, and hands the manager a triaged coaching queue — **without an
> hour of manual review.** It installs measurement where there is none today.

This note covers, briefly: **what it solves · how it works · how I built it (the agentic SDLC) ·
how it's measured · the path to production · what I'd build next.** Requirements are in
[prd.md](prd.md); architecture, schemas, and UX flows are in [design.md](design.md).

---

## What it solves

The Phase-1 diagnosis funnelled Sensi's six stated pains to one root cause: **no closed loop turns
each call into tracked, improving rep behavior.** Sensi generates rich signal on every call (a full
Jiminny transcript) and throws it away — a measurement vacuum. Managers are the binding constraint:
coaching doesn't scale because reviewing calls is manual. Rep Coach is the cheapest place to install
the loop — it **creates the baseline from call one** and offloads the review from the manager.

The bet (Phase 1): automate **post-call evaluation + coaching**. One build moves the most pains at
once — it directly solves QA, manager load, and rep support, and unlocks knowledge, ramp, and stack
consolidation. This tool is that build.

---

## How it works

A post-call loop, hybrid and explainable by design (detail in [design.md](design.md)):

- **Signal → rubric → evaluate → recommend → route.** A speaker-labeled transcript is scored
  against [`rubric.yaml`](../../build/rubric.yaml) and an evaluation record is produced.
- **Hybrid scoring — [`scoring.py`](../../build/scoring.py).** Half the signal is **deterministic,
  computed in code** (talk/listen ratio, open-question density, next-step-booked, monologue length);
  the other half is **Claude (Sonnet 5)** via Anthropic **tool-use**, which returns a schema-valid
  per-dimension score, a **verbatim evidence quote**, and a coaching tip — plus flags and
  recommendations. *Nothing is an unexplained number:* every LLM score cites the quote it's based on.
- **Rubric-as-config — the templatable seam.** All dimensions, weights (per call type), the
  prescribed motion, the published proof wall, the evaluator role, and the flag set live in the
  rubric YAML. **No code change** to retune weights, add a dimension, or stand up a new team
  (see *Templating* below).
- **Surfaces — [`app.py`](../../build/app.py) (Streamlit).** A user picker drives the app: pick a
  **rep** → their *My Calls · Trends · Activity*; pick the **manager** → *Calls · Team · Trends ·
  Measurement · Activity* across the whole team. A **call list → detail** workflow: each call opens
  a scorecard (per-dimension chips + evidence + Coach's next steps), the full transcript, and the
  per-call integration activity. An **unscored** call opens a **Process** button that runs the whole
  pipeline live — the manual stand-in for production's automated post-call trigger.
- **Mock routing behind an adapter seam — [`adapters.py`](../../build/adapters.py).** Processing a
  call **auto-routes** a Slack nudge + a HubSpot scorecard + a coaching task to a local log. The
  scoring core never talks to Slack/HubSpot directly; it calls narrow `Notifier`/`CRM` protocols, so
  the production swap is an adapter change, not a rewrite. This is the exact seam that becomes
  "HubSpot as the single surface" in Phase 3.
- **Reproducible, NDA-safe data — [`generate_data.py`](../../build/generate_data.py) +
  [`personas.yaml`](../../build/personas.yaml).** A fixed seed and baked-in dates (no runtime RNG or
  wall-clock) produce five rep archetypes that tell a dashboard story — a benchmark, a ramp curve, a
  plateau, an improvement curve — plus ~7 weeks of seeded history, 10 live-scored transcripts, and 4
  unscored demo calls. Only synthetic text is ever sent to the LLM; the one real call is anonymized.

---

## How I built it — an agentic SDLC (the meta-proof)

**I built this the way this role operates: one person + AI agents doing what used to take an ops
team.** Phase 2 ran as a compressed, documented software lifecycle, not an ad-hoc build:

> **requirements ([prd.md](prd.md)) → design ([design.md](design.md)) → an agentic loop of
> implement → verify in the *running* app → adversarial review → iterate to the acceptance
> criteria.**

Built in **vertical slices** (rubric+schema → deterministic metrics → LLM scoring → store → rep view
→ manager view → trends → measurement → routing → templating), each slice run through the loop until
it met its PRD acceptance criterion. What made it real:

- **Verify against behavior, not unit tests alone.** A committed Playwright suite
  ([`verify_ui.py`](../../build/verify_ui.py)) drives the *running* app on a fresh server per view
  and **screenshots every surface** — including a live **Process** run that scores an unscored call
  end-to-end — so "it works" means the pixels are right, not just that a function returned. The
  screenshots were read back and drove the next iteration. (This gate re-ran it green: the three
  cached-path scenarios pass, and the live Process scenario renders the scorecard in ~16s.)
- **A golden-transcript check.** A known-bad call must score **low on exactly the dimensions it
  fails** and fire the manufactured-urgency flag. If a bad call scores well, the rubric is wrong.
  (Re-verified after every scoring change. Because the score is a live LLM judgment it drifts a few
  points run-to-run, so the *invariant* is what's checked — not a fixed number: the weak archetype
  lands in the single-digit band and fires all three pressure flags. The committed weak calls score
  **10/100** and **5/100**; a fresh re-score during this gate came back **2/100** — different number,
  same verdict.)
- **The loop caught real defects — a few worth naming as evidence:**
  - **A demo-blocking stability bug.** The app threw an intermittent "Connection error" in a manual
    test. No Python traceback → a *native* segfault: bleeding-edge Streamlit 1.59 + pandas 3.0 +
    pyarrow 25 crashing during Arrow serialization. Fixed by pinning to a verified stable combo
    (`requirements.txt`) — the kind of bug only a *drive-the-running-app* verify pass surfaces.
  - **Robustness to structured-output quirks.** Claude occasionally crammed the whole payload into
    one string field or returned scalar evidence; the LLM pass gained retries + a
    concatenated-JSON recovery path + normalization so the return is always usable.
  - **The gate has blind spots — and a human caught them.** The automated content gate is a
    *text-reading* reviewer; it can't feel a sidebar or notice that scoring is pre-computed. A manual
    click-through did, which is why **AC9 (live Process) and AC10 (daily-use UX)** were *added* to
    the PRD as human/Playwright-verified criteria. The gate now has teeth it didn't before.
  - **Templating surfaced a coupling (AC8).** Standing up a second team (CS-QA) exposed two
    sales-isms hardcoded in the LLM prompt — the evaluator role and the flag list. Both were
    generalized to read from the rubric, making the loop *fully* config-driven. The exercise proved
    reuse **and** removed the thing blocking it.

The point isn't the tool alone — it's that the **operating model** (agents implementing, a harness
verifying against real behavior, adversarial review, iterate) is repeatable and is itself the
AI-enablement capability the role is about.

---

## How it's measured — "if you can't measure it, it didn't work"

Baked into the tool (Measurement tab), split the way the assignment names them:

- **Leading / internal (weeks):** **adoption** (recommendation-adoption, coaching tasks completed /
  followed up, coverage %), **usage** (weekly-active reps, training / coaching-content engagement,
  return rate — the direct counter to "reps open it once and never return"), **behavior change**
  (recommended fixes recur on later calls, flagged-dimension score movement per rep).
- **Lagging / external (quarter):** call-quality trend, ramp-time, conversion / win-rate — wired to
  HubSpot outcome data in production.
- **Honest baseline:** none of this is measured today. Rep Coach **creates the baseline from call
  one**; the internal metrics are computed from real evaluations, the lagging ones are proxies until
  the HubSpot wiring exists.

---

## Path to production (concise — the deep dive is the production-readiness session)

- **Trigger.** Replace the manual Process button with a **Jiminny call-complete webhook** — no
  manual upload.
- **Data safety.** A zero-retention, **BAA** LLM endpoint; PII handling; in-region — NDA/HIPAA
  posture. Prototype sends only synthetic text.
- **Surface = HubSpot (kills the multi-tool jump, pain #1).** The scorecard is attached to the call
  record; follow-ups become HubSpot **tasks** (prospect next-steps *and* rep coaching to-dos);
  rollup/queues/trends are **native HubSpot dashboards**; Slack is a nudge layer that deep-links
  back. The prototype's adapter seam is exactly where this swaps in.
- **Human-in-loop.** Escalations, rubric changes, and high-stakes coaching stay human.
- **Runs without me.** Versioned rubric, monitoring, one-command deploy, config over code.

Full make-vs-buy, the orchestration decision (HubSpot-native vs. n8n — challenged, not assumed), and
the non-functional detail live in `production_readiness/`.

---

## Templating (the Phase-3 hook, proven now — AC8)

The engine is generic; **only the rubric + the signal source change per team.** Proven with a second
instance: [`rubric_csqa.yaml`](../../build/rubric_csqa.yaml) (Customer-Support QA on support calls),
scored by the **unchanged** engine via [`verify_ac8.py`](../../build/verify_ac8.py) — a support
transcript scored **93/100** across six support-specific dimensions, reusing the deterministic/hybrid
signals as-is. *For a team whose signals map onto the existing ones, a new team is a new YAML, not
new code* — CS-QA reuses the three deterministic keys (agent airtime, probing-question density, a
firm follow-up) because those transfer directly to support. The honest boundary: a genuinely *new*
deterministic signal (say, hold-time) is a one-time addition to the scoring engine, then it too
becomes config — the LLM-judged dimensions, weights, motion, proof wall, evaluator role, and flags
are already fully rubric-driven. The Phase-1 "one build → many pains" and this "one engine → many
teams" are the same idea on two axes — the compounding argument.

---

## What I'd build next

1. **Wire the real trigger + HubSpot write-back** (Jiminny webhook → scorecard on the call record).
2. **Rubric v2 from outcomes** — once calls link to won/lost and ramp data, tune weights to what
   actually predicts results, and add a lightweight review step where managers correct scores (the
   labels that improve the rubric over time).
3. **Close the content loop** — recommended micro-content that adapts to each rep's weakest
   dimensions, sourced from the product KB.
4. **Second team live** — stand up CS-QA (or onboarding knowledge checks) on real calls to prove the
   pattern compounds, then make the production-orchestration call.
