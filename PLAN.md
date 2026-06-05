# Plan

Where this is headed and why it's built the way it is. The actual design — agents, data contracts, the verification gate — is in [ARCHITECTURE.md](ARCHITECTURE.md). This is the higher-level stuff.

## What I'm actually building

One product in, a competitive analysis out, that I'd be fine putting in front of a board or a sales team without caveating half of it. That means two things at once: it has to be thorough, and it has to be honest about what it doesn't know. Most tools pick one. This is the whole point of the project.

## The rules it's built around

- **No made-up data.** Every competitor claim points to a real source. Anything it can't verify is marked unknown, not guessed. Enforced in code and by the agents that try to refute each claim.
- **It stays self-critical.** Real gaps and open questions are the deliverable, not an afterthought. Our own "ahead" only counts where no rival matches us.
- **Our side is never invented.** Whatever it says about your product comes only from what you handed it.
- **I stay in the loop on the expensive calls.** Confirm what the product is, approve the two competitors — both before any deep research burns tokens.
- **Deterministic where it should be.** The research and judgment are the model's job; the final render is a fixed template, so the report comes out the same shape every time.

## How a run goes

```
Intake → [confirm product] → Discovery → [approve top 2]
       → Research → Synthesis → Verify → Render
```

Same agents and same renderer behind two front doors: the `/competitor` skill (zero setup, runs in Claude Code) and the standalone web app (runs on the Anthropic API). Both are covered in the [README](README.md).

## Decisions already made

- Depth: exhaustive — full matrix, all sections, every claim sourced.
- "Biggest" competitors means ranked by market leadership, not whoever's closest.
- Always confirm the top two before researching.
- Two competitors by default.
- Orchestration: agents fan out per phase and converge, with the verification gate at the end.

## Where it's at

Done:

- the renderer and the design system, checked end to end
- the nine agents, each its own file, installable as live subagents
- the orchestrator (phases A–E) with the cite-or-void and home-team-bias guards
- the research-backed methodology baked into the prompts
- the web app — FastAPI backend (compiles) and React/Vite frontend (builds), render path verified
- the docs: this, the README, the architecture write-up, the schema, design tokens, a worked example, a sample report

Not done yet:

- a real end-to-end run. Needs an `ANTHROPIC_API_KEY` in `app/.env`. That run is also the first proper test of the prompts against the live API and web search, so I expect to tune things once I see real output.

## What's next

Soon:

- run it on a real product and tune the prompts, effort levels, and skeptic counts against what actually comes back
- cache research per competitor so re-runs are cheap
- let you pick more than two competitors, and add a "closest rival" ranking mode alongside "biggest"

Later:

- keep run history so you can diff a market over time and see what changed
- one-click deploy for the web app
- export to PDF or a slide deck from the same data
- scheduled re-runs that ping you when a competitor changes something that matters
