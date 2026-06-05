"""FastAPI backend for the competitor agent.

Two SSE endpoints around the human approval gate:
  POST /api/discover  -> streams Phase A+B progress, ends with {productProfile, top2, ranked}
  POST /api/build     -> streams Phase C–E progress, ends with {report, html}

Run:  uvicorn main:app --reload --port 8000   (from app/backend, with ../.env populated)
"""
import asyncio
import json
import pathlib

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

ENV_PATH = pathlib.Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)

import pipeline   # noqa: E402
import render      # noqa: E402

app = FastAPI(title="Competitor Agent")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_client = None


def get_client():
    """Lazily build the Anthropic client. If the key is missing, re-read .env (so adding it after
    the server is already running just works), and fail with a clear message if it's still absent."""
    global _client
    if _client is None:
        import os
        from anthropic import AsyncAnthropic
        if not os.environ.get("ANTHROPIC_API_KEY"):
            load_dotenv(ENV_PATH, override=True)  # pick up a key added to .env after startup
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set — add it to app/.env (no restart needed).")
        _client = AsyncAnthropic(api_key=key)
    return _client


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def _stream(make_coro):
    """Run a pipeline coroutine, relaying its emitted progress events as SSE, then a final result."""
    queue: asyncio.Queue = asyncio.Queue()

    async def emit(event: dict):
        await queue.put(event)

    async def runner():
        try:
            result = await make_coro(emit)
            await queue.put({"type": "result", **result})
        except Exception as exc:  # surface failures to the UI instead of hanging
            await queue.put({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
        finally:
            await queue.put(None)

    task = asyncio.create_task(runner())
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            yield _sse(event)
    finally:
        task.cancel()


@app.get("/api/health")
async def health():
    import os
    return {"ok": True, "model": pipeline.agents.MODEL, "has_key": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@app.post("/api/discover")
async def discover(req: Request):
    body = await req.json()
    product = body.get("product") or {}
    if not product.get("ref"):
        return JSONResponse({"error": "product.ref is required"}, status_code=400)

    async def make(emit):
        return await pipeline.discover(get_client(), product, emit)

    return StreamingResponse(_stream(make), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/build")
async def build(req: Request):
    body = await req.json()
    profile = body.get("productProfile")
    competitors = body.get("competitors") or []
    meta = body.get("meta") or {}
    if not profile or not competitors:
        return JSONResponse({"error": "productProfile and competitors are required"}, status_code=400)

    async def make(emit):
        out = await pipeline.build(get_client(), profile, competitors, meta, emit)
        out["html"] = render.render_html(out["data"])  # Phase F: deterministic render
        return out

    return StreamingResponse(_stream(make), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
