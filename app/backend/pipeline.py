"""Async orchestration of the agent fleet (Phases A–E), mirroring scripts/competitor_workflow.js.

Each public coroutine takes an async `emit(dict)` callback used to stream phase progress to the
frontend over SSE. Phase F (render) is done by the caller via render.py.
"""
import asyncio
import os
import pathlib

import agents
import schemas

SKEPTICS = max(1, min(3, int(os.environ.get("COMPETITOR_SKEPTICS", "2"))))

DIMENSIONS = [
    ("pricing", "Pricing & packaging: tiers, free vs paid vs enterprise-gated, seat/usage limits. Primary source: the official pricing page."),
    ("features", "Core product & differentiators: headline capabilities, signature feature, integrations, API/SDK. Primary: product/features pages + docs/API + changelog."),
    ("positioning", "Positioning & ICP: claimed category, target buyer, value prop, marquee customers. Source: homepage, about, case studies."),
    ("momentum", "Momentum & scale: funding, customer/logo counts, recent launches, trajectory. Source: funding/press/news."),
    ("weaknesses", "Weaknesses & gaps: known limitations and recurring complaints, each WITH a representative source. Source: G2/Capterra/Reddit/forums."),
]

DISCOVERY_ANGLES = [
    ("substitution", 'SUBSTITUTION search: "alternatives to {name}", "{name} vs", "best {category} tools 2026". List products buyers compare against {name}.'),
    ("analyst", 'ANALYST/DIRECTORY signal: G2 / Capterra / TrustRadius / Gartner for "{category}". List the category leaders and their standing.'),
    ("funding", 'FUNDING & NEWS: who in "{category}" is best-funded / most-covered / fastest-growing now. Capture funding, customers, traction.'),
    ("community", 'COMMUNITY signal: Reddit / HN / forums / "X vs Y" posts about "{category}". What do practitioners actually compare and pick?'),
]


async def _progress(emit, phase, message):
    await emit({"type": "progress", "phase": phase, "message": message})


# ----------------------------------------------------------------- product material intake
_REPO_GLOBS = ["README*", "readme*", "package.json", "pyproject.toml", "setup.py",
               "requirements.txt", "Cargo.toml", "go.mod", "docs/*.md", "*.md"]


def gather_material(product: dict):
    """Return (material_text_or_None, is_url). URLs are researched by the agent via web_fetch."""
    kind = (product.get("kind") or "text").lower()
    ref = product.get("ref", "")
    if kind == "url" or ref.startswith("http"):
        return None, True
    if kind in ("text", "doc"):
        p = pathlib.Path(ref)
        if kind == "doc" and p.exists():
            return p.read_text(encoding="utf-8", errors="ignore")[:60000], False
        return ref[:60000], False
    if kind == "repo":
        root = pathlib.Path(ref)
        chunks, total = [], 0
        if root.exists():
            seen = set()
            for pat in _REPO_GLOBS:
                for f in sorted(root.glob(pat))[:20]:
                    if f.is_file() and f not in seen and total < 50000:
                        seen.add(f)
                        body = f.read_text(encoding="utf-8", errors="ignore")[:8000]
                        chunks.append(f"### {f.relative_to(root)}\n{body}")
                        total += len(body)
        return ("\n\n".join(chunks) or ref)[:60000], False
    return ref[:60000], False


def _platform_names(product_profile, competitors):
    return [c["name"] for c in competitors] + [product_profile["name"]]


