// Competitor-analysis orchestration — the multi-agent fleet behind the /competitor skill.
// Implements ARCHITECTURE.md Phases A–E. Phase F (render) stays in the main loop because
// workflow scripts have no filesystem/shell — this returns a validated data.json object.
//
// Runs in TWO stages around the human approval gate (Gate 2):
//   args.stage = 'discover'  → Phase A (intake) + Phase B (discovery). Returns {productProfile, ranked, top2}.
//   args.stage = 'build'     → Phase C (research) + D (synthesis) + E (verify). Returns {data, report}.
//
// args (discover): { stage:'discover', product:{kind:'repo'|'url'|'doc'|'text', ref:string, notes?:string} }
// args (build):    { stage:'build', productProfile:{...}, competitors:[{name,url}], meta:{org,date_label,author}, skeptics?:number }

export const meta = {
  name: 'competitor-analysis',
  description: 'Research a product\'s top competitors and produce a verified competitive-analysis data set',
  phases: [
    { title: 'Intake' },
    { title: 'Discovery' },
    { title: 'Research' },
    { title: 'Synthesis' },
    { title: 'Verify' },
  ],
}

// Methodology/rules now live in each agent's definition (agents/*.md, installed via
// scripts/install-agents.sh). The workflow passes task + data and selects the agent by agentType.

// ----------------------------------------------------------------- research dimensions (Phase C)
const DIMENSIONS = [
  { key: 'pricing', focus: 'Pricing & packaging: tiers, what is free vs paid vs enterprise-gated ("contact sales" = gated), seat/usage limits, notable caps. PRIMARY source: the official pricing page.' },
  { key: 'features', focus: 'Core product & differentiators: headline capabilities, the signature feature, integrations, API/SDK, platform breadth. PRIMARY source: product/features pages + docs/API reference + changelog.' },
  { key: 'positioning', focus: 'Positioning & ICP: the category they claim, who they target, their value proposition and messaging, marquee customers. Source: homepage, about, case studies.' },
  { key: 'momentum', focus: 'Momentum & scale: funding, customer/logo counts, recent launches, trajectory and recency. Source: funding/press/news, earnings if public.' },
  { key: 'weaknesses', focus: 'Weaknesses & gaps: known limitations and recurring complaints. Capture each gap WITH a representative source. Source: G2/Capterra/TrustRadius reviews, Reddit/forums, support docs.' },
]

// ----------------------------------------------------------------- JSON schemas (structured output)
const PROFILE_PART = {
  type: 'object', additionalProperties: true,
  properties: {
    capabilities: { type: 'array', items: { type: 'string' }, description: 'Concrete things the product does, evidenced in the material' },
    category: { type: 'string' }, icp: { type: 'string' }, positioning: { type: 'string' },
    signals: { type: 'array', items: { type: 'string' }, description: 'Category keywords / competitor names hinted at, for later search' },
    notes: { type: 'string' },
  }, required: ['capabilities'],
}

const PRODUCT_PROFILE = {
  type: 'object', additionalProperties: true,
  properties: {
    name: { type: 'string' }, category: { type: 'string' }, icp: { type: 'string' },
    what_it_is: { type: 'string' }, positioning: { type: 'string' },
    signature: { type: 'string', description: 'The signature capability line for the player card' },
    money_question: { type: 'string', description: 'The core question a buyer is answering with this product' },
    capabilities: { type: 'array', items: { type: 'string' } },
    footprint: { type: 'array', items: { type: 'object', properties: { label: { type: 'string' }, value: { type: 'string' } } } },
    search_seeds: { type: 'array', items: { type: 'string' }, description: 'Queries/keywords to find competitors' },
  }, required: ['name', 'category', 'capabilities', 'search_seeds'],
}

const CANDIDATE_LIST = {
  type: 'object', additionalProperties: false,
  properties: {
    candidates: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          name: { type: 'string' }, url: { type: 'string' },
          why: { type: 'string', description: 'Why it competes with our product' },
          leadership_signals: { type: 'array', items: { type: 'string' }, description: 'Evidence of market leadership: funding, customers, analyst ranking, mindshare' },
          sources: { type: 'array', items: { type: 'string' } },
        }, required: ['name', 'why'],
      },
    },
  }, required: ['candidates'],
}

