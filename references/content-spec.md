# Content spec & research method

The "what goes in the page and how to ground it" reference. The design lives in
[design-system.md](design-system.md) and the renderer ([../scripts/build_page.py](../scripts/build_page.py));
this file is about the **content** and the **research that backs it**. A full, valid instance is
[example-data.json](example-data.json) — when in doubt, copy its shape.

The value of this page comes from being **honest and sourced**. A page full of invented checkmarks
is worse than useless — it gets someone burned in a sales call or a board meeting. So:
**no fabricated competitor data; every competitor claim traces to a real source; unknowns are
marked `unknown`, not guessed.**

---

## The `data.json` schema

Rendered by `python3 build_page.py data.json`. A section renders only if its data is present, so
you can omit sections you don't have. Fields marked HTML-ok may contain inline tags like
`<strong>`, `<em>`; everything else is plain text and auto-escaped.

```jsonc
{
  "meta": {
    "org": "Acme AI",                 // brand: header top-left + footer
    "date_label": "May 2026 · Internal",
    "author": "Jane Analyst",         // footer "prepared by"
    "analyst_note": "what wasn't verifiable, recency of research"   // optional, for your record
  },

  "product": {                        // OUR product (always rendered last / highlighted)
    "name": "Acme Outreach",
    "short_name": "Acme Outreach",  // used in matrix column + chart axis
    "category_label": "AI campaign execution",  // colored chip on the player card
    "money_question": "How do I ...?",           // the italic quote
    "signature": "Live run tracking + ...",      // signature capability line
    "footprint": [{"label":"Foundation","value":"Owned"}, {"label":"Edge","value":"Rigor"}],  // up to 2; coverage % auto-added
    "url": "https://..."              // optional
  },

  "competitors": [                    // one or more; rendered before our product
    {
      "name": "Jasper.ai",
      "short_name": "Jasper",
      "category_label": "Enterprise content",
      "money_question": "How do I ...?",
      "signature": "Jasper IQ + Grid + ...",
      "footprint": [{"label":"Customers","value":"Enterprise"}, {"label":"AI surface","value":"Content"}],
      "sources": ["https://www.jasper.ai/", "https://..."]   // REQUIRED: where the facts came from
    }
  ],

  "hero": {
    "kicker": "Competitive Intelligence",
    "tagline": "Where we lead, where we lag, and what to build next.",
    "subtitle": "A grounded analysis of ... in 2026."
  },

  "tldr": {
    "lead_in": "The honest read",
    "sub": "What's actually true once you read the matrix.",
    "paragraphs": ["HTML-ok topline ...", "HTML-ok ..."],
    "chips": [                        // up to 3 summary chips (right column)
      {"tone":"green","icon":"check","title":"Foundation owned","body":"..."},
      {"tone":"blue","icon":"trending","title":"Closeable in 1 qtr","body":"..."},
      {"tone":"amber","icon":"alert","title":"Need a call","body":"..."}
    ]
  },

  "matrix": {
    "glance_notes": [                 // optional "X leads on Y" cards; auto-generated from coverage if omitted
      {"count":"13/19","title":"Jasper leads on content","body":"..."}
    ],
    "capabilities": [                 // 6–12 rows is the sweet spot
      {
        "name": "Brand voice & guidelines",
        "reality": "One-line reality check shown in the Reality column.",
        "verdicts": {                 // one key per product AND per competitor, by exact `name`
          "Jasper.ai":      {"status":"owned",   "source":"https://..."},
          "Skai.io":        {"status":"gap",     "source":"https://..."},
          "Acme Outreach":{"status":"partial"}                       // our own verdicts need no source
        }
      }
    ]
  },

  "ahead": {                          // Section 05 — our moats
    "sub": "Engineering moats they don't trivially copy.",
    "items": [ {"title":"Reproducible campaigns", "body":"...", "label":"Ahead"} ]
  },

  "closeable": {                      // Section 06 — gaps closeable in a quarter
    "sub": "Each gap maps to existing services.",
    "items": [
      {"title":"AI search readiness score", "desc":"...", "effort":"2–3 wks",
       "priority":"HIGH|MEDIUM|LOW",
       "effort_level":"low|med|high", "value":"low|med|high"}   // position on the effort-vs-value scatter
    ]
  },

  "decisions": {                      // Section 07 — strategic open questions (dark section)
    "sub": "Not engineering tasks. Decided in a leadership room.",
    "items": [ {"title":"Bidding", "body":"..."} ]
  },

  "positioning": {                    // Section 08 — the thesis
    "sub": "The one paragraph to keep in your head.",
    "stats": [ {"tone":"blue","value":"Underneath","label":"Where we sit"} ],   // 3 small chips
    "paragraphs": ["HTML-ok (first one renders large) ...", "..."],
    "pullquote": "The positioning sentence in quotes.",
    "closing": "HTML-ok final paragraph.",            // optional
    "checklists": [                   // right column
      {"title":"To match Jasper", "marker":"→", "marker_color":"#245AE2", "items":["...", "..."]},
      {"title":"Already ours", "tone":"green", "marker":"✓", "items":["..."]}
    ]
  },

  "sources": {                        // the proof — always fill this
    "external": [ {"label":"Skai homepage", "url":"https://skai.io/"} ],
    "internal": [ "path/to/internal/doc.md" ]          // optional, rendered as <code>
  }
}
```

### Verdict statuses (the heart of the matrix)
| status    | color  | meaning                                              | counts toward coverage |
|-----------|--------|------------------------------------------------------|------------------------|
| `owned`   | green  | real, shipping capability                            | ✅ |
| `ahead`   | blue   | not just present — a genuine differentiator/lead     | ✅ |
| `partial` | amber  | exists but limited, gated, beta, or workaround-only  | ❌ |
| `gap`     | red    | not available                                        | ❌ |
| `unknown` | grey   | research could not establish the fact                | ❌ |

Coverage % = round(100 × (owned+ahead) / total capabilities), computed per platform. Don't author
it. Be honest about our own `partial`/`gap` rows — winning every row reads as marketing.

### chip icons / tones
`icon`: `check`, `trending`, `alert`. `tone` (chips & stats): `green`, `blue`, `amber`.

---

## Research method

You'll be given a product and competitor names. Work in this order:

1. **Pin down OUR product first.** Real capabilities from the user, a URL, or a repo. Never invent
   our own feature list. For internal/clean-room products, use only what the user shared.
2. **Research each competitor on the open web.** `WebSearch` → `WebFetch` their site, pricing page
   (tiers/gating; "contact sales" = enterprise-gated), docs/API (the honest source), and recent
   news/changelog/comparison posts. Record a URL for every fact. Prefer primary sources.
3. **Derive the feature list from reality**, not a generic checklist — the rows where our real
   strengths and the category's table-stakes intersect. Mix rows we win, tie, and lose.
4. **Be self-critical.** Put real gaps into `decisions` and into our own `partial`/`gap` verdicts.
5. **Mark unknowns.** If a fact isn't established after real searching, use `unknown` and note it in
   `meta.analyst_note`. Honesty beats coverage.

### Scaling depth
- Quick / rough cut → a few targeted searches per competitor, primary sources only.
- Thorough / deep → pricing + docs + recent news per competitor; corroborate each claimed gap with
  a second source. The `deep-research` skill is a fine engine if available.

## Tone
Plain, declarative, specific. "No run history" beats "limited campaign management." Quantify with a
source ("$49/seat/mo", "GA since 2023"). Never pair a competitor's name with an unsourced negative
claim — that's a credibility and legal risk. Match the user's tight, no-filler, no-fake-numbers style.
