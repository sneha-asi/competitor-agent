---
name: competitor
description: >-
  Generate a polished, self-contained HTML competitive-analysis page comparing the user's product
  against the top competitors in its market — a "where we lead, where we lag, what to build next"
  briefing with a feature matrix, coverage chart, moats, closeable gaps, open questions, and a
  positioning thesis. Works from JUST the product (a repo, URL, doc, or description): the skill
  researches the market, identifies the top 2 competitors itself, and grounds every competitor
  claim in REAL web research — never invented. Use whenever the user wants a competitor analysis,
  competitive-intelligence brief, "us vs them" page, battlecard, vs/comparison page, or win-loss
  teardown, or asks to "make a competitor agent", "size up my competitors", or "compare us to X".
  NOT for code/string diffing, git comparisons, or A/B copy tests.
---

# Competitor analysis page

Produce a single, beautiful, self-contained HTML page that compares the user's product against the
top players in its market and reads like a strategy briefing: where we lead, where we lag, and what
to build next. The visual design is fixed (it reuses an extracted design system), so the real work
is the **research and the judgment** — the rendering is automatic.

The page is the artifact a founder or PM would put in front of a board or a sales team. That only
works if it's honest and sourced. The two rules that matter most:

1. **No fabricated competitor data.** Every competitor claim traces to a real source you found on
   the web. If you can't establish a fact, mark it `unknown` — don't guess.
2. **Be self-critical.** A matrix where we win every row is marketing, not intelligence. Surface
   real gaps and real open questions; that's what makes the rest credible.

## How it works

The page renders deterministically from a single `data.json`:

```
python3 scripts/build_page.py data.json -o <product>-comparison.html
```

So the job is: **ingest the product → discover & confirm rivals → deep research → write
`data.json` → render → verify.** You never write HTML/CSS by hand. The design (fonts, colors, the
5-status verdict system, the 8-section layout, sidebar nav, charts) lives in
[scripts/build_page.py](scripts/build_page.py) + [assets/base.css](assets/base.css). All derived
numbers (coverage %, counts, hero stats) are computed by the script — never author them.

## Defaults (how this skill is meant to run)
- **Find the rivals yourself** from just the product, unless the user names them.
- Rank by **market leadership** — the dominant, most-recognized names buyers benchmark against — not
  raw funding/size.
- **Confirm your 2 picks** with the user before investing in deep research.
- Produce the **exhaustive** version: full feature matrix, all eight sections, every competitor
  claim sourced.

## Workflow

### 1. Ingest the product (the only required input)
The user gives you the product in whatever form they have — a **repo** (read README, `docs/`,
package metadata, key source files), a **URL** (`WebFetch` the site + product/pricing pages), a
**doc/file** (read it), or a few **sentences**. Extract: what it does, its category/market, who
it's for, and its real capabilities. This is "our side" of the comparison — use only what's in
their materials, and **never invent our feature list**. If the materials are thin, ask one or two
sharp questions instead of guessing. For internal/clean-room products, take our-side facts only
from what the user shared.

### 2. Discover the top 2 competitors — then confirm
Unless the user already named them, find them: `WebSearch` for "alternatives to <product>",
"<product> vs", "top <category> tools 2026"; scan G2/Capterra category leaders and funding/news.
Rank by **market leadership**, not raw size. Then **stop and confirm** — present the 2 picks with a
one-line rationale each and let the user approve or swap before you go deep. Two is the default
count (use `AskUserQuestion` so swapping is one click).

### 3. Deep research on the two competitors (real web research)
`WebSearch` to find, `WebFetch` to read each one's official site, **pricing page**, **docs/API
reference** (often more honest than marketing), and recent news/changelog. Record the URL for every
fact you'll use; prefer primary sources and corroborate each claimed gap with a second source. Full
method: [references/content-spec.md](references/content-spec.md). The `deep-research` skill is a
strong engine for this exhaustive pass if available — feed its findings into `data.json`.

### 4. Write `data.json`
Build the structured data following the schema in
[references/content-spec.md](references/content-spec.md). A complete worked example is
[references/example-data.json](references/example-data.json) — copy its shape.

The eight sections (each rendered only if you provide its data):
1. **overview** — hero: "Product vs A vs B", tagline, computed stat grid
2. **tldr** — the honest read in one paragraph + three summary chips
3. **players** — one card per product (category, money question, signature, footprint, coverage %)
4. **matrix** — coverage chart + the row-by-row feature matrix with 5-status verdicts
5. **lead** — the moats where we're genuinely ahead
6. **closeable** — gaps closeable in a quarter (effort vs. strategic value)
7. **decisions** — strategic open questions (the dark section)
8. **positioning** — the one-paragraph thesis + what it takes to reach parity

Verdict statuses (heart of the matrix): `owned` (green) · `ahead` (blue, a differentiator) ·
`partial` (amber) · `gap` (red) · `unknown` (grey). Coverage % counts `owned`+`ahead`. Every
competitor verdict should carry a `source`. Always fill the `sources` block — it's the proof.

### 5. Render
```
python3 scripts/build_page.py data.json -o <name>-comparison.html
```
The script prints the byte size and how many sections rendered.

### 6. Verify before delivering
Open the file and confirm it renders: sections present, no broken layout, charts/table populated,
no literal `&amp;` / `&#x27;` showing as text. If a preview tool is available, screenshot it; on
macOS `open <file>.html` shows it in the browser. Then hand the user the path.

## Orchestrated (multi-agent) mode — the exhaustive default
For the exhaustive run, drive the subagent fleet in `scripts/competitor_workflow.js` via the
**Workflow** tool, in two stages around the approval gate (full design:
[ARCHITECTURE.md](ARCHITECTURE.md)):

1. **Discover** — `Workflow({ scriptPath: ".../scripts/competitor_workflow.js", args: { stage:
   "discover", product: { kind: "repo|url|doc|text", ref: "<path/url/text>", notes: "" } } })`.
   Returns `{ productProfile, ranked, top2 }`. Play back the product understanding (Gate 1), then
   present `top2` (with `ranked` as alternates) via `AskUserQuestion` — user approves or swaps (Gate 2).
2. **Build** — `Workflow({ scriptPath, args: { stage: "build", productProfile, competitors: [approved],
   meta: { org, date_label, author } } })`. Runs Phases C–E (research → synthesis → adversarial
   verification) and returns `{ data, report }` — a validated `data.json`.
3. **Render** — write `data` to `data.json`, run `python3 scripts/build_page.py data.json -o
   <name>-comparison.html`, verify, deliver. Share the `report` (rows, claims verified, what was
   downgraded to `unknown`).

This spawns many subagents and costs real tokens — **confirm with the user before launching each
stage**. For a quick/cheap pass, skip the workflow and do steps 1–6 above inline. Methodology the
agents follow: [references/methodology.md](references/methodology.md).

## Editing
- To change **content/numbers** → edit `data.json` and re-render. Never hand-edit the HTML output.
- To change the **design itself** (a new section type, color tweak) → edit `scripts/build_page.py`.
  Reuse only class names already present in `assets/base.css` (it's a compiled stylesheet — unknown
  Tailwind classes won't exist); for genuinely new visuals use inline `style=` like the charts do.
- Design tokens and the component catalog: [references/design-system.md](references/design-system.md).