const RANKED = {
  type: 'object', additionalProperties: false,
  properties: {
    ranked: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          name: { type: 'string' }, url: { type: 'string' }, why: { type: 'string' },
          leadership_score: { type: 'number', description: '0-100 market-leadership score' },
          leadership_signals: { type: 'array', items: { type: 'string' } },
          sources: { type: 'array', items: { type: 'string' } },
        }, required: ['name', 'why', 'leadership_score'],
      },
    },
    top2: {
      type: 'array', maxItems: 2,
      items: { type: 'object', properties: { name: { type: 'string' }, url: { type: 'string' }, why: { type: 'string' } }, required: ['name', 'why'] },
    },
  }, required: ['ranked', 'top2'],
}

const FINDINGS = {
  type: 'object', additionalProperties: false,
  properties: {
    dimension: { type: 'string' },
    findings: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          claim: { type: 'string', description: 'A specific, falsifiable fact' },
          detail: { type: 'string' },
          source: { type: 'string', description: 'URL the claim was read from' },
          date: { type: 'string', description: 'publication/last-updated date of the source, if known' },
          tier: { type: 'string', enum: ['primary', 'aggregator', 'review', 'blog'], description: 'reliability: primary vendor page/docs > aggregator (G2/Crunchbase) > individual review > vendor blog' },
        }, required: ['claim', 'source'],
      },
    },
    unknowns: { type: 'array', items: { type: 'string' }, description: 'Things you could not establish' },
  }, required: ['dimension', 'findings'],
}

const COMPETITOR_PROFILE = {
  type: 'object', additionalProperties: true,
  properties: {
    name: { type: 'string' }, url: { type: 'string' },
    what_it_is: { type: 'string' }, category_label: { type: 'string' },
    money_question: { type: 'string' }, signature: { type: 'string' },
    footprint: { type: 'array', items: { type: 'object', properties: { label: { type: 'string' }, value: { type: 'string' } } } },
    capabilities: { type: 'array', items: { type: 'object', properties: { name: { type: 'string' }, status_hint: { type: 'string' }, source: { type: 'string' } } } },
    gaps: { type: 'array', items: { type: 'string' } },
    sources: { type: 'array', items: { type: 'object', properties: { label: { type: 'string' }, url: { type: 'string' } } } },
  }, required: ['name', 'what_it_is', 'capabilities', 'sources'],
}

const STATUS_ENUM = ['owned', 'ahead', 'partial', 'gap', 'unknown']
const MATRIX = {
  type: 'object', additionalProperties: false,
  properties: {
    capabilities: {
      type: 'array', items: {
        type: 'object', additionalProperties: false,
        properties: {
          name: { type: 'string' }, reality: { type: 'string', description: 'One-line honest reality check' },
          verdicts: {
            type: 'object', additionalProperties: {
              type: 'object', additionalProperties: false,
              properties: { status: { type: 'string', enum: STATUS_ENUM }, note: { type: 'string' }, source: { type: 'string' } },
              required: ['status'],
            },
          },
        }, required: ['name', 'reality', 'verdicts'],
      },
    },
    glance_notes: {
      type: 'array', items: { type: 'object', properties: { count: { type: 'string' }, title: { type: 'string' }, body: { type: 'string' } } },
    },
  }, required: ['capabilities'],
}

const NARRATIVE = {
  type: 'object', additionalProperties: true,
  properties: {
    hero: { type: 'object', properties: { kicker: { type: 'string' }, tagline: { type: 'string' }, subtitle: { type: 'string' } } },
    tldr: { type: 'object' }, ahead: { type: 'object' }, closeable: { type: 'object' },
    decisions: { type: 'object' }, positioning: { type: 'object' },
  }, required: ['hero', 'tldr', 'ahead', 'closeable', 'decisions', 'positioning'],
}

