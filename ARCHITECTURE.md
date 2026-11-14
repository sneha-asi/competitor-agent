# Competitor Agent — Multi-Agent Architecture

**Thesis:** run each pipeline step as a *fan-out of specialist subagents that converge*, and gate the
whole thing on an **adversarial verification** pass so no competitor claim survives unless a skeptic
failed to disprove it. Parallelism buys speed and breadth; the verification gate buys trust.

---

## Design principles
1. **Phases in sequence, fan-out inside each.** Steps depend on each other (can't research rivals
   before we know them), so we don't parallelize the *pipeline* — we parallelize *within* each phase
   and converge before moving on.
2. **Independent perspectives beat one context.** Discovery and research split into agents that are
   blind to each other, so we get coverage and catch each other's misses.
3. **Adversarial verification is the core, not a footnote.** The failure mode that matters is a
   fabricated/half-true competitor claim. Every sourced claim must survive skeptics before it ships.
4. **Humans gate the expensive turns.** Confirm the product understanding, and confirm the 2 rivals,
   *before* spending tokens on deep research.
5. **Determinism at the end.** Synthesis produces `data.json`; the page render is the existing
   deterministic script — no model creativity in the final artifact.

---

## Topology

```
            ┌─────────────────────────────────────────────────────────────┐
 INPUT ───► │ PHASE A · INTAKE        readers ─┐                           │
 (repo/url/ │   A1 readme/docs        A2 src   ├─► S-A synth ─► product_profile.json
  doc/text) │   A3 pricing/site/changelog ─────┘                           │
            └───────────────────────────────────────────────┬─────────────┘
                                       ⟦ HUMAN GATE 1: confirm "what our product is" ⟧
            ┌───────────────────────────────────────────────▼─────────────┐
            │ PHASE B · DISCOVERY (multi-modal sweep, blind)                │
            │   B1 "alternatives/vs"  B2 G2/Capterra/analyst                │
            │   B3 funding & news     B4 community/forums                   │
            │            └────────────┴─► R-B rank by MARKET LEADERSHIP ─► candidates.json
            └───────────────────────────────────────────────┬─────────────┘
                              ⟦ HUMAN GATE 2: approve / swap the TOP 2 rivals ⟧
            ┌───────────────────────────────────────────────▼─────────────┐
            │ PHASE C · DEEP RESEARCH   (per competitor × per dimension)    │
            │   for each of 2 rivals:  pricing │ features/docs │ positioning│
            │                          momentum/news │ reviews/gaps         │
            │            └─► S-C(i) per-rival synth ─► competitor_profile[i].json
            └───────────────────────────────────────────────┬─────────────┘
            ┌───────────────────────────────────────────────▼─────────────┐
            │ PHASE D · SYNTHESIS (fan-out by artifact → merge)            │
            │   D-matrix │ D-moats │ D-gaps │ D-decisions │ D-positioning   │
            │            └─► S-D editor merges ─► draft data.json           │
            └───────────────────────────────────────────────┬─────────────┘
            ┌───────────────────────────────────────────────▼─────────────┐
            │ PHASE E · ADVERSARIAL VERIFICATION  ← the gate                │
            │   per claim: 2–3 skeptics try to REFUTE vs its source         │
            │   majority-refuted / source missing → downgrade to `unknown`  │
            │            └─► validated data.json + verification_report.md    │
            └───────────────────────────────────────────────┬─────────────┘
            ┌───────────────────────────────────────────────▼─────────────┐
            │ PHASE F · RENDER & SELF-CHECK (deterministic, single thread)  │
            │   build_page.py → screenshot/verify → deliver .html           │
            └───────────────────────────────────────────────────────────────┘
```
"Come together at the end" happens twice: **S-D** merges all parallel analysis into one draft, and
**Phase E** is the gate every claim must pass before it reaches the page.

---

## Agent roster

| Phase | Fan-out agents | Converge to | Output artifact |
|-------|----------------|-------------|-----------------|
| A · Intake | 2–3 readers, by input type (docs / source / pricing-site) | `S-A` synthesizer | `product_profile.json` (capabilities, category, ICP, search seeds) |
| B · Discovery | 4 blind searchers (alternatives, analyst dirs, funding/news, community) | `R-B` ranker | `candidates.json` (ranked, with evidence) |
| C · Research | 5 dimension agents **× 2 rivals** = ~10 | `S-C(i)` per rival | `competitor_profile[1..2].json` (sourced facts) |
| D · Synthesis | 5 artifact builders (matrix, moats, gaps, decisions, positioning) | `S-D` editor | draft `data.json` |
| E · Verify | 2–3 skeptics **per risky claim** | vote → corrector | validated `data.json` + `verification_report.md` |
| F · Render | — (deterministic) | — | `<product>-comparison.html` |

Concurrency is capped (~10–16 live agents); excess queues. Total agent count scales with #claims in
Phase E, so E only verifies the *risky* claims (competitor `owned`/`ahead`/`gap` cells and any
quantified stat), not our own side or `unknown`s.

---

## Data contracts (what flows between phases)
- `product_profile.json` → `{ name, category, icp, capabilities[], positioning, search_seeds[] }`
- `candidates.json` → `[{ name, why, leadership_signals[], sources[] }]` (ranked)
- `competitor_profile[i].json` → `{ name, pricing, features[], positioning, momentum, gaps[], sources{claim:url} }`
- draft/validated `data.json` → the schema in [references/content-spec.md](references/content-spec.md)
- `verification_report.md` → what was downgraded and why; source-coverage stats

Each phase reads only the prior artifacts, so phases are independently re-runnable.

---

## The verification gate (Phase E) — detail
For every risky claim in the draft:
1. Hand 2–3 **independent** skeptics the claim **and its cited source URL**.
2. Prompt them to **refute** — "does this source actually support this? Default to *unsupported* if
   unclear." Give each a slightly different lens (literal-source-check, recency, scope/edge-cases).
3. **Majority refute or source missing → downgrade the verdict to `unknown`** and log it.
4. Survivors keep their verdict and source.

This is why the page can be both exhaustive and honest: breadth comes from fan-out, trust comes from
the gate. A claim that no skeptic could disprove against a real URL is one you can defend in a room.

---

## Human gates
- **Gate 1 (after A):** I play back "here's what your product is" — you correct before any research.
- **Gate 2 (after B):** I show the top 2 (+ runners-up) with rationale — you approve or swap.
- (Optional Gate 3 after E: skim the validated matrix before render.)

Because the orchestrator runs to completion in the background, the gates split the run into **two
workflow invocations**: **(1) Intake → Discovery → returns candidates**; you confirm; **(2)
Research → Synthesis → Verify → Render**. I stay in the loop between them.

---

## How it maps to the orchestration tool
- Phases → `phase()`. Fan-out → `parallel()` / `pipeline()`. Each agent returns a **schema-validated**
  object so there's nothing to parse.
- Phase C is a `pipeline()` over the 2 rivals (each rival flows research → per-rival synth without a
  global barrier). Phase E is `parallel()` skeptics per claim, then a majority vote in plain code.
- **Budget-aware:** scale skeptic count and research depth to the token target; cap Phase E so a
  claim-heavy matrix can't run away.
- Workflows cost real tokens and spawn many agents, so **I confirm with you before launching** each
  invocation.
