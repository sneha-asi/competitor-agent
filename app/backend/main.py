"""FastAPI backend for the competitor agent.

Two SSE endpoints around the human approval gate:
  POST /api/discover  -> streams Phase A+B progress, ends with {productProfile, top2, ranked}
  POST /api/build     -> streams Phase C–E progress, ends with {report, html}

Run:  uvicorn main:app --reload --port 8000   (from app/backend, with ../.env populated)
"""
import asyncio
import json
import os
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


def _write_env(updates: dict):
    """Persist settings to app/.env, preserving comments and other lines."""
    lines = ENV_PATH.read_text().splitlines() if ENV_PATH.exists() else []
    done, out = set(), []
    for ln in lines:
        head = ln.split("=", 1)[0].strip()
        if ln.strip() and not ln.lstrip().startswith("#") and head in updates:
            out.append(f"{head}={updates[head]}"); done.add(head)
        else:
            out.append(ln)
    for k, v in updates.items():
        if k not in done:
            out.append(f"{k}={v}")
    ENV_PATH.write_text("\n".join(out) + "\n")


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
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"  # keep the connection alive through long, quiet phases
                continue
            if event is None:
                break
            yield _sse(event)
    finally:
        task.cancel()


@app.get("/api/health")
async def health():
    return {"ok": True, "model": pipeline.agents.MODEL, "has_key": bool(os.environ.get("ANTHROPIC_API_KEY"))}


@app.post("/api/settings")
async def save_settings(req: Request):
    """Set the API key (validated against Anthropic) and/or the model, from the UI. Saved to app/.env."""
    global _client
    body = await req.json()
    key = (body.get("key") or "").strip()
    model = (body.get("model") or "").strip()
    updates = {}
    if key:
        from anthropic import AsyncAnthropic, AuthenticationError
        try:
            await AsyncAnthropic(api_key=key).models.list(limit=1)  # validates auth, no token cost
        except AuthenticationError:
            return JSONResponse({"error": "Anthropic rejected that key (401). Double-check it."}, status_code=400)
        except Exception as exc:
            return JSONResponse({"error": f"Couldn't validate the key: {exc}"}, status_code=400)
        os.environ["ANTHROPIC_API_KEY"] = key
        updates["ANTHROPIC_API_KEY"] = key
        _client = None  # rebuild with the new key on next request
    if model:
        os.environ["COMPETITOR_MODEL"] = model
        pipeline.agents.MODEL = model
        updates["COMPETITOR_MODEL"] = model
    if updates:
        _write_env(updates)
    return {"ok": True, "has_key": bool(os.environ.get("ANTHROPIC_API_KEY")), "model": pipeline.agents.MODEL}


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