# ----------------------------------------------------------------- Phase A + B (discover)
async def discover(client, product: dict, emit):
    material, is_url = gather_material(product)
    notes = ("\nUser notes: " + product["notes"]) if product.get("notes") else ""

    await _progress(emit, "Intake", "Reading the product…")
    if is_url:
        url = product["ref"]
        reader_tasks = [
            f"Read the homepage and product/features pages at {url} (use web_fetch).{notes}",
            f"Read the PRICING page under {url} (find /pricing).{notes}",
            f"Read the docs/changelog/blog under {url}.{notes}",
        ]
        readers = [agents.call_agent(client, "intake-reader", t, schema=schemas.PROFILE_PART, use_web=True)
                   for t in reader_tasks]
    else:
        mat = material or ""
        reader_tasks = [
            f"Extract what the product does and its capabilities from this material.{notes}\n\nMATERIAL:\n{mat}",
            f"Extract category, ICP, signature feature, and competitor/category keywords from this material.{notes}\n\nMATERIAL:\n{mat}",
        ]
        readers = [agents.call_agent(client, "intake-reader", t, schema=schemas.PROFILE_PART)
                   for t in reader_tasks]
    parts = [p for p in await asyncio.gather(*readers, return_exceptions=True) if isinstance(p, dict)]

    await _progress(emit, "Intake", "Synthesizing our-side profile…")
    import json
    profile = await agents.call_agent(
        client, "product-synthesizer",
        "Merge these partial reads of OUR product into one clean profile.\n\nPartial reads:\n" + json.dumps(parts),
        schema=schemas.PRODUCT_PROFILE)
    await _progress(emit, "Intake", f"Product understood: {profile.get('name','(unnamed)')} — {profile.get('category','')}")

    await _progress(emit, "Discovery", "Sweeping the market (4 blind angles)…")
    seeds = ", ".join(profile.get("search_seeds", []))
    scout_tasks = []
    for key, tmpl in DISCOVERY_ANGLES:
        angle = tmpl.format(name=profile["name"], category=profile.get("category", ""))
        task = (f"Product: {profile['name']} — {profile.get('what_it_is', profile.get('category',''))}\n"
                f"Category: {profile.get('category','')}\nSearch seeds: {seeds}\n\nYour angle — {angle}")
        scout_tasks.append(agents.call_agent(client, "discovery-scout", task, schema=schemas.CANDIDATE_LIST, use_web=True))
    sweeps = [s for s in await asyncio.gather(*scout_tasks, return_exceptions=True) if isinstance(s, dict)]
    candidates = [c for s in sweeps for c in s.get("candidates", [])]

    await _progress(emit, "Discovery", f"Ranking {len(candidates)} candidates by market leadership…")
    ranked = await agents.call_agent(
        client, "ranker",
        f'Rank competitors for "{profile["name"]}" ({profile.get("category","")}). De-duplicate, drop '
        f"noise, rank by MARKET LEADERSHIP, and nominate the top 2.\n\nCandidates:\n" + json.dumps(candidates),
        schema=schemas.RANKED)
    top2 = ranked.get("top2", [])
    await _progress(emit, "Discovery", "Top 2: " + " · ".join(c["name"] for c in top2))
    return {"productProfile": profile, "ranked": ranked.get("ranked", []), "top2": top2}


# ----------------------------------------------------------------- Phase C–E (build)
async def _research_competitor(client, comp, emit):
    import json
    await _progress(emit, "Research", f"Researching {comp['name']} across {len(DIMENSIONS)} dimensions…")
    tasks = [agents.call_agent(
        client, "dimension-researcher",
        f"Competitor: \"{comp['name']}\" ({comp.get('url','find their site')}).\nDimension — {key}: {focus}",
        schema=schemas.FINDINGS, use_web=True) for key, focus in DIMENSIONS]
    findings = [f for f in await asyncio.gather(*tasks, return_exceptions=True) if isinstance(f, dict)]
    await _progress(emit, "Research", f"Synthesizing {comp['name']} profile…")
    return await agents.call_agent(
        client, "profile-synthesizer",
        f"Competitor: \"{comp['name']}\".\n\nDimension findings:\n" + json.dumps(findings),
        schema=schemas.COMPETITOR_PROFILE)


