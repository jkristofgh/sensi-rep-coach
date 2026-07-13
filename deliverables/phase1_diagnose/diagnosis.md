# Phase 1 — Diagnose Before You Build

**GTM AI Enablement — Seller Enablement Intelligence**
Janos Kristof · prepared for Daniel Urcuyo & Daniel Rubin

> **How to read this.** The deliverable here is not the answer — it's the *path* to an answer
> I'd bet on. It walks the discovery in the order I'd run it: interrogate the brief, **mine
> every source we were given** (the real call, the GTM deck, the Guide Book, the product/customer
> materials), then lay out who I'd talk to and what data I'd pull to confirm or kill the
> hypothesis before building. The bet is at the end.
>
> **On the one call — an important caveat.** I treat it as a *revealing sample, not proof of a
> pattern.* It shows the **kind** of gaps that currently go uncaught; it does **not** establish
> that every rep or every call looks like this, and I make no such claim. Whether these gaps are
> systemic is a question the discovery plan (Step 2) answers by *sampling* — it is not an
> assumption baked into the diagnosis. In fact, the point is the opposite: today no one at Sensi
> can say how common these gaps are, because nothing measures calls at all.
>
> *Starting facts already established (from prior interviews): CRM = HubSpot; call recording =
> Jiminny. All references to the real sales call are anonymized (names, agency, PII removed).*

---

## Step 0 — Interrogate the brief before trusting it

The brief hands me six neat pain points. The fastest way to build the wrong thing is to treat
those six as the problem. They read as **symptoms**. My first move is to ask: *what single
condition would produce all six at once?*

| # | Stated pain | Symptom or root cause? |
|---|-------------|------------------------|
| 1 | Fragmented tech stack, no unified system | Symptom — tooling gap |
| 2 | QA manual & mostly not happening | Symptom — no process |
| 3 | Managers overloaded, coaching gets cut | Symptom — capacity |
| 4 | Reps have no AI to get better | Symptom — tooling gap |
| 5 | Persona/product knowledge inconsistent | Symptom — content gap |
| 6 | Onboarding ramp too long | Symptom — outcome of 1–5 |

All six share one root: **there is no closed loop that turns each sales call into tracked,
improving rep behavior.** Sensi generates a rich behavioral signal on every call and then
throws it away. Nothing measures how a rep actually performed, nothing routes that into a
next action, and nothing tracks whether it led to improvement. Every stated pain is a
downstream consequence of that missing loop — which is why fixing any one of them in isolation
(buy a KB, write a QA checklist, hire enablement) doesn't compound.

This reframing matters because it changes what "good" looks like: the win isn't a better tool,
it's **installing measurement where none exists** — and measurement is also the cheapest,
fastest thing one person can build.

## Step 1 — Mine every source, then pressure-test the one real call

I worked all the material we were given — because the fastest way to find the *real* problem is
to compare what Sensi *says* a great sale looks like (deck, Guide Book) against what the one real
call *actually* shows.

| Source | What I pulled from it | How it feeds the diagnosis |
|--------|-----------------------|----------------------------|
| Situation brief | Six stated pains | Reframed as symptoms (Step 0) |
| **Real sales call** (Jiminny) | The only behavioral ground truth we have | The evidence base — teardown below |
| **GTM deck** | Sensi's *prescribed* call motion + its published proof metrics | The benchmark I measure the call against |
| **Guide Book** | Product/agent definitions; ops-pain framing | Confirms product taxonomy + buyer pain |
| **Product / customer materials** (Solo Care, customer stories, deck videos\*) | Persona language, outcome claims | Rubric inputs — what a good call should cite |
| sensi.ai / profile | Category, ICP, business context | Grounding |

\*I transcribed the deck's embedded videos locally (offline, NDA-safe). They corroborate the
published outcomes in customers' *own voices* — one agency owner recounts her call-to-assessment
conversion climbing **33% → 85%** (plus weekly billable hours 1,189 → 2,201 and clients 88 → 220)
on camera. That sharpens the point below: **credible, attributable numbers were sitting on Sensi's
own customer videos — the rep ignored them and invented his own.**

Now the one real call (a ~50-minute second-stage demo/close with a home-care agency owner) — the
only behavioral ground truth. **This is a single sample: I read it for the *kind* of gaps it
exposes, not as evidence that all calls look like this.** Anonymized, timestamped:

| Moment | What happened | Why it's a coachable signal |
|--------|---------------|-----------------------------|
| Open [00:37] | *"Any questions from our first conversation?" → "I don't have any."* then straight to screen-share | **Zero fresh discovery.** No re-confirm of goals, criteria, timeline, or decision process |
| Talk time (whole call) | Rep speaks ~85–90% of the call; prospect utterances are mostly "okay / right / correct" | **Severe talk/listen imbalance** — monologue, not dialogue |
| ROI build [32:06–35:48] | Rep repeatedly self-labels "being *very conservative*," builds to a "$623,000 back to you" number | Numbers *presented at*, not *discovered with*, the prospect |
| The close question [36:18] | *"Would you agree I'm being conservative?" → "Yes, because I have nothing to disagree."* | **Compliance, not conviction.** A leading question manufacturing false agreement — the rep doesn't catch it |
| Buying signal [46:54] | Prospect volunteers: *"I have been trying to sell the business for a bit."* | **The single most important fact in the call — surfaced by accident, at minute 47.** Real discovery finds this in minute 5 |
| Signal handling [47:26–49:06] | Rep reframes ("systems and processes raise your multiple") but never qualifies: timeline? does a buyer inherit the contract? should we even proceed now? | Missed the obvious qualifying questions the signal demanded |
| Close [49:17–49:46] | *"We have a board meeting at the end of this month… valid until the end of the month."* | **Manufactured urgency** layered on a prospect who just said he's exiting |
| Next step [46:36], [49:46] | *"I'll send you an email with the five things… check in next week."* | **No firm next meeting booked** — a diffuse, low-commitment close |
| Product coverage | Rep correctly walked the full agent suite — Sally, Olly, the Concierge, Solo Care | **On-brand — so this is *not* a product-knowledge gap.** It isolates the defect to *discovery* and *proof*, not knowledge |

**What this one call demonstrates** (and what I would *not* over-claim): it shows the **kind** of
coachable gaps that exist and go completely uncaught, and that the raw signal to catch them lives
in the transcript. It does **not** prove every call looks like this — I'd confirm the actual
spread by sampling (Step 2). The load-bearing point is subtler and doesn't depend on the spread:
**today nothing scores any call, so no one — not the rep, not the manager — knows how common
these gaps are.** That measurement vacuum is the problem, and it's exactly what an AI system can
fill cheaply, at scale, from day one.

### The tell: in this call, the rep broke Sensi's *own* playbook

What elevates this from "one rough call" to a *diagnosis worth investigating* is that the call
departs from Sensi's **own** documented motion and proof standards — a mismatch a scoring loop
would catch automatically and today catches never.

**1. Motion inverted.** Sensi's deck prescribes the agenda: *Intro → **Getting to Know You & Your
Business** (discovery) → Product → **Customer Story & Value** → Q&A.* In this call the rep opened
with *"I'm going to share my screen for most of this call,"* asked only *"any questions from our
first conversation?"*, then ran a product tour + a self-built ROI calculator — **discovery-first
became product-dump-first.**

**2. Invented numbers instead of Sensi's published proof.** Sensi publishes an attributable proof
wall — **35% more billable hours, 2.6× inquiry→assessment conversion, 23% readmission drop, 300%
retention, 80%+ hospitalization reduction**, plus the Diana story (**0%→100%** satisfaction, 14
months with no falls). The rep used **none** of it, and instead improvised:

| Rep said (this call) | What Sensi actually publishes | Verdict |
|----------------------|-------------------------------|---------|
| "$623K, unbelievably conservative" | ~$500K avg savings; no total-$ ROI figure | **Invented — and it overshoots Sensi's own ceiling** |
| "3.3 months longer LoS, 1,000-agency survey" | "2× length of stay"; no such survey exists | **Fabricated provenance** |
| "Sally = 3–4× a salesperson" | "your entire inside sales force in one agent" | **Unsupported multiplier** |
| "90-plus / 80–83% adoption" | no adoption figure is published | **Unsupported** |

**Why this matters (carefully):** I'm not claiming every rep does this. I'm claiming something
more defensible — **Sensi already has a winning motion and a proof library, and nothing measures
whether any given call uses them.** This one call shows the gap is *possible and invisible*; the
fix is the loop that would make it *visible and measured*. It also hands the future rubric its
two highest-value, evidence-backed dimensions: **motion adherence** (discovery before pitch) and
**proof-point fidelity** (Sensi-sourced numbers, not invented ones).

### Who the rep is selling to (and why it's genuinely hard)

