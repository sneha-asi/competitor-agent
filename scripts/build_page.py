#!/usr/bin/env python3
"""Render a competitive-analysis HTML page from a data.json.

Usage:
    python3 build_page.py data.json [-o output.html]

The design is fixed (it reuses assets/base.css and the exact component class names
from the original Lovable export, so the look is preserved byte-for-byte where it
matters). Everything that varies — products, capabilities, verdicts, prose — comes
from data.json. All derived numbers (coverage %, section counts) are COMPUTED here,
never authored, so the document is internally consistent.

See ../references/content-spec.md for the data.json schema and the no-fake-data rules.
"""
import argparse
import html
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASE_CSS = HERE.parent / "assets" / "base.css"
FONTS_LINK = ('<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700'
              '&family=Inter:wght@400;500;600;700&family=Geist:wght@400;500;600&display=swap" rel="stylesheet">')

# Verdict system — exact colors from the original. Order matters for the legend.
STATUS = {
    "owned":   {"label": "Owned",   "fg": "#0F9D58", "bg": "#DFF6E8", "bd": "#0F9D58"},
    "ahead":   {"label": "Ahead",   "fg": "#245AE2", "bg": "#D3DEF9", "bd": "#245AE2"},
    "partial": {"label": "Partial", "fg": "#D97706", "bg": "#FEF3C7", "bd": "#D97706"},
    "gap":     {"label": "Gap",     "fg": "#DC2626", "bg": "#FEE2E2", "bd": "#DC2626"},
    "unknown": {"label": "Unknown", "fg": "#666666", "bg": "#F4F3F2", "bd": "#CCCCCC"},
}
POSITIVE = {"owned", "ahead"}  # counted toward coverage

# Bar colors assigned to competitors in order; our product always gets the lime accent.
COMPETITOR_BAR = ["#245AE2", "#01194C", "#7C3AED", "#0EA5E9"]
PRODUCT_BAR = {"fill": "#D6F549", "stroke": "#80932C"}

# Lucide icon paths (24x24) used in the TL;DR chips.
ICONS = {
    "check":    '<circle cx="12" cy="12" r="10"></circle><path d="m9 12 2 2 4-4"></path>',
    "trending": '<path d="M16 7h6v6"></path><path d="m22 7-8.5 8.5-5-5L2 17"></path>',
    "alert":    '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"></path>'
                '<path d="M12 9v4"></path><path d="M12 17h.01"></path>',
    "arrow":    '<path d="M7 7h10v10"></path><path d="M7 17 17 7"></path>',
}
CHIP_TONE = {
    "green": {"fg": "#0F9D58", "bg": "#DFF6E8", "bd": "#0F9D58"},
    "blue":  {"fg": "#245AE2", "bg": "#D3DEF9", "bd": "#245AE2"},
    "amber": {"fg": "#D97706", "bg": "#FEF3C7", "bd": "#D97706"},
}

# The eight fixed sections (id, sidebar label). A section is rendered only if it has data.
SECTIONS = [
    ("overview",    "Overview"),
    ("tldr",        "TL;DR"),
    ("players",     "The Players"),
    ("matrix",      "Feature Matrix"),
    ("lead",        "Where We Lead"),
    ("closeable",   "Closeable Gaps"),
    ("decisions",   "Strategic Decisions"),
    ("positioning", "Positioning"),
]


def e(s):
    """Escape plain text."""
    return html.escape(str(s if s is not None else ""))


def raw(s):
    """Pass through (for fields documented as HTML-allowed: paragraphs, prose with <strong>)."""
    return str(s if s is not None else "")


# --------------------------------------------------------------------------- pills & bits

def status_pill(status, font_size="10px"):
    s = STATUS.get(status, STATUS["unknown"])
    return (f'<span class="font-cta inline-flex items-center gap-1.5 rounded-md border '
            f'transition-transform hover:scale-105 px-2 py-0.5" '
            f'style="color:{s["fg"]};background:{s["bg"]};border-color:{s["bd"]};font-size:{font_size}">'
            f'<span class="inline-block h-1.5 w-1.5 rounded-full" style="background:{s["fg"]}"></span>'
            f'{e(s["label"])}</span>')


def kicker(text, dark=False):
    if dark:
        return (f'<span class="font-cta inline-flex rounded-md border px-2 py-1" '
                f'style="color:#D6F549;border-color:rgba(214,245,73,0.4)">{e(text)}</span>')
    return (f'<span class="font-cta inline-flex rounded-md border px-2 py-1" '
            f'style="color:#245AE2;border-color:#D3DEF9;background:#F8FAFD">{e(text)}</span>')


def stat_card(value, label, fg="#2F2F2F", bg="#FFFFFF", bd="#E2E8F0"):
    return (f'<div class="rounded-md border px-3 py-2.5" style="border-color:{bd};background:{bg}">'
            f'<div class="font-num text-display-xs" style="color:{fg};font-size:22px">{e(value)}</div>'
            f'<div class="font-cta mt-1" style="color:{fg};font-size:10px">{e(label)}</div></div>')


def section_head(num_label, title, sub, anchor=None):
    """Left column of a standard section header: kicker + h2 + sub.
    The CALLER supplies the enclosing `<div class="grid ... md:grid-cols-12">` wrapper
    (and any right-hand stat column), so headers compose consistently."""
    return f'''<div class="md:col-span-7">
    {kicker(num_label)}
    <h2 class="mt-3 text-display-md md:text-display-lg" style="color:#2F2F2F">{e(title)}</h2>
    <p class="mt-2 text-p-md md:text-p-lg" style="color:#4D4D4D;max-width:760px">{e(sub)}</p>
  </div>'''


