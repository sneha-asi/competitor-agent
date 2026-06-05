"""Render data.json -> HTML by reusing the skill's deterministic renderer (scripts/build_page.py)."""
import pathlib
import sys

_SCRIPTS = pathlib.Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import build_page  # noqa: E402  (from ../../scripts/build_page.py)


def render_html(data: dict) -> str:
    """data must follow references/content-spec.md / example-data.json shape."""
    return build_page.build(data)
