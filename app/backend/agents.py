"""Thin wrapper that turns each fleet agent (agents/*.md) into a Claude API call.

- System prompt = the agent definition body (frontmatter stripped), prompt-cached so repeated
  calls of the same agent type (e.g. 5 researchers) hit the cache.
- Reasoning-only agents use structured output (`output_config.format`) for guaranteed-valid JSON.
- Web agents (scouts, researchers, verifier) use Claude's built-in web_search/web_fetch tools;
  structured output is skipped for them (it 400s alongside citations), so they're asked for JSON
  and parsed tolerantly. pause_turn (server-tool loop) is resumed automatically.
"""
import json
import os
import pathlib
import re

_AGENTS_DIR = pathlib.Path(__file__).resolve().parents[2] / "agents"

MODEL = os.environ.get("COMPETITOR_MODEL", "claude-opus-4-8")
EFFORT = os.environ.get("COMPETITOR_EFFORT", "high")

WEB_TOOLS = [
    {"type": "web_search_20260209", "name": "web_search"},
    {"type": "web_fetch_20260209", "name": "web_fetch"},
]

_FRONTMATTER = re.compile(r"^---\n.*?\n---\n", re.S)
_prompt_cache: dict[str, str] = {}


def system_prompt(agent_name: str) -> str:
    """Load agents/<agent_name>.md, strip YAML frontmatter, return the system prompt body."""
    if agent_name not in _prompt_cache:
        path = _AGENTS_DIR / f"{agent_name}.md"
        text = path.read_text(encoding="utf-8")
        _prompt_cache[agent_name] = _FRONTMATTER.sub("", text, count=1).strip()
    return _prompt_cache[agent_name]


def _extract_json(text: str):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1:
            return json.loads(text[start:end + 1])
        raise


async def call_agent(client, agent_name, task, *, schema=None, use_web=False,
                     effort=None, max_tokens=16000):
    """Run one agent. Returns parsed JSON (dict) when a schema is given, else the text."""
    sys_text = system_prompt(agent_name)
    output_config = {"effort": effort or EFFORT}
    strict = schema is not None and not use_web
    if strict:
        output_config["format"] = {"type": "json_schema", "schema": schema}
    elif schema is not None:
        task = (task + "\n\nReturn ONLY a JSON object (no prose, no markdown fence) with these "
                "top-level keys: " + ", ".join(schema.get("properties", {}).keys()) + ".")

    kwargs = dict(
        model=MODEL,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": sys_text, "cache_control": {"type": "ephemeral"}}],
        thinking={"type": "adaptive"},
        output_config=output_config,
        messages=[{"role": "user", "content": task}],
    )
    if use_web:
        kwargs["tools"] = WEB_TOOLS

    response = await client.messages.create(**kwargs)

    # Resume the server-tool loop if it paused (web_search/web_fetch iteration cap).
    guard = 0
    while response.stop_reason == "pause_turn" and guard < 6:
        guard += 1
        kwargs["messages"] = [
            {"role": "user", "content": task},
            {"role": "assistant", "content": response.content},
        ]
        response = await client.messages.create(**kwargs)

    text = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")
    if schema is None:
        return text
    return _extract_json(text)