# --------------------------------------------------------------------------- platforms

def platforms(data):
    """Ordered list of (name, is_product, short_name) — competitors first, product last."""
    out = []
    for c in data.get("competitors", []):
        out.append((c["name"], False, c.get("short_name", c["name"])))
    p = data["product"]
    out.append((p["name"], True, p.get("short_name", p["name"])))
    return out


def coverage_pct(data, name):
    caps = data.get("matrix", {}).get("capabilities", [])
    if not caps:
        return 0
    pos = sum(1 for cap in caps if cap.get("verdicts", {}).get(name, {}).get("status") in POSITIVE)
    return round(100 * pos / len(caps))


def coverage_count(data, name):
    caps = data.get("matrix", {}).get("capabilities", [])
    pos = sum(1 for cap in caps if cap.get("verdicts", {}).get(name, {}).get("status") in POSITIVE)
    return pos, len(caps)


# --------------------------------------------------------------------------- sections

def render_overview(data):
    p = data["product"]
    hero = data.get("hero", {})
    names = [c.get("short_name", c["name"]) for c in data.get("competitors", [])]
    vs = ' <span style="color:#D6F549">vs</span> '.join(e(n) for n in names)
    title = f'{e(p["name"])}<br><span style="color:#D6F549">vs</span> {vs}' if names else e(p["name"])

    n_caps = len(data.get("matrix", {}).get("capabilities", []))
    n_plat = len(data.get("competitors", [])) + 1
    n_lead = len(data.get("ahead", {}).get("items", []))
    n_close = len(data.get("closeable", {}).get("items", []))
    n_dec = len(data.get("decisions", {}).get("items", []))
    n_sec = sum(1 for sid, _ in SECTIONS if _section_has_data(data, sid))
    cards = [
        (n_caps, "Capabilities scored", "#FFFFFF"),
        (n_plat, "Platforms compared", "#FFFFFF"),
        (n_lead, "Where we lead", "#D6F549"),
        (n_close, "Closeable in 1 qtr", "#FFFFFF"),
        (n_dec, "Strategic choices", "#FFFFFF"),
        (n_sec, "Sections in this doc", "#FFFFFF"),
    ]
    stat_html = "".join(
        f'<div class="rounded-md border px-3 py-2.5" '
        f'style="border-color:rgba(255,255,255,0.18);background:rgba(255,255,255,0.04)">'
        f'<div class="font-num" style="color:{c};font-size:22px;line-height:1">{v}</div>'
        f'<div class="font-cta mt-1.5" style="color:#C8C8C8;font-size:9px">{e(l)}</div></div>'
        for v, l, c in cards)

    jump = []
    idx = 2
    for sid, label in SECTIONS[1:]:
        if _section_has_data(data, sid):
            jump.append(f'<a href="#{sid}" class="font-cta rounded-md border px-2.5 py-1 transition-colors '
                        f'hover:bg-white/10" style="color:#FFFFFF;border-color:rgba(255,255,255,0.2)">'
                        f'{idx:02d} · {e(label)}</a>')
        idx += 1

    kick = e(hero.get("kicker", "Competitive Intelligence"))
    date_label = e(data.get("meta", {}).get("date_label", ""))
    return f'''<section id="overview" class="relative px-6 pb-12 pt-16 md:px-12 md:pb-16 md:pt-20" style="background:linear-gradient(135deg, #245AE2 0%, #01194C 100%)">
  <div class="mx-auto w-full max-w-[1296px]">
    <div class="grid items-end gap-10 md:grid-cols-12">
      <div class="md:col-span-8">
        <div class="flex items-center gap-3">
          <span class="inline-block h-2.5 w-2.5 rounded-full" style="background:#D6F549"></span>
          <span class="font-cta" style="color:#D6F549;letter-spacing:0.15em">{kick}</span>
          <span class="font-cta" style="color:#C8C8C8">{date_label}</span>
        </div>
        <h1 class="mt-5 text-display-xl md:text-display-2xl" style="color:#FFFFFF;letter-spacing:-0.02em;line-height:1.05">{title}</h1>
        <p class="mt-5 text-display-xs" style="color:#FFFFFF;max-width:640px">{e(hero.get("tagline", ""))}</p>
        <p class="mt-4 text-p-md" style="color:#C8C8C8;max-width:600px">{e(hero.get("subtitle", ""))}</p>
      </div>
      <div class="md:col-span-4">
        <div class="grid grid-cols-2 gap-2">{stat_html}</div>
      </div>
    </div>
    <div class="mt-10 flex flex-wrap items-center gap-2 border-t pt-5" style="border-color:rgba(214,245,73,0.2)">
      <span class="font-cta mr-2" style="color:#D6F549">Jump to</span>
      {"".join(jump)}
    </div>
  </div>
</section>'''