async def build(client, product_profile: dict, competitors: list, meta: dict, emit):
    import json
    profiles = [p for p in await asyncio.gather(
        *[_research_competitor(client, c, emit) for c in competitors], return_exceptions=True)
        if isinstance(p, dict)]

    names = _platform_names(product_profile, competitors)
    await _progress(emit, "Synthesis", "Building the feature matrix…")
    matrix = await agents.call_agent(
        client, "matrix-builder",
        f"Platform keys to use in each row's verdicts (array of objects with a 'platform' field): "
        f"{json.dumps(names)}. Our product: \"{product_profile['name']}\".\n\n"
        f"Our product profile:\n{json.dumps(product_profile)}\n\nCompetitor profiles:\n{json.dumps(profiles)}",
        schema=schemas.MATRIX)

    await _progress(emit, "Synthesis", "Writing the narrative…")
    narrative = await agents.call_agent(
        client, "narrative-writer",
        f"Product: \"{product_profile['name']}\" vs {', '.join(c['name'] for c in competitors)}.\n\n"
        f"Matrix:\n{json.dumps(matrix)}\n\nCompetitor profiles:\n{json.dumps(profiles)}\n\n"
        f"Our product profile:\n{json.dumps(product_profile)}",
        schema=schemas.NARRATIVE)

    # ---- Phase E: adversarial verification of risky competitor claims ----
    comp_names = {c["name"] for c in competitors}
    claims = []
    for ci, cap in enumerate(matrix.get("capabilities", [])):
        for v in cap.get("verdicts", []):
            if v.get("platform") in comp_names and v.get("source") and v.get("status") in ("owned", "ahead", "gap"):
                claims.append((ci, v, cap["name"]))
    await _progress(emit, "Verify", f"Verifying {len(claims)} competitor claims with {SKEPTICS} skeptics each…")

    lenses = ["Read the cited source literally — does it state this, or are you inferring?",
              "Check recency and scope — is the source current and about the right product/edition?",
              "Look for contradiction — does anything on the source contradict the claim?"]

    async def verify(ci, v, cap_name):
        prompt = (f'Claim: "{v["platform"]} — {cap_name}: status={v["status"]}'
                  f'{(" (" + v.get("note","") + ")") if v.get("note") else ""}".\nCited source: {v["source"]}\n')
        votes = await asyncio.gather(*[
            agents.call_agent(client, "claim-verifier", prompt + "Lens: " + lenses[k % len(lenses)],
                              schema=schemas.REFUTE, use_web=True, effort="low")
            for k in range(SKEPTICS)], return_exceptions=True)
        ok = [x for x in votes if isinstance(x, dict)]
        supported = sum(1 for x in ok if x.get("supported"))
        return ci, v, cap_name, (supported * 2 >= len(ok) if ok else True)

    downgrades = []
    for ci, v, cap_name, kept in await asyncio.gather(*[verify(*c) for c in claims]):
        if not kept:
            v["status"], v["note"], v["source"] = "unknown", "unverified", v.get("source")
            downgrades.append(f"{v['platform']} / {cap_name}: {v['status']} → unknown")

    data, report = _assemble(product_profile, competitors, profiles, matrix, narrative, meta, downgrades)
    await _progress(emit, "Verify", f"Verification complete: {len(downgrades)} claim(s) downgraded.")
    return {"data": data, "report": report}


# ----------------------------------------------------------------- assemble data.json
def _player_card(p, is_product):
    return {
        "name": p["name"], "short_name": p.get("short_name", p["name"]),
        "category_label": p.get("category_label") or (p.get("category", "") if is_product else ""),
        "money_question": p.get("money_question", ""), "signature": p.get("signature", ""),
        "footprint": (p.get("footprint") or [])[:2], "url": p.get("url", ""),
    }


def _assemble(product_profile, competitors, profiles, matrix, narrative, meta, downgrades):
    pp_name = product_profile["name"]
    comp_names = {c["name"] for c in competitors}

    caps = []
    for cap in matrix.get("capabilities", []):
        verdicts = {}
        for v in cap.get("verdicts", []):
            plat = v.get("platform")
            if not plat:
                continue
            # provenance guard: competitor cell with a definite status but no source -> unknown
            if plat in comp_names and v.get("status") in ("owned", "ahead", "partial", "gap") and not v.get("source"):
                verdicts[plat] = {"status": "unknown", "note": v.get("note", "no source")}
            else:
                verdicts[plat] = {k: v[k] for k in ("status", "note", "source") if v.get(k)}
        # home-team-bias guard: our "ahead" only counts if no rival also has the row
        ours = verdicts.get(pp_name)
        if ours and ours.get("status") == "ahead":
            if any(verdicts.get(c["name"], {}).get("status") in ("owned", "ahead") for c in competitors):
                ours["status"] = "owned"
                ours["note"] = (ours.get("note", "") + "; parity — rival also has it").strip("; ")
        caps.append({"name": cap.get("name", ""), "reality": cap.get("reality", ""), "verdicts": verdicts})

    # dedupe external sources
    src = {}
    for p in profiles:
        for s in p.get("sources", []):
            if s.get("url"):
                src[s["url"]] = s.get("label") or s["url"]
    for cap in caps:
        for v in cap["verdicts"].values():
            if v.get("source"):
                src.setdefault(v["source"], v["source"])

    data = {
        "meta": meta or {},
        "product": _player_card({**product_profile, "category_label": product_profile.get("category")}, True),
        "competitors": [_player_card(p, False) for p in profiles],
        "hero": narrative.get("hero", {}),
        "tldr": narrative.get("tldr", {}),
        "matrix": {"capabilities": caps, "glance_notes": matrix.get("glance_notes", [])},
        "ahead": narrative.get("ahead", {}),
        "closeable": narrative.get("closeable", {}),
        "decisions": narrative.get("decisions", {}),
        "positioning": narrative.get("positioning", {}),
        "sources": {"external": [{"label": l, "url": u} for u, l in src.items()], "internal": []},
    }
    report = {
        "competitors": [c["name"] for c in competitors],
        "rows": len(caps), "claims_downgraded": downgrades, "sources": len(src),
    }
    return data, report
