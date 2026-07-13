# Decision Log — How This Diagnosis Was Made

Janos Kristof · the "how I think" companion to the deliverables

> **Why I'm showing you this.** The assignment rewards people who are "relentlessly curious
> about the real problem, not the stated one" and who "think in systems that compound." Those
> are *process* traits — invisible in a polished final answer. So this log exposes the working:
> where I started, where I pushed back on myself, what I deliberately cut, and why. A clean
> conclusion can be a lucky guess; a documented path is a repeatable skill.

## The starting point (my first-draft instinct)

My initial plan was broad — I mapped all six stated pains and proposed a workstream for each:
call QA, a product knowledge base, a persona knowledge base, onboarding automation, and a
release-to-docs content pipeline. It was comprehensive. It was also **wrong for this
assignment**, for reasons I only saw when I re-read the brief as a rubric.

## The five course-corrections

**1. Comprehensive → sharp.**
The brief says *"we expect sharpness. Pick your battles"* and asks for *one* hypothesis and
*one* tool. A plan that keeps six workstreams alive fails that test on contact. I forced the
funnel: six pains are **symptoms of one root cause** (no closed loop that turns calls into
tracked, improving behavior). Committing to one leverage point isn't narrowing the scope — it's
finding the point that makes the others move.

**2. Conclusion → process.**
My first draft led with the answer ("build a call scorecard"). But Phase 1 is graded on the
*discovery process*, not the conclusion. I rebuilt it to show the path: interrogate the brief →
mine the one real artifact → sequence who I'd interview and what data I'd pull → *then* the bet.
Same destination; now the map is the deliverable.

**3. Stated problem → real problem.**
The brief's six bullets are the *stated* problem. I treated them as symptoms and went looking for
the real one — starting with the single piece of behavioral ground truth we were given, the sales
call. That's where the thesis got its *first* evidence: this one call shows the **kind** of
coachable signal that today goes uncaptured and unscored — and nothing in the stack measures
whether it happens on any other call. The call didn't prove a team-wide pattern; it revealed a
**measurement vacuum** worth betting on (which I'd then size by sampling, per the diagnosis).

**4. "Measurement later" → measurement is the point.**
The brief is blunt: *"If you can't measure it, it didn't work."* My first draft treated metrics
as a reporting afterthought. I inverted it: the reason call-coaching is the leverage point is
precisely that it's the cheapest place to **install measurement where there's a vacuum** — it
*creates* the baseline. Measurement moved from feature to thesis.

**5. Content-reuse → a pattern that compounds.**
My draft Phase 3 said "the product KB also feeds marketing, website, CS." That's content
*reuse* — not what "systems that compound" means. I reframed it to the underlying **repeatable
architecture** (the enablement loop) that re-templates to any team by swapping a rubric, and
made "reusable in under a day" a literal, demonstrable test.

## Corrections from the validation gate (the process caught me)

Before finalizing, I ran the deliverables through an independent validation against the
assignment (coverage + completeness). It returned **REVISE** — and it was right on two things I'd
have shipped otherwise:

**6. I'd leaned on one source; the assignment says use them all.** My first pass mined the brief
+ the one call and skated past the GTM deck, Guide Book, and customer materials — while *claiming*
to be relentlessly curious. So I went back and mined them, which surfaced the strongest evidence
in the whole diagnosis: the recorded call **inverts Sensi's own prescribed motion** (discovery →
product → value) and **substitutes invented numbers** for Sensi's published proof wall. The
diagnosis is far more defensible for using Sensi's own words as the benchmark.

**7. I was over-claiming from a sample of one.** My draft implied that *every* call looks like the
one we were given ("the signal exists on every call… consistent enough to score"). That's not a
fair inference from n=1, and I corrected it everywhere: the call is a **revealing sample, not a
verdict** on the whole team. The bet doesn't need every call to be weak — it rests on the fact
that **nothing measures calls at all**, so no one can even say how common the gaps are. I also
added an explicit sampling plan (15–20 calls) as the honest way to learn the real distribution
before betting.

**Course-correction I avoided:** I nearly framed the persona's difficulty as HIPAA/Medicare
friction — then checked, and found Sensi's materials frame it as *operational* fragility
(turnover, caregiver shortage, billable-hour economics), not regulatory. I dropped the regulatory
angle rather than assert a plausible-but-unsupported claim.

## Two decisions I made deliberately (and could defend either way)

- **Human reps, not the Sally AI agent.** Sensi sells an AI *seller* (Sally), so "seller
  enablement" is honestly ambiguous. I chose humans because the stated pains and the one real
  artifact are about humans — but I flagged Sally-tuning as a valid future instance of the same
  pattern rather than pretending the ambiguity doesn't exist.
- **Added a make-vs-buy discipline.** The strongest objection to building anything is "Jiminny/
  Gong already do this." Rather than dodge it, I made it a first-class deliverable with a
  reusable framework and named candidates — and a stated willingness to *not build* if discovery
  shows the buy option already fits. Judgment about ownership is the competency; the verdict is
  secondary.

## What I deliberately did NOT do
- Didn't *assume* the CRM — I held it as unconfirmed until I could verify it rather than take a
  working note as fact. Now **confirmed as HubSpot** (via prior interviews), so the production
  design targets HubSpot specifically (Workflows a real routing option); the prototype still
  mocks CRM/Slack for scope. The discipline was verify-then-assert, not the guess itself.
- Didn't build a broad multi-feature platform — one running, measurable tool beats five
  half-built ones, and the time box is itself a judgment test.
- Didn't decide the production orchestration (Python vs. n8n vs. no-new-tool) inside the build —
  that's a real decision deserving its own session, not a snap call.

## The through-line
Every correction above came from reading the brief's *language* as grading criteria and letting
the one real artifact — not my assumptions — carry the evidence. That's the operating pattern
I'd bring to the role: interrogate the stated problem, find the real one in the data, commit to
the leverage point, and build the measurement in from line one.