const REFUTE = {
  type: 'object', additionalProperties: false,
  properties: {
    supported: { type: 'boolean', description: 'Does the cited source clearly support the claim?' },
    confidence: { type: 'string', enum: ['low', 'medium', 'high'] },
    reason: { type: 'string' },
  }, required: ['supported', 'reason'],
}

// ----------------------------------------------------------------- intake reader task sets
function readerTasks(product) {
  const ref = product.ref
  const how = product.kind === 'url'
    ? `Use WebFetch to read pages under/related to: ${ref}`
    : (product.kind === 'repo'
      ? `Use Read/Grep over the repo at: ${ref}`
      : `Use Read to open, or treat as literal text: ${ref}`)
  const notes = product.notes ? `\nUser notes about the product: ${product.notes}` : ''
  if (product.kind === 'url') {
    return [
      `Read the homepage and product/features pages. ${how}. Extract what the product does and its capabilities.${notes}`,
      `Read the PRICING page. ${how} (find /pricing). Extract tiers, what's gated, ICP signals.${notes}`,
      `Read the docs/changelog/blog. ${how}. Extract real capabilities, integrations, and recent launches.${notes}`,
    ]
  }
  if (product.kind === 'repo') {
    return [
      `Read the README and any top-level docs. ${how}. Extract what the product does and its capabilities.${notes}`,
      `Map the source layout, feature modules, and package manifest(s). ${how}. Infer real capabilities from what's actually built.${notes}`,
      `Read architecture/ADR/config and any docs/ folder. ${how}. Extract differentiators and the category it plays in.${notes}`,
    ]
  }
  return [
    `Extract what the product does, its capabilities, category, and ICP. ${how}.${notes}`,
    `Extract the signature feature, the buyer's core "money question", and competitor/category keywords for search. ${how}.${notes}`,
  ]
}

// ----------------------------------------------------------------- discovery search angles
const DISCOVERY_ANGLES = [
  (p) => `Find competitors by SUBSTITUTION search: search "alternatives to ${p.name}", "${p.name} vs", "best ${p.category} tools 2026". List the products buyers compare against ${p.name}.`,
  (p) => `Find competitors via ANALYST/DIRECTORY signal: G2 / Capterra / TrustRadius / Gartner category for "${p.category}". List the category leaders and their standing.`,
  (p) => `Find competitors via FUNDING & NEWS: who in "${p.category}" is best-funded / most-covered / fastest-growing right now. Capture funding, customer counts, recent traction.`,
  (p) => `Find competitors via COMMUNITY signal: Reddit / HN / forums / "X vs Y" blog posts about "${p.category}". What do practitioners actually compare and pick between?`,
]

// ----------------------------------------------------------------- helpers
function platformNames(productProfile, competitors) {
  return [...competitors.map((c) => c.name), productProfile.name]
}

// ================================================================= MAIN
const stage = (args && args.stage) || 'discover'