def render_tldr(data):
    t = data["tldr"]
    n_lead = len(data.get("ahead", {}).get("items", []))
    n_close = len(data.get("closeable", {}).get("items", []))
    n_dec = len(data.get("decisions", {}).get("items", []))
    mini = (stat_card(n_lead, "Ahead", "#0F9D58", "#DFF6E8", "#34D399")
            + stat_card(n_close, "Closeable", "#245AE2", "#D3DEF9", "#A7BDF3")
            + stat_card(n_dec, "Decide", "#D97706", "#FEF3C7", "#FBBF24"))
    paras = "".join(f'<p class="{"" if i == 0 else "mt-4 "}text-p-lg" style="color:#4D4D4D">{raw(p)}</p>'
                    for i, p in enumerate(t.get("paragraphs", [])))
    chips = ""
    for c in t.get("chips", []):
        tone = CHIP_TONE.get(c.get("tone", "blue"), CHIP_TONE["blue"])
        icon = ICONS.get(c.get("icon", "check"), ICONS["check"])
        chips += f'''<div class="rounded-xl border p-4" style="border-color:{tone['bd']};background:{tone['bg']}">
  <div class="flex items-center gap-2" style="color:{tone['fg']}">
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{icon}</svg>
    <span class="font-cta">{e(c.get("title", ""))}</span>
  </div>
  <p class="mt-2 text-p-sm" style="color:#2F2F2F">{e(c.get("body", ""))}</p>
</div>'''
    return f'''<section id="tldr" class="px-6 py-14 md:px-12">
  <div class="mx-auto max-w-[1296px]">
    <div class="grid items-end gap-6 md:grid-cols-12">
      <div class="md:col-span-7">
        {kicker(t.get("lead_in", "The honest read"))}
        <h2 class="mt-3 text-display-md md:text-display-lg" style="color:#2F2F2F">The picture, in one paragraph</h2>
        <p class="mt-2 text-p-md md:text-p-lg" style="color:#4D4D4D;max-width:760px">{e(t.get("sub", ""))}</p>
      </div>
      <div class="md:col-span-5"><div class="grid grid-cols-3 gap-2">{mini}</div></div>
    </div>
    <div class="mt-8 grid gap-6 lg:grid-cols-12">
      <div class="rounded-xl border bg-white p-7 lg:col-span-8" style="border-color:#E2E8F0">{paras}</div>
      <div class="grid gap-4 lg:col-span-4">{chips}</div>
    </div>
  </div>
</section>'''


def _player_card(entry, data, is_product):
    if is_product:
        p = data["product"]
        chip = (f'<span class="font-cta inline-flex rounded-md px-2 py-1" '
                f'style="background:#245AE2;color:#FFFFFF">{e(p.get("category_label",""))}</span>'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" '
                f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                f'stroke-linejoin="round" aria-hidden="true" style="color:#245AE2">{ICONS["arrow"]}</svg>')
        card_style = "border-color:#245AE2;border-width:2px"
        h3 = f'<h3 class="mt-4 text-display-sm" style="color:#245AE2">{e(p["name"])}</h3>'
        src = p
    else:
        chip = (f'<span class="font-cta inline-flex rounded-md px-2 py-1" '
                f'style="background:#F7FDDB;color:#80932C">{e(entry.get("category_label",""))}</span>')
        card_style = "border-color:#E2E8F0;border-width:1px"
        h3 = f'<h3 class="mt-4 text-display-sm" style="color:#2F2F2F">{e(entry["name"])}</h3>'
        src = entry

    name = src["name"]
    pos, total = coverage_count(data, name)
    foot = list(src.get("footprint", []))[:2]
    foot.append({"label": "Coverage", "value": f"{coverage_pct(data, name)}%"})
    foot_html = "".join(
        f'<div><div class="font-cta" style="color:#999;font-size:9px">{e(f["label"])}</div>'
        f'<div class="font-num mt-0.5" style="color:#111;font-size:13px">{e(f["value"])}</div></div>'
        for f in foot)
    return f'''<div class="flex flex-col rounded-xl border bg-white p-6" style="{card_style}">
  <div class="flex items-center justify-between">{chip}</div>
  {h3}
  <p class="mt-3 italic text-p-sm" style="color:#666">"{e(src.get("money_question",""))}"</p>
  <div class="mt-3 pt-3 border-t" style="border-color:#E2E8F0">
    <div class="font-cta mb-1.5" style="color:#999;font-size:10px">Signature</div>
    <p class="text-p-sm font-semibold" style="color:#111">{e(src.get("signature",""))}</p>
  </div>
  <div class="mt-4 grid grid-cols-3 gap-2 border-t pt-3" style="border-color:#E2E8F0">{foot_html}</div>
</div>'''


def render_players(data):
    cards = "".join(_player_card(c, data, False) for c in data.get("competitors", []))
    cards += _player_card(None, data, True)
    cols = "lg:grid-cols-3" if (len(data.get("competitors", [])) + 1) <= 3 else "lg:grid-cols-4"
    return f'''<section id="players" class="border-y px-6 py-14 md:px-12" style="background:#F8FAFD;border-color:#E2E8F0">
  <div class="mx-auto max-w-[1296px]">
    <div class="grid items-end gap-6 md:grid-cols-12">
      {section_head("The three players", "What each product actually is",
                    "One sentence on category, the money question they answer, their signature feature, plus a quick footprint row.")}
    </div>
    <div class="mt-8 grid gap-5 {cols}">{cards}</div>
  </div>
</section>'''


def _coverage_chart(data):
    plats = platforms(data)
    rows = []
    ci = 0
    pct_vals = {name: coverage_pct(data, name) for name, _, _ in plats}
    maxpct = max(pct_vals.values()) or 1
    for name, is_prod, short in plats:
        pct = pct_vals[name]
        width = round(100 * pct / maxpct)  # scale bars so the leader fills the track
        if is_prod:
            fill, stroke = PRODUCT_BAR["fill"], PRODUCT_BAR["stroke"]
            bar_style = f"background:{fill};border:1px solid {stroke}"
            lab = "#111"
        else:
            fill = COMPETITOR_BAR[ci % len(COMPETITOR_BAR)]
            ci += 1
            bar_style = f"background:{fill}"
            lab = "#111"
        rows.append(f'''<div class="flex items-center gap-3">
  <div class="font-num" style="width:130px;text-align:right;color:#2F2F2F;font-size:14px;flex-shrink:0">{e(short)}</div>
  <div style="flex:1;min-width:0"><div style="height:32px;border-radius:0 4px 4px 0;{bar_style};width:{width}%;min-width:40px"></div></div>
  <div class="font-num" style="color:#111;font-size:20px;font-weight:600;width:54px;flex-shrink:0">{pct}%</div>
</div>''')
    return f'<div class="mt-5 flex flex-col gap-4" style="min-height:200px;justify-content:center">{"".join(rows)}</div>'


