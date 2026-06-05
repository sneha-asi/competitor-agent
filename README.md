# competitor

A reusable agent that turns **one product** into a polished, self-contained HTML
competitive-analysis page — *"where we lead, where we lag, what to build next"* — versus the top
competitors in its market. You give it the product; it researches the rivals, fact-checks every
claim, and renders the briefing.

Built as a [Claude Code](https://claude.com/claude-code) skill (`/competitor`).

---

## What it produces
A single self-contained `.html` file (no build step, no runtime — opens in any browser) with eight
sections: hero · the honest read · the players · a feature matrix (5-status: owned / ahead /
partial / gap / unknown) · where we lead · closeable-in-a-quarter gaps · open strategic questions ·
positioning thesis · sources.

## Two rules it's built around
1. **No fabricated competitor data.** Every competitor claim traces to a real source found on the
   web; anything unverifiable is marked `unknown`, never guessed.
2. **Self-critical, not marketing.** An honest matrix shows real gaps and open questions — not a
   page where you win every row.

## How it works
The per-run job is **research → `data.json` → render**. The page renders deterministically:

```bash
python3 scripts/build_page.py data.json -o my-product-comparison.html
```

You never hand-write HTML — the design (fonts, colors, the verdict system, the 8-section layout,
charts) is baked into the renderer + `assets/base.css`, and all derived numbers (coverage %, counts)
are computed.

## The flow (from just a product)
1. **Ingest** — share a repo / URL / doc / a few sentences; "our side" is extracted only from your
   materials, never invented.
2. **Discover & confirm** — it finds the top 2 competitors (by market leadership) and shows you the
   picks before going deep.
3. **Deep research** — site, pricing, docs, recent news; every fact sourced.
4. **Verify** — claims are adversarially fact-checked against their sources.
5. **Render** — the page.

See **[PLAN.md](PLAN.md)** for the run/build plan and **[ARCHITECTURE.md](ARCHITECTURE.md)** for the
multi-agent design (fan-out per phase → converge, gated by adversarial verification).

## Repo layout
```
SKILL.md                  # the skill: triggering + workflow
PLAN.md / ARCHITECTURE.md # plan and multi-agent design
scripts/build_page.py     # data.json -> styled HTML (the renderer)
assets/base.css           # extracted, compiled design system (inlined into every page)
references/
  content-spec.md         # data.json schema + research method
  design-system.md        # design tokens + component/verdict reference
  example-data.json       # a complete worked example (renders to a full page)
```

## Use as a skill
Drop this folder into `~/.claude/skills/competitor/` (or clone it there). In Claude Code, it triggers
on requests like *"do a competitor analysis of my product"* or *"make a competitor agent."*
