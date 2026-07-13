# Rep Coach — Product Requirements (PRD)

**Phase 2 · Build** · Janos Kristof · *derived from the Phase 1 diagnosis*

> **One-line product.** Rep Coach scores every sales call against a Sensi-tuned rubric, hands the
> rep two specific fixes for the next call, and hands the manager a triaged coaching queue —
> without an hour of manual review. It **installs measurement where there is none today.**

This PRD is deliberately short. It exists so the build has acceptance criteria to hit and so the
*way* we build it (the agentic loop in `tool_note.md`) has a target. Design lives in `design.md`.

---

## 1. Why this, and who it's for

The Phase 1 diagnosis found one root cause behind the six stated pains: **no closed loop turns
each call into tracked, improving rep behavior.** Rep Coach is the cheapest place to install that
loop — it *creates the baseline from call one*.

| Persona | Job-to-be-done | What Rep Coach gives them |
|---------|----------------|---------------------------|
| **Rep** | "How did my last call go, and what do I fix before the next one?" | A per-call scorecard with evidence, the top-2 focus areas, and recommended micro-content |
| **Manager** | "Who needs coaching this week — without me reviewing every call?" | A team rollup, an auto-flagged escalation queue, and a triaged coaching queue |
| **Enablement / coach** | "What's *systematically* weak across the team?" | Trend dashboards by rep and by rubric dimension over time |

---

## 2. Scope

**In scope (the running prototype):**
- Score a speaker-labeled transcript against a **call-type-aware rubric** (`rubric.yaml`).
- **Hybrid scoring** — deterministic metrics in code + LLM judgment with **verbatim evidence quotes**.
- A **user picker** (dropdown of all users) that drives the app — pick a **rep** → that rep's own
  tabs (**My Calls · Trends · Activity**); pick the **manager** → team tabs (**Calls · Team ·
  Trends · Measurement · Activity**). A **call list → call detail** workflow with a per-row
  **Details / Process** button.
- **Inline Process** — an unscored call is scored live by the real engine on demand and
  **auto-routes** the coaching loop (session-only; the committed dataset stays reproducible).
- **Mock routing** — processing writes Slack/HubSpot actions to a local log (adapter seam), shown
  as **per-call activity** on the detail page.
- A **reproducible, offline, NDA-safe synthetic dataset** (5 reps, 3 call types, the Sensi agent
  suite) + the one anonymized real call, with seeded score history for the dashboards.

**Mocked (prototype only, real in production → the production-readiness session):**
- The **"call-complete" trigger** — a file-drop / button stands in for a Jiminny webhook.
- **Slack + HubSpot** — behind a clean adapter interface; prototype impls write locally.

**Out of scope (explicitly deferred):**
- Auth / RBAC, multi-tenant, real integrations, real-time ingestion, production orchestration.
- Rebuilding conversation intelligence (capture/transcription = **buy**, per `make_vs_buy.md`).

**Companion deliverable — `tool_note.md` (the assignment's "short note").** The running app is
half the Phase-2 deliverable; the note is the other half and **must** cover, concisely:
- **What it solves** — the problem from the diagnosis, in one paragraph.
- **How it works** — the hybrid scoring loop + rubric-as-config (points to `design.md`).
- **How I built it** — the **agentic SDLC** (implement → verify → adversarial review → iterate);
  this is an *explicit, graded* assignment ask ("show us how you built it"), not an afterthought.
- **Path to production** — a *concise* summary (trigger, data safety, HubSpot surface, human-in-loop);
  the deep dive is the dedicated production-readiness session.
- **What I'd build next** — the near-term roadmap beyond the prototype.

---

## 3. Functional requirements

**FR1 — Score a call.** Given a speaker-labeled transcript + its metadata (rep, product, call
type), produce an **evaluation record**: overall score, per-dimension score + **evidence quotes**
+ a coaching tip, deterministic metrics, flags, and recommended micro-content.

**FR2 — Rubric as config.** All dimensions, weights, and call-type weightings live in
`rubric.yaml` — **no code change** to add a dimension or retune weights. Rubric is **versioned**.

**FR3 — Hybrid, explainable scoring.** Deterministic signals (talk/listen ratio, question counts,
next-step booked) are computed in code and shown; LLM-judged dimensions must cite **verbatim
quotes** from the transcript. Nothing is an unexplained number.

**FR4 — Rep view: call list → detail.** *My Calls* lists the rep's calls (Date · Account ·
Product · Type · **Overall**; unscored → "—"). Clicking a call opens its **detail**: the visual
scorecard (overall + per-dimension bars, expandable evidence), an **overall summary** (the LLM's,
or a generated fallback), **Coach's next steps** (top-2 focus fixes + tips merged with recommended
micro-content), and the **per-call integration activity**.