def _glance_notes(data):
    notes = data.get("matrix", {}).get("glance_notes")
    plats = platforms(data)
    if not notes:
        # Auto-generate from coverage if the author didn't supply notes.
        notes = []
        for name, is_prod, short in plats:
            pos, total = coverage_count(data, name)
            notes.append({"name": short, "count": f"{pos}/{total}",
                          "title": f"{short}: {coverage_pct(data, name)}% coverage",
                          "body": ""})
    badge_colors = ["#D3DEF9:#163688", "#01194C:#FFFFFF", "#F7FDDB:#80932C", "#EDE9FE:#5B21B6"]
    out = []
    for i, n in enumerate(notes):
        bg, fg = badge_colors[i % len(badge_colors)].split(":")
        out.append(f'''<div class="flex items-start gap-3 rounded-xl border bg-white p-4" style="border-color:#E2E8F0">
  <div class="rounded-md px-2 py-1 font-num" style="background:{bg};color:{fg};font-size:18px">{e(n.get("count",""))}</div>
  <div class="min-w-0 flex-1">
    <div class="text-p-md font-semibold" style="color:#2F2F2F">{e(n.get("title",""))}</div>
    <div class="mt-1 text-p-sm" style="color:#4D4D4D">{e(n.get("body",""))}</div>
  </div>
</div>''')
    out.append('<div class="rounded-xl border-2 border-dashed p-3 text-p-sm italic" '
               'style="border-color:#E2E8F0;color:#666">Coverage is breadth, not advantage. '
               'See “Where we lead” for the fights that actually matter.</div>')
    return "".join(out)


def _matrix_table(data):
    plats = platforms(data)
    headers = '<th class="font-cta border-b px-4 py-2.5 text-left" style="border-color:#E2E8F0;color:#666;min-width:220px">Capability</th>'
    for name, is_prod, short in plats:
        w = "140px" if is_prod else "110px"
        headers += (f'<th class="font-cta border-b px-4 py-2.5 text-left" '
                    f'style="border-color:#E2E8F0;color:#666;width:{w}">{e(short)}</th>')
    headers += '<th class="font-cta border-b px-4 py-2.5 text-left" style="border-color:#E2E8F0;color:#666;min-width:320px">Reality</th>'

    rows = ""
    for cap in data.get("matrix", {}).get("capabilities", []):
        cells = f'<td class="border-b px-4 py-3 text-p-md" style="border-color:#E2E8F0;color:#111;font-weight:600">{e(cap["name"])}</td>'
        for name, is_prod, short in plats:
            v = cap.get("verdicts", {}).get(name, {})
            cells += (f'<td class="border-b px-4 py-3" style="border-color:#E2E8F0">'
                      f'{status_pill(v.get("status", "unknown"))}</td>')
        cells += (f'<td class="border-b px-4 py-3 text-p-sm" style="border-color:#E2E8F0;color:#4D4D4D">'
                  f'{e(cap.get("reality",""))}</td>')
        rows += f'<tr class="transition-colors hover:bg-[#F7FDDB]/40">{cells}</tr>'

    legend = "".join(
        f'<span class="font-cta inline-flex items-center gap-1.5 rounded-md border transition-transform '
        f'hover:scale-105 px-2.5 py-1" style="color:{s["fg"]};background:{s["bg"]};border-color:{s["bd"]};font-size:12px">'
        f'<span class="inline-block h-1.5 w-1.5 rounded-full" style="background:{s["fg"]}"></span>{e(s["label"])}</span>'
        for s in STATUS.values())

    return f'''<div class="flex flex-wrap items-center gap-2 mb-4">
  <span class="font-cta mr-1" style="color:#666">Legend</span>{legend}
</div>
<div class="rounded-xl border" style="border-color:#E2E8F0">
  <div class="overflow-x-auto">
    <table class="w-full border-collapse" style="min-width:980px">
      <thead class="bg-white"><tr>{headers}</tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>'''


def render_matrix(data):
    caps = data.get("matrix", {}).get("capabilities", [])
    n = len(caps)
    n_status = len({v.get("status", "unknown")
                    for cap in caps for v in cap.get("verdicts", {}).values()}) or 1
    stats = (stat_card(n, "Capabilities") + stat_card(n_status, "Status types")
             + stat_card(len(platforms(data)), "Platforms"))
    return f'''<section id="matrix" class="px-6 py-14 md:px-12">
  <div class="mx-auto max-w-[1296px]">
    <div class="grid items-end gap-6 md:grid-cols-12">
      {section_head("Section 04", "Feature matrix", "Glance at the headline first, then read the row-by-row breakdown.", "matrix")}
      <div class="md:col-span-5"><div class="grid grid-cols-3 gap-2">{stats}</div></div>
    </div>
    <div class="mt-8 grid gap-6 lg:grid-cols-12">
      <div class="lg:col-span-7">
        <span class="font-cta inline-flex rounded-md px-2 py-1" style="background:#D3DEF9;color:#245AE2">The picture in one chart</span>
        <h3 class="mt-3 text-display-sm" style="color:#2F2F2F">Feature coverage at a glance</h3>
        <p class="mt-2 text-p-md" style="color:#4D4D4D">Counting <strong style="color:#111">Owned</strong> + <strong style="color:#111">Ahead</strong> only. Higher is broader, not better.</p>
        {_coverage_chart(data)}
      </div>
      <div class="grid gap-3 lg:col-span-5">{_glance_notes(data)}</div>
    </div>
    <div class="mt-12 border-t pt-10" style="border-color:#E2E8F0">
      <div class="mb-6">
        <span class="font-cta inline-flex rounded-md px-2 py-1" style="background:#F7FDDB;color:#80932C">The detail</span>
        <h3 class="mt-3 text-display-sm" style="color:#2F2F2F">Row-by-row breakdown</h3>
        <p class="mt-2 text-p-md" style="color:#4D4D4D">Every capability, every platform, plus a one-line reality check on each.</p>
      </div>
      {_matrix_table(data)}
    </div>
  </div>
</section>'''


