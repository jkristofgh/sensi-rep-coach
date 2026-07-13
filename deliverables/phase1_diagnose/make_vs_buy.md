# Make vs. Buy — Seller Enablement Stack

Janos Kristof · companion to Phase 1 diagnosis

> **Why this document exists.** The sharpest challenge to anything I build is: *"Jiminny and
> Gong already do call coaching — why build?"* A credible enablement lead answers that **before**
> writing a line of code. This is the reusable decision framework I'd apply to every component,
> the named options I'd evaluate, and where I'd land — with the reasoning visible, not just the
> verdict. **Every verdict below is provisional by design** — it is the *pre-discovery lean*,
> not a decision. Consistent with "diagnose before you build," the framework re-decides once
> Step-2 interviews confirm what's already licensed and enabled (finalized in the
> production-readiness session).

## The decision framework (applied to every component)

For each capability I score seven criteria, weighted for a **one-person ops function** at a
Series-C, HIPAA-adjacent company:

1. **Already solved?** — does a tool in the stack (or a cheap one) already do this well?
2. **Lock-in / switching cost** — how trapped are we if it's wrong?
3. **Customization** — can it be tuned to Sensi's persona, products, and rubric?
4. **Data residency / NDA / HIPAA fit** — can confidential call data flow through it safely?
5. **Time-to-value** — days, or a quarter?
6. **Total cost** — license + integration + the maintenance tail.
7. **Maintenance load** — can *one person* keep it running "long after they've moved on"?

**Guiding principle:** *Buy the commodity, build the differentiator, integrate the rest.*
Conversation capture is a commodity. The Sensi-specific enablement *loop* is the differentiator.

## The stack, component by component

| Component | Decision | Named candidates considered | Why |
|-----------|----------|-----------------------------|-----|
| **Call capture / transcription / conversation intelligence** | **BUY** | **Jiminny (already in stack)**, Gong, Chorus (ZoomInfo), Avoma, Clari Copilot, Salesloft Conversations, Outreach Kaia | Recording, transcription, and generic CI are commodities. Rebuilding them burns the whole time budget for no differentiation. Use what captures the call; stay tool-agnostic (transcript in). |
| **Scoring / coaching-loop engine** | **BUILD** | (this is the Phase 2 prototype) | The differentiator. Off-the-shelf CI gives *generic* scorecards; none delivers a **Sensi-tuned rubric + tracked feedback → outcome linkage + a cross-team templating pattern** as one closed, compounding loop. This is where a person with AI beats a platform. |
| **Orchestration / workflow** | **DECIDED — core in code + lightest orchestration** | No-new-tool (HubSpot Workflows + Jiminny triggers + a small service), n8n, Zapier, Make, Temporal/Windmill/Prefect, custom Python | **Decided in `production_readiness.md` §2:** keep the scoring core in code (testable, prompt-versioned, golden-check); use the lightest orchestration that clears NDA/data-residency — **test HubSpot Workflows / Operations Hub first** (no new vendor; **HubSpot is the confirmed CRM**). Self-hosted **n8n is the complexity-driven fallback**, not the default — and the adapter seam makes adopting it a *glue change, not a rewrite*. Anti-pattern rejected: re-implementing scoring in workflow nodes. |
| **Sales training / onboarding / enablement** | **BUY / config** | Highspot, Seismic, Mindtickle, Spekit; AI-roleplay: Second Nature, Hyperbound | Mature category; buying beats building. Our loop *feeds* these (what to train becomes data-driven), it doesn't replace them. |
| **Knowledge base + call scripts/playbook** (the loop's *grounding artifacts*) | **BUY / config** | Guru, Notion, Confluence + AI search (Glean, Dashworks); scripts/playbook live in the KB or HubSpot | Content management is solved. These artifacts *feed the engine*: the **product KB** grounds product-claim-accuracy scoring and supplies the rep's recommended micro-content; **Sensi's call scripts/playbook** ground motion-adherence scoring ("discovery before pitch") and supply "what to do next time." The value-add is keeping them current and wired into the loop — integrations, not a new KB. |
| **Dashboards / BI** | **light-BUILD now → BUY later** | Streamlit (prototype), then Metabase, Looker, HubSpot native reporting, Sigma | Streamlit is right for a fast, running demo. At scale, move the dashboard layer to a real BI tool — most likely **HubSpot native reporting**, so managers stay in one surface (see next row). |
| **Rep/manager surface (system of action)** | **BUY / consolidate → HubSpot** | **HubSpot** (UI Extensions / CRM cards, custom objects, Workflows / Operations Hub, native dashboards); alternatives: standalone app, embed | The multi-tool jump (**pain #1**) is best fixed by *not adding a surface*. Put the **scorecard on the call record**, **follow-ups as tasks** (prospect next-steps *and* rep-coaching to-dos), and **trends as dashboards** — all inside the CRM reps/managers already live in; Slack becomes a nudge that deep-links back. Streamlit is the **prototype surface only**. Capability is tier-dependent (Enterprise / developer projects) — confirm in discovery. |
| **LLM layer** (NDA/HIPAA-critical) | **BUY with the right terms** | **Anthropic Claude (zero-retention + BAA)**, Azure OpenAI, AWS Bedrock (BAA, in-VPC / data residency) | Never build a model. The *only* thing that matters here is contractual: zero-retention / BAA / data-residency, because call data is confidential and HIPAA-adjacent. |

## The headline answer: "Jiminny/Gong already coach — why build?"

**Because I'm not rebuilding conversation intelligence — I'm building the loop around it.**
Off-the-shelf CI tools are excellent at *capture and generic analysis* and weak at exactly the
three things this problem needs:

1. **A Sensi-specific rubric** — tuned to *this* persona (home-care agency owners) and *these*
   failure modes (the ones the real call exposed: monologue, leading closes, missed buying
   signals, weak next steps), not a generic "talk-ratio" widget.
2. **A closed feedback→outcome loop** — score → rep action → manager triage → *tracked change
   over time*, linked to deal outcomes. Generic CI shows you a call; it doesn't run the loop.
3. **A cross-team templating pattern** — the same engine re-pointed at CS or onboarding by
   swapping a rubric file (Phase 3). No CI product templates enablement across functions in a day.

And it's **CI-tool-agnostic by design**: the prototype takes a transcript in and emits the loop
out, so whatever Sensi captures calls with (Jiminny today) plugs in without rework. That also
*de-risks* the buy decision — we're not betting the enablement layer on one vendor.

> **What discovery would change here:** if Step-2 interviews reveal Jiminny's coaching/scorecard
> features are licensed *and* would meet the rubric need, the honest move is to configure Jiminny
> first and build only the loop/tracking gap on top. The framework — not ego — decides.