**FR4b — Process an unscored call.** A call with no evaluation opens a **Process** button that runs
the whole pipeline live (deterministic + LLM scoring, then routing) — the manual stand-in for
production's automated post-call trigger. Processed results persist in session state (the committed
dataset stays reproducible); the demo ships with **unscored transcripts** so Process has real work.

**FR5 — Manager view.** Team rollup (rep × avg score + trend), an **escalation queue** (calls with
extreme gaps auto-flagged), and a **coaching queue** (who to coach this week). A manager can open
**any rep's** call detail — from the all-reps *Calls* list or straight from the Team queues.

**FR6 — Trend dashboard.** Scores over time by rep and by dimension, from seeded history — the
five rep archetypes produce a readable story (benchmark, ramp curve, plateau, improvement).

**FR7 — Routing (auto).** Processing a call **auto-routes** the coaching loop — a Slack nudge and a
HubSpot scorecard + coaching task — to a local log (adapter seam), proving the loop *routes*, not
just scores. (No manual "Send to Slack / Create HubSpot" buttons; routing is a consequence of
processing, as it would be in production.)

**FR7b — Per-call activity.** Each call's **detail page** shows the integration actions routed for
that call — **endpoint** (Slack / HubSpot / …), **type** (nudge / task / scorecard), **timestamp**,
and **content**. This makes the integration points visible on the record itself — the prototype
stand-in for the HubSpot activity timeline in production.

**FR8 — Measurement panel.** Show **leading/internal** — *adoption* (rec-adoption, coaching
tasks completed / followed up, coverage %), *usage* (weekly-active reps, content engagement,
return rate), *behavior change* (recommended fixes recur on later calls, flagged-dimension
movement) — and **lagging/external** (call-quality trend, ramp-time proxy, conversion proxy),
with the honest
baseline note.

**FR9 — Templatable (Phase 3 hook).** Pointing the app at a *second* rubric (e.g. a CS-QA variant)
scores a different call type with **no code change**.

---

## 4. Non-functional requirements

- **NFR1 · NDA-safe & offline.** Only synthetic text is sent to the LLM; the one real call is
  anonymized. Runs without network except the LLM call; pre-computed evaluations are cached so the
  demo is stable.
- **NFR2 · Reproducible.** Fixed seed + baked-in dates (no wall-clock / RNG at runtime).
  Regenerating data and re-scoring is one documented command each.
- **NFR3 · Explainable.** Evidence quotes + deterministic metrics are always visible next to scores.
- **NFR4 · Fast enough to demo live.** Cached evaluations render instantly; a single live
  re-score returns in a few seconds.
- **NFR5 · One-person maintainable.** Small, readable modules; config over code; a `.env.example`;
  no bespoke infra.
- **NFR6 · Model-configurable.** LLM model is a config value (default **Claude Sonnet 5**),
  swappable without code changes; structured output is schema-validated.

---

## 5. Acceptance criteria (map 1:1 to Verification, and to the 2E gates)

