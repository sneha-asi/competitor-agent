# Plan & Roadmap

The product vision, the principles it's built on, and where it's headed. Design internals live in
[ARCHITECTURE.md](ARCHITECTURE.md); this is the "what and why."

---

## Vision

One input — a product — becomes a **sourced, board-ready competitive briefing** against its top
market rivals, with zero manual research. The bar is *exhaustive and defensible*: a document a
founder or PM can put in front of a board or a sales team and stand behind line by line.

## Principles

1. **No fabricated data.** Every competitor claim traces to a real source; the unverifiable is
   marked `unknown`, never guessed. Enforced in code (cite-or-void) and by an adversarial gate.
2. **Self-critical, not marketing.** Real gaps and open questions are the point. Our own `ahead`
   only counts where no rival matches us.
3. **Our side is never invented.** Capabilities come only from the user's materials.
4. **Human in the loop at the expensive turns.** Confirm the product understanding; approve the
   top 2 rivals — before any deep research spends tokens.
5. **Deterministic where it should be.** Research and judgment are model-driven; the final render
   is a deterministic template, so the artifact is consistent every time.

## How a run goes

```
A · Intake ──▶ [confirm product] ──▶ B · Discovery ──▶ [approve top 2]
   ──▶ C · Deep research ──▶ D · Synthesis ──▶ E · Verify (gate) ──▶ F · Render
```

Two surfaces, same fleet and same renderer: the **`/competitor` Claude Code skill** (zero setup,
session model) and the **standalone web app** (self-serve, Anthropic API). See
[README.md](README.md) for both.

## Decisions (locked)

| Decision | Choice |
|----------|--------|
| Analysis depth | Exhaustive — full matrix, all sections, every claim sourced |
| "Biggest" rivals | Ranked by **market leadership** |
| Human gate | Confirm the top 2 before deep research |
| Competitor count | 2 (default) |
| Orchestration | Fan-out per phase → converge, gated by adversarial verification |

---

## Status

**Shipped**
- ✅ Deterministic renderer + extracted design system, verified visually end-to-end.
- ✅ The 9-agent fleet — individual definitions, installable as live subagents.
- ✅ Orchestrator (Phases A–E), schema-validated, with cite-or-void and home-team-bias guards.
- ✅ Research-grounded methodology baked into the agent prompts.
- ✅ Standalone web app — FastAPI backend (compiles) + React/Vite frontend (builds); render path verified.
- ✅ Docs: README, this plan, architecture, content spec, design tokens, worked example, sample report.

**Pending**
- ⏳ First live end-to-end run — needs an `ANTHROPIC_API_KEY` in `app/.env`. This is also the first
  true integration test of the agent prompts against the real API + web search.

## Roadmap

**Next**
- Live run on a real product; tune prompts, effort levels, and skeptic counts against real output.
- Caching of research per competitor so re-runs are cheap and incremental.
- Configurable competitor count (2 → N) and a "closest head-to-head" ranking mode.

**Later**
- Persist runs (history + diff): watch a market over time, surface what changed.
- One-click deploy for the web app (containerized backend + static frontend).
- Export formats beyond HTML (PDF, slide deck) reusing the same `data.json`.
- Scheduled re-runs that alert on meaningful competitor changes.