def render_lead(data):
    a = data["ahead"]
    items = a.get("items", [])
    n = len(items)
    stats = (stat_card(n, "Moats", "#0F9D58", "#DFF6E8", "#34D399")
             + stat_card(0, "Competitors match")
             + stat_card("100%", "Built", "#245AE2", "#D3DEF9", "#A7BDF3"))
    cards = ""
    for i, it in enumerate(items, 1):
        cards += f'''<div class="flex flex-col rounded-xl border bg-white p-5" style="border-color:#E2E8F0">
  <div class="flex items-center justify-between">
    <span class="font-num text-display-sm" style="color:#245AE2">{i:02d}</span>
    <span class="font-cta rounded-md border px-1.5 py-0.5" style="border-color:#0F9D58;color:#0F9D58;background:#DFF6E8;font-size:10px">{e(it.get("label","Ahead"))}</span>
  </div>
  <h3 class="mt-3 text-display-xs" style="color:#2F2F2F;font-size:18px">{e(it["title"])}</h3>
  <p class="mt-2 text-p-sm" style="color:#666">{e(it.get("body",""))}</p>
</div>'''
    grid_cols = "lg:grid-cols-5" if n >= 5 else f"lg:grid-cols-{max(n,1)}"
    return f'''<section id="lead" class="px-6 py-14 md:px-12" style="background:#F4F3F2">
  <div class="mx-auto max-w-[1296px]">
    <div class="grid items-end gap-6 md:grid-cols-12">
      {section_head("Section 05 · Bucket 1", "Where we are genuinely ahead", a.get("sub", ""))}
      <div class="md:col-span-5"><div class="grid grid-cols-3 gap-2">{stats}</div></div>
    </div>
    <div class="mt-8 grid gap-4 md:grid-cols-3 {grid_cols}">{cards}</div>
  </div>
</section>'''


def _scatter(items):
    """CSS-positioned effort-vs-value scatter. x=effort (low→left), y=value (high→top)."""
    pos = {"low": 18, "med": 50, "medium": 50, "high": 82}
    dots = ""
    seen = {}
    for i, it in enumerate(items, 1):
        x = pos.get(str(it.get("effort_level", "med")).lower(), 50)
        yv = pos.get(str(it.get("value", "med")).lower(), 50)
        y = 100 - yv  # invert: high value near top
        key = (x, y)
        seen[key] = seen.get(key, 0) + 1
        off = (seen[key] - 1) * 7
        dots += (f'<div style="position:absolute;left:calc({x}% + {off}px);top:calc({y}% + {off}px);'
                 f'transform:translate(-50%,-50%);width:24px;height:24px;border-radius:9999px;'
                 f'background:#245AE2;border:2px solid #FFFFFF;color:#FFFFFF;display:flex;'
                 f'align-items:center;justify-content:center;font-size:11px;font-weight:600;'
                 f'font-family:var(--font-geist)">{i}</div>')
    return f'''<div style="position:relative;height:240px;border:1px solid #E2E8F0;border-radius:12px;background:#FFFFFF;margin-top:12px">
  <div class="font-cta" style="position:absolute;left:8px;top:8px;color:#999;font-size:9px;letter-spacing:0.1em">HIGH VALUE</div>
  <div class="font-cta" style="position:absolute;left:8px;bottom:8px;color:#999;font-size:9px;letter-spacing:0.1em">LOW VALUE</div>
  <div class="font-cta" style="position:absolute;right:8px;bottom:8px;color:#999;font-size:9px;letter-spacing:0.1em">HIGH EFFORT</div>
  <div class="font-cta" style="position:absolute;left:8px;bottom:24px;color:#245AE2;font-size:9px;letter-spacing:0.1em">↖ SHIP FIRST</div>
  {dots}
</div>'''