if (stage === 'discover') {
  // ---- Phase A: Intake ----
  phase('Intake')
  const product = args.product
  if (!product || !product.ref) throw new Error('discover stage needs args.product {kind, ref}')
  const tasks = readerTasks(product)
  const parts = (await parallel(
    tasks.map((t, i) => () => agent(`You are reading OUR OWN product to establish "our side" of a competitive analysis. Use ONLY what the material actually shows — do not invent capabilities.\n\nTask: ${t}\n\nReturn a partial product profile.`,
      { agentType: 'competitor-intake-reader', label: `intake:${i + 1}`, phase: 'Intake', schema: PROFILE_PART }))
  )).filter(Boolean)

  const productProfile = await agent(
    `Merge these partial reads of OUR product into one clean profile. De-duplicate capabilities, pick the sharpest category label and ICP, write a one-line "money_question" a buyer answers with this product, a "signature" capability line, up to 2 footprint stats, and 4-6 "search_seeds" (queries/keywords) we'll use to find competitors.\n\nPartial reads:\n${JSON.stringify(parts)}`,
    { agentType: 'competitor-product-synthesizer', label: 'intake:synthesize', phase: 'Intake', schema: PRODUCT_PROFILE })

  log(`Product understood: ${productProfile.name} — ${productProfile.category}`)

  // ---- Phase B: Discovery (blind multi-modal sweep -> rank) ----
  phase('Discovery')
  const sweeps = (await parallel(
    DISCOVERY_ANGLES.map((mk, i) => () => agent(`Product: ${productProfile.name} — ${productProfile.what_it_is || productProfile.category}\nCategory: ${productProfile.category}\nSearch seeds: ${(productProfile.search_seeds || []).join(', ')}\n\n${mk(productProfile)}\n\nReturn every credible competitor you find with why it competes and any leadership signals (funding, customers, analyst standing) + sources.`,
      { agentType: 'competitor-discovery-scout', label: `discover:${i + 1}`, phase: 'Discovery', schema: CANDIDATE_LIST }))
  )).filter(Boolean)

  const allCandidates = sweeps.flatMap((s) => (s && s.candidates) || [])
  const ranked = await agent(
    `You are the RANKER. Here are competitor candidates gathered four different ways for "${productProfile.name}" (${productProfile.category}). De-duplicate (same company under different names/URLs = one entry), then rank by MARKET LEADERSHIP — the dominant, most-recognized names buyers benchmark against (mindshare, funding, customer base, analyst standing), NOT raw closeness. Output the full ranked list with a 0-100 leadership_score and the single best TOP 2 to compare against.\n\nCandidates:\n${JSON.stringify(allCandidates)}`,
    { agentType: 'competitor-ranker', label: 'discover:rank', phase: 'Discovery', schema: RANKED })

  log(`Top 2 by market leadership: ${ranked.top2.map((c) => c.name).join(' · ')}`)
  return { productProfile, ranked: ranked.ranked, top2: ranked.top2 }
}

// ===== stage === 'build' =====
const productProfile = args.productProfile
const competitors = args.competitors || []
const META = args.meta || {}
const SKEPTICS = Math.max(1, Math.min(3, args.skeptics || 2))
if (!productProfile || competitors.length === 0) throw new Error('build stage needs args.productProfile and args.competitors')

// ---- Phase C: Deep research (pipeline over competitors; dimensions fan out per competitor) ----
phase('Research')
const profiles = (await pipeline(
  competitors,
  // stage 1: research every dimension for this competitor, in parallel
  (comp) => parallel(DIMENSIONS.map((d) => () =>
    agent(`Research the competitor "${comp.name}" (${comp.url || 'find their site'}) on ONE dimension.\n\nDimension — ${d.key}: ${d.focus}\n\nUse WebSearch + WebFetch. For each finding, record the source URL, its date if shown, and a reliability tier (primary vendor page/docs > aggregator like G2/Crunchbase > individual review > vendor blog); flag anything older than ~12 months as worth re-verifying. Return specific, sourced findings; list what you could not verify under unknowns.`,
      { agentType: 'competitor-dimension-researcher', label: `research:${comp.name}:${d.key}`, phase: 'Research', schema: FINDINGS })
  )),
  // stage 2: synthesize this competitor's findings into a profile
  (findings, comp) => agent(`Synthesize a clean competitor profile for "${comp.name}" from these per-dimension findings. Produce: what_it_is (neutral), a category_label (short chip), the buyer's money_question, the signature feature, up to 2 footprint stats, a capabilities list (each with a status_hint of owned/partial/gap and a source), known gaps, and a deduped sources list (label+url). Keep every claim tied to a source from the findings.\n\nFindings:\n${JSON.stringify((findings || []).filter(Boolean))}`,
    { agentType: 'competitor-profile-synthesizer', label: `research:${comp.name}:synth`, phase: 'Research', schema: COMPETITOR_PROFILE })
)).filter(Boolean)