| # | Acceptance criterion | Verifies |
|---|----------------------|----------|
| **AC1** | `pip install -r requirements.txt && streamlit run app.py` → app loads | It runs |
| **AC2** | Select a transcript → scorecard renders with per-dimension scores, evidence quotes, tips | FR1, FR3, FR4 |
| **AC3** | Deterministic metrics (talk/listen ratio, question count) match a hand check on one transcript | FR3 |
| **AC4** | Manager view shows the rollup; an extreme-gap transcript surfaces in the escalation queue | FR5 |
| **AC5** | Trend dashboard renders variance across reps/time from seeded history | FR6 |
| **AC6** | Processing a call **auto-routes** a Slack nudge + a HubSpot scorecard + a coaching task to the local log (no manual "Send" buttons — routing is a consequence of Process, per FR7); the routed actions appear as that call's per-call activity | FR7, FR7b |
| **AC7** | Measurement panel shows leading + lagging metrics populated | FR8 |
| **AC8** | **Templating (done):** `rubric_csqa.yaml` (a CS-QA variant) + a support transcript scored by the **unchanged** engine via `verify_ac8.py` → **93/100**, all 6 support dimensions incl. the reused deterministic/hybrid signals. Sales golden-check still passes (the committed weak-archetype calls R4_disc_001/002 score **10/100** and **5/100**, each firing all three pressure flags; a live re-score lands in the same single-digit band — see the invariant below). | FR2, FR9 |
| **AC9** | **Process (live):** opening an **unscored** call shows a Process button → the real engine runs (deterministic + Claude) → the detail renders the scorecard, and the auto-routed Slack + HubSpot actions appear as that call's **per-call activity** | FR1, FR3, FR4b, FR7, FR7b |
| **AC10** | **Daily-use UX:** a **user picker** selects a rep (→ own **My Calls · Trends · Activity** tabs) or the manager (→ **Calls · Team · Trends · Measurement · Activity** tabs); calls open via a per-row **Details / Process** button; a manager can open any rep's call detail; **no left sidebar** | Usability, FR4, FR5 |

> **Gate note (why AC9/AC10 exist).** These two came from a **human click-through**, not the
> automated gates — and that is the point. The engineering gate proves the tool *runs correctly*;
> the content-validation gate is a **text-reading reviewer** that cannot feel a sidebar or notice
> that scoring is pre-computed. AC1–AC8 were all satisfied by rendering cached evaluations, so the
> "would a rep actually *use* this daily?" gap slipped through. **AC9/AC10 must be verified by a
> human or a Playwright click-through**, not the text gate — they close that blind spot.

**Golden-transcript check (build-time):** the anonymized real call must score **low** on exactly
the dimensions it fails — *discovery quality, buying-signal handling, proof-point fidelity,
next-step specificity* — and the pressure/authenticity flag must fire on the manufactured
urgency. If a known-bad call scores well, the rubric is wrong.

> **Templating note (AC8 finding).** Building the CS-QA variant surfaced two remaining sales-isms
> hardcoded in the LLM prompt — the evaluator **role** and the **flag list**. Both were generalized
> to read from the rubric (`evaluator_role` + `flags.types`), a **one-time** engine change that
> makes the loop *fully* rubric-driven: dimensions, weights, motion, proof, role, and flags are all
> config now. After that, a new team is genuinely a new YAML, not new code — exactly what the
> templating slice is meant to prove (and to surface). The CS-QA rubric reuses the engine's
> deterministic/hybrid dimension **keys** (`talk_listen_balance`, `discovery_quality`, `next_step`)
> because those signals transfer to support QA; only the labels/descriptions change.

---

## 6. Success metrics (how we'd know it worked — "if you can't measure it, it didn't work")

The three internal signals the assignment names — **adoption, usage, behavior change** — are
tracked distinctly; the external signals are the outcome metrics.

**Leading — internal (weeks):**
- **Adoption** — recommendation-adoption rate; **coaching tasks completed / followed up** (the
  HubSpot to-dos actually closed); coverage % (share of calls actually evaluated).
- **Usage** — **weekly-active reps**; **training / coaching-content engagement** (recommended
  micro-content opened from a scorecard); **return rate** (do reps come back to their scorecard?)
  — the direct counter to the falsification "reps open it once and never return."
- **Behavior change** — **recommended fixes recur on later calls** (the coaching actually changes
  behavior); flagged-dimension score movement per rep after coaching.

**Lagging — external (quarter):** **call quality** (average rubric-score trend per rep),
**ramp-time** to full productivity, **conversion / win-rate** by stage.

**Baseline note (honest):** none of these are measured today — Rep Coach **creates the baseline
from call one**. The prototype's measurement panel demonstrates the metric definitions on
synthetic data; production wires the lagging metrics to HubSpot's real outcome data.

---

## 7. Open questions (resolved in discovery / the production session)
- Are Jiminny's own scorecard/tracker features licensed and sufficient for the rubric? → decides
  how much of the loop is *build* vs *configure* (`make_vs_buy.md`).
- HubSpot tier (UI Extensions / custom objects / Operations Hub availability) → shapes the
  production write-back surface.
