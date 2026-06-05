# Competitor Agent — Plan

A reusable agent (`/competitor`) that turns **one product** into a polished, sourced
competitive-analysis page. You give it the product; a team of subagents finds the rivals, researches
them, fact-checks each other, and builds the briefing.

Multi-agent design: **[ARCHITECTURE.md](ARCHITECTURE.md)**. Page design/renderer: built & verified.

---

## Goal
From just a product (repo / website / doc / a few sentences), produce one self-contained HTML page —
"where we lead, where we lag, what to build next" — versus the **top 2 market-leading competitors**,
at an **exhaustive** depth, with **every competitor claim sourced and adversarially verified**.

## Locked decisions
Depth → **Exhaustive** · "Biggest" → **Market leaders** · **Confirm picks first** · **2 competitors**
· orchestration → **multiple subagents per step that converge**, gated by an adversarial fact-check.

## Non-negotiable rules
- No fabricated competitor data — unverifiable → `unknown`. Enforced by the Phase E verification gate.
- Self-critical, not marketing — real gaps + open questions, not a win-every-row matrix.
- Our side is never invented — only from your materials.

---

## How a run goes (two invocations, you in the middle)

**Invocation 1 — Intake → Discovery**
1. **Phase A · Intake** — parallel readers ingest the product → I play back *"here's what your
   product is."*  → **you confirm/correct.**
2. **Phase B · Discovery** — 4 blind searchers sweep the market → ranked by market leadership → I
   return the **top 2 (+ runners-up) with rationale.**

⟢ *You approve or swap the 2 rivals.* ⟢

**Invocation 2 — Research → Build**
3. **Phase C · Deep research** — 5 dimension agents × 2 rivals, every fact with a source.
4. **Phase D · Synthesis** — 5 builders draft the matrix, moats, gaps, decisions, positioning → one editor merges into `data.json`.
5. **Phase E · Verify (the gate)** — 2–3 skeptics try to refute each risky claim against its source; failures → `unknown`. Produces a verification report.
6. **Phase F · Render** — `build_page.py` → screenshot-verify → deliver the `.html`.

---

## What's left to build (implementation)
1. **Write the orchestration script** `scripts/competitor_workflow.js` implementing Phases A–F with
   `phase()` / `parallel()` / `pipeline()` and schema-validated agent outputs (per ARCHITECTURE.md).
   - Split at Gate 2: script returns after Phase B; a second entry runs C–F on approval.
2. **Define the JSON schemas** for each artifact (product_profile, candidates, competitor_profile,
   data.json, verdicts) so agents return structured data, not prose.
3. **Wire it into SKILL.md** — when a product arrives, run invocation 1; on approval, invocation 2.
4. **Add budget caps** — skeptic count + research depth scale to the token target; Phase E capped.
5. **Dry-run** on a real product, tune, done.

> Orchestration spawns many subagents and costs real tokens — I'll confirm before launching each
> invocation.

## Status
- ✅ Renderer + design system + example page (verified end-to-end).
- ✅ Single-pass workflow encoded as the skill's defaults.
- ✅ Multi-agent architecture designed → [ARCHITECTURE.md](ARCHITECTURE.md).
- ⏳ **Next:** build the orchestration script (steps above), then you share the product and we run it.
