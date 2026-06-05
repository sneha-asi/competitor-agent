# Competitor Agent

You give it a product. It works out who your two biggest competitors are, researches them properly, and hands back a competitive analysis you can actually trust. Every claim it makes about a competitor links to a real source, and anything it can't pin down it marks as *unknown* instead of making something up.

I built this because most "AI competitor analysis" is confident nonsense. Long, polished, and quietly half-invented. This one is built the other way around: it would rather say "couldn't verify this" than fill the gap with a guess.

<img src="docs/hero.png" alt="A sample report" width="900">

There's a full sample you can open in a browser: [docs/example-report.html](docs/example-report.html). That's the design every run produces.

## What it does

Point it at your product (a website, a repo, a doc, or just a paragraph describing it) and it:

- reads your product and figures out what it actually does — only from what you give it, it won't invent features on your behalf
- searches the market, picks your top two competitors, and checks the picks with you before spending any real time
- digs into each one: pricing, the actual product, how they position, funding/traction, and where they're weak
- argues with itself. A separate batch of agents try to *disprove* every competitor claim against the source it came from. Anything that doesn't hold up gets downgraded to unknown.
- renders the whole thing as one self-contained HTML page you can open anywhere or hand to someone

## Two rules I didn't want it to break

1. **No made-up data.** If a claim about a competitor doesn't have a source behind it, it doesn't ship. This is enforced twice over — in code (a cell with no citation gets voided) and by the agents that try to refute each claim.
2. **It's not a marketing deck.** If you're winning every row of the matrix, something's off. The output is supposed to show you where you're behind and which questions are genuinely undecided, not flatter you. Your own "ahead" only counts on rows where no competitor matches you.

## Running it

Two ways, depending on whether you live in Claude Code or want a real UI.

**Inside Claude Code** — no setup. Just ask:

> do a competitor analysis of https://myproduct.com

It uses the `/competitor` skill in this repo: ingests the product, comes back with the two competitors for you to okay, then researches, verifies, and writes the report. See [SKILL.md](SKILL.md).

**As a web app** — the standalone version, runs on the Anthropic API (one key covers the agents *and* the web search):

```bash
cd app
cp .env.example .env          # drop your ANTHROPIC_API_KEY in here
cd backend && pip install -r requirements.txt && uvicorn main:app --port 8000
cd ../frontend && npm install && npm run dev      # http://localhost:5173
```

Enter a product, watch the phases stream by, approve the two competitors, download the report. More in [app/README.md](app/README.md).

## How it works, roughly

It runs in phases. Each phase kicks off a few small agents that each go do one thing, then their results get pulled back together before the next phase starts:

```
Intake  →  [you confirm the product]  →  Discovery  →  [you approve the top 2]
        →  Research  →  Synthesis  →  Verify  →  Render
```

- **Intake / Discovery** read your product and find the rivals (four blind searches from different angles, then a ranker picks the two biggest).
- **Research** is five angles per competitor — pricing, features, positioning, momentum, weaknesses — all web-sourced.
- **Synthesis** turns the sourced profiles into the feature matrix and the writing around it.
- **Verify** is the part I care about most: two or three skeptics per claim, each told to refute it against its source. Majority can't back it up, it becomes unknown.
- **Render** is deterministic — no model touches the final HTML, so it comes out the same shape every time.

If you want the actual design (data contracts, the verification gate, all nine agents), it's written up in [ARCHITECTURE.md](ARCHITECTURE.md).

The nine agents live in [`agents/`](agents/), one file each, and both the skill and the web app reuse them:
`intake-reader`, `product-synthesizer`, `discovery-scout`, `ranker`, `dimension-researcher`, `profile-synthesizer`, `matrix-builder`, `narrative-writer`, `claim-verifier`.

## What's in here

```
SKILL.md                     the /competitor skill (how it triggers, the workflow)
PLAN.md  ARCHITECTURE.md      where it's going, and how it's built
agents/                      the nine agents, one file each
scripts/
  build_page.py              data.json -> the styled HTML report
  competitor_workflow.js     the orchestrator (phases A-E)
  install-agents.sh          registers the agents as live Claude Code subagents
assets/base.css              the design system, inlined into every report
references/                  data schema, research method, design tokens, a worked example
app/                         the standalone web app (FastAPI + React/Vite)
docs/                        the sample report and the screenshot above
```

## Config

The skill just uses your Claude Code session. The web app reads `app/.env`:

- `ANTHROPIC_API_KEY` — required for the app
- `COMPETITOR_MODEL` — defaults to `claude-opus-4-8`; set `claude-sonnet-4-6` if you want it cheaper
- `COMPETITOR_EFFORT` — `low` / `medium` / `high` / `xhigh` / `max`
- `COMPETITOR_SKEPTICS` — how many verifiers per claim (default 2)

Heads up: a full app run fires off around twenty web-enabled agent calls, so it does cost real tokens. The knobs above are how you keep that in check.

## Status

The renderer, the design system, the nine agents, the orchestrator, and the web app are all in place — backend compiles, frontend builds, and the render path is verified against the sample data. The one thing left is a real end-to-end run, which needs an API key. The roadmap's in [PLAN.md](PLAN.md).