// ---- Phase D: Synthesis (matrix + narrative fan out, then assemble in code) ----
phase('Synthesis')
const names = platformNames(productProfile, competitors)
const matrixDraft = await agent(
  `Build the FEATURE MATRIX. Platforms (exact keys to use in "verdicts"): ${JSON.stringify(names)}. Our product is "${productProfile.name}".\n\nAnchor rows on Jobs-to-be-Done and real capability DEPTH, not feature-count — a longer checkmark column is not a win. Start from this canonical palette and adapt it to THIS category, keeping 8-14 rows that are a HONEST mix of rows we win, tie, and lose: core capability depth · integrations · API / developer experience · analytics & reporting · AI / automation · admin & governance · security & compliance · scalability · onboarding / time-to-value · support · pricing transparency · segment/ICP fit. For every platform in every row assign a status: owned (has it, shipping) | ahead (a genuine differentiator/lead) | partial (limited/gated/beta) | gap (missing) | unknown (couldn't establish). Competitor cells MUST carry a "source" URL drawn from the profiles — a competitor cell with a definite status but no source will be voided to unknown. Grade OURSELVES by the same evidence bar: do not score ourselves owned/ahead everywhere, and only mark us "ahead" on a row where NO competitor matches us. Add a one-line honest "reality" per row. Also add up to 3 "glance_notes" ("X leads on Y", count like "9/12").\n\nOur product profile:\n${JSON.stringify(productProfile)}\n\nCompetitor profiles:\n${JSON.stringify(profiles)}`,
  { agentType: 'competitor-matrix-builder', label: 'synth:matrix', phase: 'Synthesis', schema: MATRIX })

const narrative = await agent(
  `Write the NARRATIVE sections of the briefing for "${productProfile.name}" vs ${competitors.map((c) => c.name).join(', ')}, grounded in the matrix and profiles. Tone: plain, declarative, self-critical (this is intelligence, not marketing).\n\nProduce:\n- hero: {kicker:"Competitive Intelligence", tagline (≤12 words, "where we lead, where we lag, what to build next" energy), subtitle (1 sentence)}\n- tldr: {lead_in:"The honest read", sub, paragraphs:[2 short HTML-ok paragraphs — the honest topline], chips:[3 → {tone:green|blue|amber, icon:check|trending|alert, title, body}]}\n- ahead: {sub, items:[the moats where WE genuinely lead → {title, body}]}\n- closeable: {sub, items:[gaps closeable in ~a quarter → {title, desc, effort (e.g. "2-3 wks"), priority:HIGH|MEDIUM|LOW, effort_level:low|med|high, value:low|med|high}]}\n- decisions: {sub, items:[strategic OPEN QUESTIONS, not eng tasks → {title, body}]}\n- positioning: {sub, stats:[3 → {tone, value (≤2 words), label}], paragraphs:[1-2 HTML-ok], pullquote (the positioning sentence), closing, checklists:[ "To match <rival>" lists with {title, marker:"→"|"?", marker_color, items:[]}, and an "Already ours" {title, tone:green, marker:"✓", items:[]} ]}\n\nMatrix:\n${JSON.stringify(matrixDraft)}\n\nProfiles:\n${JSON.stringify(profiles)}`,
  { agentType: 'competitor-narrative-writer', label: 'synth:narrative', phase: 'Synthesis', schema: NARRATIVE })

// ---- Phase E: Adversarial verification (refute each risky competitor claim vs its source) ----
phase('Verify')
const LENSES = ['Read the cited source literally — does it state this exact claim, or are you inferring?',
  'Check recency and scope — is the source current and about the right product/edition?',
  'Look for contradiction — does anything on the source or its site contradict the claim?']
const competitorNames = new Set(competitors.map((c) => c.name))

// collect risky claims: competitor cells with a definite status + a source
const claims = []
matrixDraft.capabilities.forEach((cap, ci) => {
  Object.entries(cap.verdicts || {}).forEach(([plat, v]) => {
    if (competitorNames.has(plat) && v && v.source && ['owned', 'ahead', 'gap'].includes(v.status)) {
      claims.push({ ci, plat, cap: cap.name, status: v.status, note: v.note || '', source: v.source })
    }
  })
})
log(`Verifying ${claims.length} competitor claims with ${SKEPTICS} skeptics each`)