def render_closeable(data):
    c = data["closeable"]
    items = c.get("items", [])
    n = len(items)
    n_high = sum(1 for it in items if str(it.get("priority", "")).upper() == "HIGH")
    stats = (stat_card(n, "Gaps", "#245AE2", "#D3DEF9", "#A7BDF3")
             + stat_card(n_high, "High priority", "#245AE2", "#D3DEF9", "#A7BDF3")
             + stat_card(len(items), "Items"))
    rows = ""
    for it in items:
        pr = str(it.get("priority", "MEDIUM")).upper()
        if pr == "HIGH":
            pc = ("#245AE2", "#D3DEF9", "#245AE2")
        elif pr == "LOW":
            pc = ("#666666", "#F4F3F2", "#CCCCCC")
        else:
            pc = ("#80932C", "#F7FDDB", "#80932C")
        rows += f'''<tr class="transition-colors hover:bg-[#F7FDDB]/40">
  <td class="border-b px-3 py-3" style="border-color:#E2E8F0;color:#111">
    <div class="text-p-md font-semibold">{e(it["title"])}</div>
    <div class="mt-1 text-p-sm" style="color:#4D4D4D">{e(it.get("desc",""))}</div>
  </td>
  <td class="border-b px-3 py-3 font-num align-top" style="border-color:#E2E8F0;color:#111;white-space:nowrap;font-size:14px">{e(it.get("effort",""))}</td>
  <td class="border-b px-3 py-3 align-top" style="border-color:#E2E8F0">
    <span class="font-cta inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5" style="color:{pc[0]};background:{pc[1]};border-color:{pc[2]};font-size:10px">
      <span class="inline-block h-1.5 w-1.5 rounded-full" style="background:{pc[0]}"></span>{e(pr)}</span>
  </td>
</tr>'''
    legend_list = ""
    for i, it in enumerate(items, 1):
        legend_list += f'''<div class="flex items-center gap-2.5 rounded-md border px-2.5 py-1.5" style="border-color:#E2E8F0;background:#F8FAFD">
  <span class="flex h-5 w-5 shrink-0 items-center justify-center rounded-full font-num" style="background:#245AE2;color:#FFFFFF;font-size:11px">{i}</span>
  <span class="text-p-sm flex-1" style="color:#2F2F2F;font-size:12px">{e(it["title"])}</span>
  <span class="font-num" style="color:#666;font-size:11px">{e(it.get("effort",""))}</span>
</div>'''
    return f'''<section id="closeable" class="px-6 py-14 md:px-12">
  <div class="mx-auto max-w-[1296px]">
    <div class="grid items-end gap-6 md:grid-cols-12">
      {section_head("Section 06 · Bucket 2", "Closeable in one quarter", c.get("sub", ""))}
      <div class="md:col-span-5"><div class="grid grid-cols-3 gap-2">{stats}</div></div>
    </div>
    <div class="mt-8 grid gap-6 lg:grid-cols-12">
      <div class="lg:col-span-7">
        <div class="overflow-hidden rounded-xl border" style="border-color:#E2E8F0">
          <table class="w-full border-collapse">
            <thead class="bg-white"><tr>
              <th class="font-cta border-b px-3 py-2.5 text-left" style="border-color:#E2E8F0;color:#666">Gap</th>
              <th class="font-cta border-b px-3 py-2.5 text-left" style="border-color:#E2E8F0;color:#666">Effort</th>
              <th class="font-cta border-b px-3 py-2.5 text-left" style="border-color:#E2E8F0;color:#666">Priority</th>
            </tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
      </div>
      <div class="lg:col-span-5">
        <span class="font-cta inline-flex rounded-md px-2 py-1" style="background:#D3DEF9;color:#245AE2">Which to ship first?</span>
        <h3 class="mt-3 text-display-sm" style="color:#2F2F2F">Effort vs. strategic value</h3>
        <p class="mt-2 text-p-sm" style="color:#666">Upper-left = high value, low effort = ship first.</p>
        {_scatter(items)}
        <div class="mt-3 grid gap-1.5">{legend_list}</div>
      </div>
    </div>
  </div>
</section>'''


def render_decisions(data):
    d = data["decisions"]
    items = d.get("items", [])
    cards = ""
    for i, it in enumerate(items, 1):
        cards += f'''<div class="rounded-xl border p-5" style="border-color:#344770;background:#0E245A">
  <div class="flex items-baseline gap-3">
    <span class="font-num" style="color:#D6F549;font-size:22px">{i:02d}</span>
    <h3 class="text-display-xs" style="color:#FFFFFF">{e(it["title"])}</h3>
  </div>
  <p class="mt-3 text-p-sm" style="color:#FFFFFF">{e(it.get("body",""))}</p>
</div>'''
    word = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six"}.get(len(items), str(len(items)))
    return f'''<section id="decisions" class="px-6 py-12 md:px-12" style="background:#01194C">
  <div class="mx-auto max-w-[1296px]">
    <div class="max-w-[760px]">
      {kicker("Section 07", dark=True)}
      <h2 class="mt-3 text-display-lg" style="color:#FFFFFF">{word} open question{"s" if len(items)!=1 else ""}</h2>
      <p class="mt-2 text-p-md" style="color:#C8C8C8">{e(d.get("sub",""))}</p>
    </div>
    <div class="mt-8 grid gap-4 md:grid-cols-2">{cards}</div>
  </div>
</section>'''