The buyer is a **home-care agency owner/operator** (the deck's customer quotes are exactly these
titles). Sensi frames their pain as **operational and financial fragility** — a *77% rise in
caregiver turnover*, *89% of providers rejecting new business for lack of caregivers*, and
margins that live or die on the **billable hour** and **length of stay**. That shapes the rubric:
a strong Sensi call ties value to *those* levers. *(I checked deliberately: Sensi's materials do
**not** frame the difficulty as HIPAA / Medicare / regulatory — Medicaid appears only as a
prospect's question in the call. So I'm not leaning on a regulatory angle; that would be my
inference, not Sensi's positioning.)*

## Step 2 — What I'd go find beyond the brief

One call is a hypothesis generator, not proof. Before building, I'd run a fast, sequenced
discovery. **Order matters** — I go from "what does good look like and what's been tried"
(so I don't rebuild a dead end) outward to the front line, then to the data.

| Order | Who | Why them first | Questions I'd ask |
|-------|-----|----------------|-------------------|
| 1 | Daniel U. & Daniel R. (Ops leadership) | Align on the definition of "getting better" and what's already been tried | How do you know a rep is improving today? What have you tried that didn't stick, and why? |
| 2 | VP Sales / CRO | Owns the sales process the rubric must reflect | What does a great call look like by stage? Where do deals actually stall? **How many reps, teams, and calls a week — and where's the growth?** (sizes the loop) |
| 3 | 3 reps: 1 top, 1 ramping, 1 struggling | Ground truth on the daily workflow; top-vs-bottom delta is the coaching target | Walk me through a recent won *and* lost call — where did each turn? How do you prep, and what do you do after? What would you *actually* use? |
| 4 | 1–2 front-line managers | They're the overloaded constraint; coaching adoption lives or dies with them | What are your priorities? What are your biggest challenges? How do you coach today? *(open, not leading — let them name the constraint)* |
| 5 | RevOps / HubSpot owner | Owns the data + the integration surface | What's captured in **HubSpot** automatically vs. manually? Does Jiminny already sync to HubSpot? **What's our weekly call volume, and what % is recorded?** What activity/stage data can the loop read *and* write back? |
| 6 | Enablement / onboarding lead | Ramp is the compounding symptom | What's the ramp curriculum? What's documentation vs. shadowing vs. measured? |
| 7 | Product Marketing | Source of the persona/product-knowledge inconsistency | How do new features reach reps today? What's the lag between release and rep fluency? |

**External data I'd pull (and where it lives):**
- **Win/loss by rep and by stage** (CRM) — is the problem discovery, demo, or close?
- **Ramp cohorts** — time-to-first-deal / time-to-quota by hire cohort (CRM + HR/onboarding).
- **Existing call-tool analytics** (Jiminny) — are talk-ratios / trackers *already* available
  and simply unused? This directly changes build-vs-buy (see `make_vs_buy.md`).
- **Call coverage** — how many calls/week are actually recorded? (No recordings → no loop.)
- **Org sizing** — # teams · reps · calls/week and the growth trajectory (HubSpot · Jiminny ·
  sales ops) — sizes the loop and drives the scaling/architecture questions in Phase 3.
- **Stage-conversion rates** (CRM) — where in the funnel deals leak, to focus the rubric.
- **New-rep onboarding survey / CSAT** — qualitative ramp friction.

**How I'd turn all this into a picture — the synthesis method (not just collection):**
- **Sample, don't anecdote.** I would **not** assume the one call is representative. I'd score
  **15–20 recent calls across the three rep tiers** with an ad-hoc LLM evaluation to learn the
  *actual* distribution of gaps, then **review the findings with reps and sales managers** — to see
  how *common* each gap is and validate the rubric with the people who live it. That's how a single
  call becomes a diagnosis I'd bet on.
- **Top-vs-bottom delta.** Compare top performers' calls to strugglers' on the same rubric
  dimensions; the gap between them *is* the coaching curriculum.
- **Motion-adherence + proof-fidelity coding.** Score each sampled call against Sensi's own deck
  agenda and proof wall (Step 1 shows both are concretely measurable).
- **Triangulate quant.** Talk/listen ratio and discovery-question counts (deterministic) × win/
  loss by stage × ramp cohorts → *where in the funnel* the behavior actually costs deals, so the
  rubric weights what matters.

## Step 3 — The funnel: six symptoms → one root cause → one leverage point

```
Fragmented stack ─┐
No QA process ─────┤
Managers overloaded┤──▶  ROOT CAUSE: no closed loop turns each call
Reps lack AI ──────┤        into tracked, improving rep behavior
Knowledge gaps ────┤        (a measurement vacuum)
Long ramp ─────────┘
                              │
                              ▼
        LEVERAGE POINT: install the loop at the cheapest entry —
        automated post-call evaluation + coaching
```

## Step 4 — The bet (the hypothesis I'd take into Phase 2)

> **Biggest leverage point:** an **automated post-call evaluation + coaching loop** — every
> call is scored against a Sensi-specific rubric, the rep gets specific feedback + a next
> action, the manager gets a triaged coaching queue, and every score is tracked over time.

**Why I believe it:**
1. **The gap is real, and today it's invisible.** This call shows the *kind* of coachable gap
   that exists, and the deck cross-check shows it's a departure from Sensi's *own* motion and
   proof standards. Whether that's one rep or many, *nothing measures it* — so the loop is what
   turns an unknown into a managed number (Step 1). (I'm betting on the measurement vacuum, not
   on a claim that all calls are weak.)
2. **It's the cheapest place to install measurement** — there is no baseline today; this
   *creates* the baseline from call one, which unlocks every other fix.
3. **It attacks the binding constraint** — manager capacity. Triaged, pre-analyzed calls turn
   coaching from an hour of review into a five-minute intervention.
4. **It compounds** — the same loop (rubric + evaluate + route + track) later templates onto
   onboarding, persona/product gaps, and other teams (Phase 3). The other five pains become
   *measurable* once the loop exists.
5. **One person can build it with AI** — which is precisely the bet this role is testing.

**What I'd build to test it:** a working "Rep Coach" scorecard (Phase 2) that ingests a
transcript, scores it (deterministic metrics + LLM judgment with evidence quotes), and produces
the rep view, the manager queue, and a trend dashboard — with the measurement layer built in.

**How I'd know I'm wrong (falsification — I'd rather find this in week 2 than month 6):**
- Reps don't open it, or open it once and never return → the feedback isn't actionable enough.
- Scores don't move behavior on flagged dimensions within ~3–4 weeks → the rubric measures the
  wrong things, or coaching isn't closing the loop.
- Managers don't trust the scores enough to act → evidence/explainability is too thin.
Each has a leading metric in the Phase 2 tool, so the hypothesis is testable, not just asserted.

## Step 5 — Why this leverage point (not the others): the coverage overlap

A single-pain fix wouldn't earn the bet. This one does because **the six pains overlap**, and
the artifacts the loop produces each serve several at once. Read the pains not as six separate
problems but as three moves seen from different roles:

- **QA (2), manager overload (3), rep support (4)** are the *same evaluation event* viewed by
  three people — one scored call feeds all three. Solve one, solve three.
- **Knowledge inconsistency (5) and long ramp (6)** are the *same rubric* applied to learning —
  "what good looks like," measured, with targeted content to close the gap.
- **Stack fragmentation (1)** is the connective tissue the loop *is* — it threads call
  performance → coaching → content → outcome across Jiminny, HubSpot, Slack, and the KB.

| Pain point | Proposed solution | Loop artifact that delivers it | Coverage |
|------------|-------------------|--------------------------------|----------|
| **2 · QA not happening** | Automated evaluation of every call against a consistent rubric | Rubric + per-call scorecard | ● Directly solves |
| **3 · Managers overloaded** | Pre-analyzed calls, triaged coaching queue, auto-escalation on extreme gaps | Manager rollup + escalation flags | ● Directly solves |
| **4 · Reps lack AI support** | Personal scorecard, top-2 focus areas, recommended micro-content before the next call | Rep view + recommendations | ● Directly solves |
| **1 · Fragmented stack** | Consolidate onto **HubSpot as the single surface** (score on the call record, follow-ups as tasks, dashboards) so reps/managers stop jumping tools; the loop is the connective layer feeding it | The loop (integration spine) → **HubSpot in production** | ◐ Unifies → ● in production |
| **5 · Inconsistent knowledge** | Product-claim-accuracy scoring exposes per-rep *and* systemic gaps; routes targeted content | Gap analytics + recommendations | ◐ Measures & routes |
| **6 · Long onboarding ramp** | Objective ramp curve, the rubric as the onboarding standard, targeted practice | Tracked scores over time + rubric-as-standard | ◐ Accelerates |

`●` = the core loop solves it directly · `◐` = the loop supplies the measurement/spine, paired
with a buy (KB, BI) or an integration.

**The through-line:** every `●` and `◐` above is powered by the *same two artifacts* — the
**rubric** and the **evaluation data**. Build them once (for pains 2/3/4) and pains 1/5/6 come
along for the ride. That is the definition of a leverage point: not the biggest single pain, but
the **smallest build that moves the most pains** — and the same overlap is what lets it scale
across teams in Phase 3 (one engine → many rubrics).

## Scope decisions made explicit
- **Human reps, not the Sally AI agent.** Sensi *sells* an AI sales agent (Sally), so "seller
  enablement" is genuinely ambiguous. The stated pains ("our sellers are not getting better")
  and the one real artifact are about **humans**. I'm targeting humans; a Sally-tuning loop is
  a valid future instance of the *same* pattern, noted in Phase 3.
- **HubSpot is the CRM (confirmed).** Verified through prior interviews — the production
  integration target is **HubSpot** (including HubSpot Workflows for routing tasks). I still
  **mock CRM/Slack in the prototype** (no live access, and to keep scope tight), but the
  production design assumes HubSpot specifically, not a generic CRM.