const verdicts = await parallel(claims.map((cl) => () =>
  parallel(Array.from({ length: SKEPTICS }, (_, k) => () =>
    agent(`You are a SKEPTIC. Try to REFUTE this competitive-analysis claim. Default to supported=false if the source does not clearly back it.\n\nClaim: "${cl.plat} — ${cl.cap}: status=${cl.status}${cl.note ? ' (' + cl.note + ')' : ''}".\nCited source: ${cl.source}\n\n${LENSES[k % LENSES.length]}\n\nFetch the source and judge whether it clearly supports the claim.`,
      { agentType: 'competitor-claim-verifier', label: `verify:${cl.plat}:${cl.cap.slice(0, 20)}:${k + 1}`, phase: 'Verify', schema: REFUTE })
  )).then((votes) => {
    const v = votes.filter(Boolean)
    const supported = v.filter((x) => x.supported).length
    return { ...cl, supported, total: v.length, kept: supported * 2 >= v.length }  // majority must support
  })
))

// apply downgrades
const downgrades = []
verdicts.filter(Boolean).forEach((r) => {
  if (!r.kept) {
    matrixDraft.capabilities[r.ci].verdicts[r.plat] = { status: 'unknown', note: 'unverified', source: r.source }
    downgrades.push(`${r.plat} / ${r.cap}: ${r.status} → unknown (${r.supported}/${r.total} skeptics supported)`)
  }
})
log(`Verification complete: ${downgrades.length} claim(s) downgraded to unknown`)

// provenance guard: any competitor cell with a definite status but no source -> unknown
matrixDraft.capabilities.forEach((cap) => {
  Object.entries(cap.verdicts || {}).forEach(([plat, v]) => {
    if (competitorNames.has(plat) && v && ['owned', 'ahead', 'partial', 'gap'].includes(v.status) && !v.source) {
      cap.verdicts[plat] = { status: 'unknown', note: v.note || 'no source' }
    }
  })
})
// home-team-bias guard: our "ahead" is a differentiator only if NO rival also has the row
matrixDraft.capabilities.forEach((cap) => {
  const ours = cap.verdicts && cap.verdicts[productProfile.name]
  if (ours && ours.status === 'ahead') {
    const rivalHasIt = competitors.some((c) => {
      const rv = cap.verdicts[c.name]
      return rv && (rv.status === 'owned' || rv.status === 'ahead')
    })
    if (rivalHasIt) { ours.status = 'owned'; ours.note = (ours.note ? ours.note + '; ' : '') + 'parity — rival also has it' }
  }
})

// ---- assemble final data.json (mechanical, no model) ----
function playerCard(p, isProduct) {
  return {
    name: p.name, short_name: p.short_name || p.name,
    category_label: p.category_label || (isProduct ? p.category : ''),
    money_question: p.money_question || '', signature: p.signature || '',
    footprint: (p.footprint || []).slice(0, 2), url: p.url || '',
  }
}
// dedupe external sources from profiles + matrix
const srcMap = new Map()
profiles.forEach((p) => (p.sources || []).forEach((s) => { if (s && s.url) srcMap.set(s.url, s.label || s.url) }))
matrixDraft.capabilities.forEach((cap) => Object.values(cap.verdicts || {}).forEach((v) => { if (v && v.source) srcMap.set(v.source, srcMap.get(v.source) || v.source) }))
const external = [...srcMap].map(([url, label]) => ({ label, url }))

const data = {
  meta: META,
  product: playerCard({ ...productProfile, category_label: productProfile.category }, true),
  competitors: profiles.map((p) => playerCard(p, false)),
  hero: narrative.hero,
  tldr: narrative.tldr,
  matrix: matrixDraft,
  ahead: narrative.ahead,
  closeable: narrative.closeable,
  decisions: narrative.decisions,
  positioning: narrative.positioning,
  sources: { external, internal: [] },
}

const report = {
  competitors: competitors.map((c) => c.name),
  rows: matrixDraft.capabilities.length,
  claims_verified: claims.length,
  downgraded: downgrades,
  sources: external.length,
}
return { data, report }