def render_positioning(data):
    p = data["positioning"]
    stats = ""
    tone_map = {"blue": ("#245AE2", "#D3DEF9", "#A7BDF3"), "green": ("#0F9D58", "#DFF6E8", "#34D399"),
                "amber": ("#D97706", "#FEF3C7", "#FBBF24")}
    for s in p.get("stats", []):
        fg, bg, bd = tone_map.get(s.get("tone", "blue"), tone_map["blue"])
        stats += stat_card(s.get("value", ""), s.get("label", ""), fg, bg, bd)
    paras = ""
    for i, para in enumerate(p.get("paragraphs", [])):
        cls = "text-display-xs" if i == 0 else "mt-4 text-p-lg"
        style = "color:#2F2F2F;line-height:1.5" if i == 0 else "color:#4D4D4D"
        paras += f'<p class="{cls}" style="{style}">{raw(para)}</p>'
    pull = ""
    if p.get("pullquote"):
        pull = (f'<p class="mt-3 rounded-md border-l-4 bg-[#F8FAFD] px-5 py-4 text-display-xs" '
                f'style="border-left-color:#245AE2;color:#245AE2">{e(p["pullquote"])}</p>')
    closing = f'<p class="mt-4 text-p-md" style="color:#4D4D4D">{raw(p["closing"])}</p>' if p.get("closing") else ""

    checklists = ""
    for cl in p.get("checklists", []):
        green = cl.get("tone") == "green"
        box_style = "border-color:#0F9D58;background:#DFF6E8" if green else "border-color:#E2E8F0"
        title_fg = "#0F9D58" if green else "#666"
        li_fg = "#0F9D58" if green else "#2F2F2F"
        marker = cl.get("marker", "→")
        mc = cl.get("marker_color", "#0F9D58" if green else "#245AE2")
        lis = "".join(f'<li class="flex gap-2"><span style="color:{mc}">{e(marker)}</span>{e(x)}</li>'
                      for x in cl.get("items", []))
        checklists += f'''<div class="rounded-xl border p-4" style="{box_style}">
  <div class="font-cta" style="color:{title_fg};font-size:10px">{e(cl.get("title",""))}</div>
  <ul class="mt-2 space-y-1 text-p-sm" style="color:{li_fg}">{lis}</ul>
</div>'''

    return f'''<section id="positioning" class="px-6 py-14 md:px-12">
  <div class="mx-auto max-w-[1296px]">
    <div class="grid items-end gap-6 md:grid-cols-12">
      {section_head("Section 08 · The thesis", "The positioning that's actually true", p.get("sub", ""))}
      <div class="md:col-span-5"><div class="grid grid-cols-3 gap-2">{stats}</div></div>
    </div>
    <div class="mt-8 grid gap-6 lg:grid-cols-12">
      <div class="rounded-xl border p-7 lg:col-span-8" style="border-color:#E2E8F0;background:#FFFFFF">
        {paras}{pull}{closing}
      </div>
      <div class="grid gap-3 lg:col-span-4">{checklists}</div>
    </div>
    {_sources_block(data)}
  </div>
</section>'''


def _sources_block(data):
    src = data.get("sources", {})
    ext = src.get("external", [])
    intern = src.get("internal", [])
    if not ext and not intern:
        return ""
    arrow = ('<svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" '
             'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
             'stroke-linejoin="round" aria-hidden="true" style="color:#999">' + ICONS["arrow"] + '</svg>')
    ext_html = ""
    for s in ext:
        ext_html += (f'<li class="flex gap-1.5"><span>·</span>'
                     f'<a href="{e(s.get("url","#"))}" target="_blank" rel="noopener noreferrer" '
                     f'class="inline-flex items-center gap-1 underline decoration-dotted underline-offset-2 '
                     f'transition-colors hover:text-[#245AE2]" style="color:#4D4D4D">{e(s.get("label",s.get("url","")))}'
                     f'{arrow}</a></li>')
    intern_html = "".join(
        f'<li class="flex gap-1.5"><span>·</span>'
        f'<code style="font-family:var(--font-geist);font-size:12px;color:#4D4D4D">{e(x)}</code></li>'
        for x in intern)
    cols = ""
    if ext_html:
        cols += (f'<div><div class="font-cta" style="color:#666;font-size:10px">External sources</div>'
                 f'<ul class="mt-2 space-y-1 text-p-sm" style="color:#666">{ext_html}</ul></div>')
    if intern_html:
        cols += (f'<div><div class="font-cta" style="color:#666;font-size:10px">Internal sources</div>'
                 f'<ul class="mt-2 space-y-1 text-p-sm" style="color:#666">{intern_html}</ul></div>')
    return (f'<hr class="mt-10 border-0" style="border-top:1px solid #E2E8F0">'
            f'<div class="mt-6 grid gap-4 md:grid-cols-2">{cols}</div>')


# --------------------------------------------------------------------------- scaffold

def _section_has_data(data, sid):
    if sid == "overview":
        return True
    if sid == "tldr":
        return bool(data.get("tldr"))
    if sid == "players":
        return bool(data.get("competitors")) or bool(data.get("product"))
    if sid == "matrix":
        return bool(data.get("matrix", {}).get("capabilities"))
    if sid == "lead":
        return bool(data.get("ahead", {}).get("items"))
    if sid == "closeable":
        return bool(data.get("closeable", {}).get("items"))
    if sid == "decisions":
        return bool(data.get("decisions", {}).get("items"))
    if sid == "positioning":
        return bool(data.get("positioning"))
    return False


RENDERERS = {
    "overview": render_overview, "tldr": render_tldr, "players": render_players,
    "matrix": render_matrix, "lead": render_lead, "closeable": render_closeable,
    "decisions": render_decisions, "positioning": render_positioning,
}


def sidebar(data, active_sections):
    items = ""
    for i, (sid, label) in enumerate(SECTIONS, 1):
        if sid not in active_sections:
            continue
        items += f'''<a href="#{sid}" class="font-cta flex items-center gap-2 border-l-2 py-2 pl-3 pr-2 transition-colors" data-nav="{sid}" style="border-color:transparent;color:#666666;background:transparent">
  <span style="color:#CCC;font-family:var(--font-geist)">{i:02d}</span><span>{e(label)}</span>
</a>'''
    return f'''<aside class="no-print fixed left-0 top-12 z-30 h-[calc(100vh-3rem)] w-56 shrink-0 border-r bg-white px-3 py-5 transition-transform md:sticky md:translate-x-0 -translate-x-full" id="sidebar" style="border-color:#E2E8F0">
  <div class="font-cta mb-3 px-3" style="color:#999;font-size:10px">Sections · {len(active_sections)}</div>
  <nav class="flex flex-col">{items}</nav>
  <div class="mt-6 px-1 font-cta" style="color:#CCC;font-size:9px">↑ ↓ to navigate</div>
</aside>'''


