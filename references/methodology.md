# Competitive Analysis Methodology Brief

A prompt-ready playbook for a multi-agent system producing rigorous, sourced
competitive-analysis briefings (product vs. its top 2 market competitors).
Encode these rules verbatim into agent prompts. Bullets are designed to be lifted directly.

---

## 1. Excellent vs. Mediocre Competitive Analysis

**What makes it trustworthy (do these):**
- **Every competitor claim is grounded in a primary source with a date and URL.** No claim ships without provenance. Marketing fluff = unsourced superlatives ("the leading platform").
- **Decision-oriented, not descriptive.** Ends in "where we win / where we lose / what to build next," not a feature inventory.
- **Graded, not binary.** Use Full / Partial / None / Unknown — never silent yes/no. "Unknown" is a valid, honest cell.
- **Separates the job from the feature.** Maps how each product helps the buyer execute their *job-to-be-done*, not just which checkboxes it ticks. A competitor can match features and still win on UX, onboarding speed, or time-to-value.
- **Names the date and the source's reliability tier.** Pricing seen on a vendor page (Tier 1) outranks a third-party blog (Tier 3).
- **Falsifiable.** A reader can re-check any claim from the cited link.

**Frameworks pros use (pick by purpose, then sequence — they're complementary, not rival):**
- **Feature-parity / capability matrix** — head-to-head capability grid; the spine of any teardown. Grade cells, don't binary them.
- **Jobs-to-be-Done (JTBD)** — reframe competition around the buyer's job ("get reliable revenue reporting"), not the product category. Surfaces indirect/substitute competitors a feature grid misses.
- **Porter's Five Forces** — industry structure / profitability lens (rivalry, new entrants, substitutes, supplier power, buyer power). Use at the *line-of-business* level, not the whole sector. Good for "is this market defensible."
- **Positioning / perceptual map (2x2)** — plot players on two buyer-salient axes (e.g. price vs. depth, SMB vs. enterprise) to expose white space.
- **Marketing mix (4Ps/7Ps)** — Product, Price, Place, Promotion (+People, Process, Physical evidence). Best for *operationalizing* a chosen position, not defining one.
- **Win-loss analysis** — interviews with deals won/lost; the single most credible source of real differentiation and objection patterns.
- **SWOT** — *synthesis only*, at the end. It doesn't explain causality or quantify; use it to consolidate findings from the rigorous work above, never as the analysis itself.

**Competitor selection discipline (so "top 2" is defensible):**
- Sort into **direct** (same thing, same buyer), **indirect** (same job, different mechanism), and **adjacent** (overlap on one axis). State *why* the chosen top 2 are the right rivals (overlap on ICP + job + deal-frequency), and name the runners-up considered.

---

## 2. Research Dimensions Per Competitor + Where the Primary Signal Lives

Investigate this canonical set for each competitor. Prefer the highest-tier source; record the source + date per cell.

| Dimension | Most reliable PRIMARY signal | Notes / traps |
|---|---|---|
| **Pricing & packaging** | Official pricing page (tiers, price points, billing interval, seat vs. usage). Capture "Contact sales" thresholds. | Enterprise pricing is often hidden — mark Unknown, infer band from review mentions, never invent a number. |
| **Core features & differentiators** | Official product/feature pages + docs; product itself (free trial/sandbox); changelog/release notes for what's real vs. roadmap. | Distinguish shipped vs. announced/roadmap. Marketing page ≠ shipped. |
| **Integrations / API / extensibility** | Public API reference, developer docs, integrations marketplace/directory, SDK repos. | Count + depth of integrations; webhook/SSO/SCIM support; rate limits. |
| **Target ICP & positioning** | Homepage hero + "Customers"/case-study pages, the segment language they use, G2 segment breakdown (SMB/Mid/Ent). | Who they say they're for vs. who actually reviews them. |
| **Go-to-market** | Pricing motion (self-serve vs. sales-led), job postings (sales vs. PLG roles), ad libraries (Meta/LinkedIn/Google), partner pages. | Hiring + ad spend reveal GTM direction before the website does. |
| **Momentum / funding / traction** | Crunchbase/PitchBook, press releases, SEC/earnings (if public), funding-round news, headcount trend (LinkedIn), changelog cadence. | Logo walls and "trusted by" lists corroborate enterprise traction. |
| **Known weaknesses & complaints** | G2 / Capterra / TrustRadius "What do you dislike?" fields; Reddit, community forums, app-store reviews; support-doc gaps. | Richest unfiltered signal. Read recent + filter by reviewer segment; watch for incentivized/gift-card reviews and astroturfing. |
| **Compliance / security** | Vendor trust/security center; SOC 2 / ISO 27001 / HIPAA / GDPR pages; status page; subprocessor list. | "SOC 2 Type II" ≠ "SOC 2 in progress." Capture the exact attestation + date. |
| **Reliability / support** | Public status page + incident history; SLA terms; support tiers in pricing. | Uptime history is a hard, dateable fact. |

**Source reliability tiers (cite the tier):**
1. Vendor primary (pricing/docs/API/changelog/trust center) and the product itself.
2. Structured third parties with methodology (G2/Capterra aggregate, Crunchbase, SEC filings).
3. Individual reviews / forum posts (signal, but anecdotal — corroborate before asserting).
4. Vendor blogs / analyst-sponsored content / competitor comparison pages (treat as claims, not facts).

---

## 3. Common Pitfalls & Biases (and the counter for each)

- **Home-team bias / over-scoring yourself** — grade your own product by the *same* evidence bar as competitors; require a primary-source citation for your own "Full" cells too. Have an adversarial agent argue the competitor's side.
- **Taking marketing claims at face value** — never promote a marketing-page claim to a fact. Demote to "claims X (source, date)" until confirmed in docs/product/reviews.
- **Feature-checklist trap** — a longer checkmark column ≠ winning. Weight by JTBD importance and implementation quality (UX, time-to-value), not feature count.
- **Cherry-picking / confirmation bias** — pre-commit the dimension list and matrix rows *before* researching, so you can't drop inconvenient cells. Actively log evidence that contradicts your thesis.
- **Recency bias** — one shiny recent launch or one recent bad review is noise. Weight by sample size and look at the trend (changelog cadence, review trend over 4+ quarters).
- **Stale data** — date-stamp every claim; flag anything older than ~6-12 months as "may be stale — reverify." Pricing/features change quietly.
- **Survivorship / review-platform bias** — reviews over-represent extremes and incentivized users; filter by reviewer segment matching your ICP and discount tiny review counts.
- **False precision** — don't state hidden enterprise pricing as exact; give a band with its basis or mark Unknown.

---

## 4. Recommended Feature-Matrix Row Categories (B2B SaaS, generalizes across categories)

Use ~10-14 rows. These are buyer-salient and category-agnostic; swap 2-3 "core capability" rows for the specific product category. Grade each Full / Partial / None / Unknown with a source.

1. **Core capability depth** — the central job the category exists to do (1-3 rows, category-specific).
2. **Breadth of use cases / modularity** — single workflow vs. platform/suite.
3. **Integrations & ecosystem** — # and depth of prebuilt connectors, marketplace.
4. **API / developer experience & extensibility** — public API, SDKs, webhooks, docs quality.
5. **Data & analytics / reporting** — dashboards, export, BI connectivity.
6. **AI / automation capabilities** — native AI features, agents, automation rules.
7. **Admin, roles & governance** — RBAC, audit logs, SSO/SAML, SCIM provisioning.
8. **Security & compliance** — SOC 2 / ISO 27001 / HIPAA / GDPR, encryption, data residency.
9. **Scalability & performance** — multi-team/region scale, published limits, uptime SLA.
10. **Onboarding & time-to-value** — setup speed, templates, implementation effort.
11. **Support & success** — support tiers, CSM, community, docs depth.
12. **Pricing model & transparency** — self-serve vs. sales-led, public pricing, seat vs. usage, free tier/trial.
13. **Target segment fit** — SMB / Mid-market / Enterprise focus.
14. **Mobile / platform coverage** — web, mobile, desktop, offline (if relevant).

---

## 5. Reducing Hallucination / Ungrounded Claims (LLM agents)

- **Retrieval-grounded only.** Every competitor fact must trace to fetched source text — no claims from model memory. If it wasn't retrieved, it's "Unknown."
- **Cite the primary source + date inline** for each claim/cell (URL + access date + reliability tier). Programmatically reject cells with no citation.
- **Atomic-claim verification (chain-of-verification).** Decompose the draft into atomic claims; a separate verifier agent re-checks each against the cited source text and flags unsupported ones. Self-citation rate correlates negatively with hallucination.
- **Adversarial pass.** A red-team agent argues the opposite of each "we win" / "they lack X" claim and must be answered with evidence or the claim is downgraded to "Unknown."
- **Mark unknowns explicitly; never interpolate.** No invented prices, dates, customer counts, or features. "Could not verify" beats a plausible guess.
- **Constrain output shape.** Structured schema (claim, value, source_url, date, tier, confidence) makes ungrounded fields obvious and auto-checkable.
- **Separate fact from inference.** Label derived conclusions ("inferred from job postings") distinctly from sourced facts.
- **Recency guard.** Prefer sources < 6-12 months; tag older evidence "stale — reverify."

---

## Sources

- [Productboard — Competitor Analysis: Framework, Template & Best Practices](https://www.productboard.com/glossary/competitor-analysis/)
- [thrv — Competitive Analysis Matrix (Jobs-to-be-Done)](https://www.thrv.com/glossary/competitive-analysis-matrix)
- [The Growth Syndicate — Competitor Analysis Framework](https://www.thegrowthsyndicate.com/resources/competitor-analysis-framework)
- [HireSteve — G2 and Capterra Reviews as Competitive Intelligence (2026)](https://hiresteve.ai/articles/g2-capterra-reviews-competitive-intelligence-2026)
- [SiftHub — The Untapped Sources of Competitive Intelligence](https://www.sifthub.io/blog/sources-of-competitive-intelligence)
- [Platform Executive — Choosing the Right Framework: SWOT, PESTLE, Porter's Five Forces, 5C](https://www.platformexecutive.com/knowledge/business-models/competitive-intelligence/choosing-the-right-framework-when-to-use-swot-pestle-porters-five-forces-and-5c-analysis/)
- [Wikipedia — Porter's Five Forces Analysis](https://en.wikipedia.org/wiki/Porter's_five_forces_analysis)
- [LinkedIn — How to Avoid Common Pitfalls and Biases in Competitor Analysis](https://www.linkedin.com/advice/0/how-do-you-avoid-common-pitfalls-biases-when-5c)
- [ML Journey — How to Reduce Hallucination in LLM Applications](https://mljourney.com/how-to-reduce-hallucination-in-llm-applications/)
- [arXiv — Citation Grounding: Detecting and Reducing LLM Citation Hallucinations](https://arxiv.org/html/2606.00898)
- [T2D3 — Using a Feature Matrix for B2B SaaS Pricing Strategy](https://www.t2d3.pro/learn/saas-pricing-matrix)
