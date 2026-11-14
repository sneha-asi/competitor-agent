# Competitor Agent — web app

A self-serve frontend for the competitor agent. You give it a product; a FastAPI backend runs the
9-agent fleet on the **Anthropic API** (with Claude's built-in web search), streams progress live,
and renders the briefing — the same design as the CLI skill's `build_page.py`.

```
frontend (React/Vite)  ──fetch+SSE──▶  backend (FastAPI)  ──▶  Anthropic API (agents + web_search)
        ▲                                     │
        └────────── streamed HTML report ◀────┴── build_page.py (deterministic render)
```

## Run it

**1. Backend** (needs your key):
```bash
cd app
cp .env.example .env            # then put your ANTHROPIC_API_KEY in .env
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**2. Frontend** (new terminal):
```bash
cd app/frontend
npm install
npm run dev                     # opens http://localhost:5173 (proxies /api to :8000)
```

Open http://localhost:5173 → enter your product (URL / repo path / doc / description) → **Find
competitors** → approve the top 2 → **Build report** → download the HTML.

## How it maps to the fleet
- The backend loads each agent's system prompt from `../agents/*.md` (single source of truth) and
  calls Claude once per agent, prompt-cached.
- Research agents (scouts, dimension researchers, verifier) use Claude's `web_search`/`web_fetch`
  server tools. Reasoning agents use structured output (`output_config.format`).
- Two endpoints around the human gate: `POST /api/discover` (Phases A–B → returns the top 2) and
  `POST /api/build` (Phases C–E → returns the validated data + rendered HTML). Both stream progress
  over SSE.

## Cost & model
Defaults to `claude-opus-4-8`. A full run spawns ~20 agent calls with web search, so it uses real
tokens. Set `COMPETITOR_MODEL=claude-sonnet-4-6` in `.env` to cut cost ~40%, and
`COMPETITOR_EFFORT`/`COMPETITOR_SKEPTICS` to tune depth.

## Files
```
app/
├── .env.example
├── backend/
│   ├── main.py          # FastAPI + SSE endpoints
│   ├── pipeline.py      # async orchestration of Phases A–E
│   ├── agents.py        # agents/*.md → Claude API call (caching, web tools, structured output)
│   ├── schemas.py       # structured-output JSON schemas
│   ├── render.py        # reuse ../scripts/build_page.py
│   └── requirements.txt
└── frontend/            # React/Vite single-page UI (form → progress → approve → report)
```