SCROLL_JS = """
(function(){
  var bar=document.getElementById('progress');
  var navlinks=[].slice.call(document.querySelectorAll('[data-nav]'));
  var ids=navlinks.map(function(a){return a.getAttribute('data-nav');});
  function onScroll(){
    var h=document.documentElement;
    var pct=(h.scrollTop)/((h.scrollHeight-h.clientHeight)||1)*100;
    if(bar)bar.style.width=pct+'%';
    var cur=ids[0],mid=window.innerHeight*0.35;
    ids.forEach(function(id){var el=document.getElementById(id);if(el&&el.getBoundingClientRect().top<=mid)cur=id;});
    navlinks.forEach(function(a){
      var on=a.getAttribute('data-nav')===cur;
      a.style.borderColor=on?'#245AE2':'transparent';
      a.style.color=on?'#245AE2':'#666666';
      a.style.background=on?'#F8FAFD':'transparent';
    });
  }
  document.addEventListener('scroll',onScroll,{passive:true});onScroll();
  var t=document.getElementById('navToggle');var sb=document.getElementById('sidebar');
  if(t&&sb)t.addEventListener('click',function(){sb.classList.toggle('-translate-x-full');});
})();
"""


def build(data):
    base_css = BASE_CSS.read_text(encoding="utf-8") if BASE_CSS.exists() else ""
    meta = data.get("meta", {})
    org = meta.get("org", "")
    p = data["product"]
    comp_names = [c.get("short_name", c["name"]) for c in data.get("competitors", [])]
    title = f'{p["name"]} vs ' + " vs ".join(comp_names) if comp_names else p["name"]
    if org:
        title += f" · {org}"
    desc = data.get("hero", {}).get("tagline", "")

    active = [sid for sid, _ in SECTIONS if _section_has_data(data, sid)]
    body_sections = "\n".join(RENDERERS[sid](data) for sid in active)

    # header live stats
    n_lead = len(data.get("ahead", {}).get("items", []))
    n_close = len(data.get("closeable", {}).get("items", []))
    n_dec = len(data.get("decisions", {}).get("items", []))
    footer_left = " · ".join(x for x in [org, p["name"]] if x)
    footer_right_bits = [meta.get("date_label", "")]
    if meta.get("author"):
        footer_right_bits.append("prepared by " + meta["author"])
    footer_right = " · ".join(x for x in footer_right_bits if x)

    return f'''<!DOCTYPE html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="author" content="{e(org)}">
<style>{base_css}</style>
{FONTS_LINK}
</head><body>
<div class="min-h-screen bg-white" style="color:#2F2F2F">
  <div class="no-print fixed left-0 right-0 top-0 z-50 h-0.5">
    <div id="progress" class="h-full transition-[width]" style="width:0%;background:#245AE2"></div>
  </div>
  <header class="no-print sticky top-0 z-40 flex h-12 items-center justify-between border-b bg-white px-4 md:px-6" style="border-color:#E2E8F0">
    <div class="flex items-center gap-3">
      <button id="navToggle" class="md:hidden" aria-label="Toggle navigation">
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16"></path><path d="M4 12h16"></path><path d="M4 19h16"></path></svg>
      </button>
      <div class="font-display text-[16px] font-semibold tracking-tight">{e(org or p["name"])}</div>
      <span class="hidden text-p-sm md:inline" style="color:#666;font-size:12px">{e(p["name"])} / Competitive Analysis</span>
    </div>
    <div class="hidden items-center gap-4 md:flex">
      <div class="flex items-baseline gap-1.5"><span class="font-num" style="color:#0F9D58;font-size:16px">{n_lead}</span><span class="font-cta" style="color:#666;font-size:10px">ahead</span></div>
      <div class="flex items-baseline gap-1.5"><span class="font-num" style="color:#245AE2;font-size:16px">{n_close}</span><span class="font-cta" style="color:#666;font-size:10px">closeable</span></div>
      <div class="flex items-baseline gap-1.5"><span class="font-num" style="color:#D97706;font-size:16px">{n_dec}</span><span class="font-cta" style="color:#666;font-size:10px">decisions</span></div>
    </div>
  </header>
  <div class="flex">
    {sidebar(data, active)}
    <main class="min-w-0 flex-1">
      {body_sections}
      <footer class="flex h-14 items-center justify-between px-6 md:px-12" style="background:#121317">
        <div class="text-p-sm" style="color:#FFFFFF;font-family:var(--font-manrope)">{e(footer_left)}</div>
        <span class="inline-block h-2 w-2 rounded-full" style="background:#D6F549"></span>
        <div class="font-cta" style="color:#C8C8C8">{e(footer_right)}</div>
      </footer>
    </main>
  </div>
</div>
<script>{SCROLL_JS}</script>
</body></html>'''


def main():
    ap = argparse.ArgumentParser(description="Render a competitive-analysis page from data.json")
    ap.add_argument("data", help="path to data.json")
    ap.add_argument("-o", "--output", help="output html path (default: <product>-comparison.html)")
    args = ap.parse_args()

    data = json.loads(pathlib.Path(args.data).read_text(encoding="utf-8"))
    if "product" not in data or "name" not in data.get("product", {}):
        sys.exit("data.json must include product.name")

    html_out = build(data)
    if args.output:
        out = pathlib.Path(args.output)
    else:
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in data["product"]["name"]).strip("-")
        out = pathlib.Path(f"{slug}-comparison.html")
    out.write_text(html_out, encoding="utf-8")
    print(f"wrote {out}  ({len(html_out):,} bytes, {len([s for s,_ in SECTIONS if _section_has_data(data,s)])} sections)")


if __name__ == "__main__":
    main()
