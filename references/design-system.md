# Design system

Extracted from the original Lovable export. The renderer ([../scripts/build_page.py](../scripts/build_page.py))
is the source of truth for markup; this is the quick reference. The compiled stylesheet
[../assets/base.css](../assets/base.css) is inlined into every page — **only class names that
already appear in it exist**, so reuse existing classes and use inline `style=` for anything new.

## Fonts (loaded from Google Fonts)
- **Manrope** — display headings & `font-cta` labels. `--font-manrope`.
- **Inter** — body copy (`text-p-*`). `--font-inter`.
- **Geist** — numerals (`font-num`, tabular). `--font-geist`.

Custom utility classes defined in base.css:
- `text-display-2xl / -xl / -lg / -md / -sm / -xs` — Manrope display scale (xl = 48px).
- `text-p-lg / -md / -sm` — Inter body scale (md = 16px).
- `font-cta` — Manrope, uppercase, letter-spacing .1em, 12px/700 (the small caps labels).
- `font-num` — Geist tabular numerals. `font-display` — Manrope 500.
- `no-print` — hidden in the print stylesheet (header, sidebar, progress bar).

## Color roles
| hex | role |
|-----|------|
| `#245AE2` | brand / primary blue (product accent, "ahead", links) |
| `#01194C` | deep navy — hero gradient end, dark "decisions" section bg |
| `#0E245A` / `#344770` | dark-section card fill / border |
| `#D6F549` (border `#80932C`, tint `#F7FDDB`) | lime accent — hero highlights, our product's bar |
| `#2F2F2F` / `#4D4D4D` / `#666` / `#111` | text: near-black → secondary → muted → strong |
| `#E2E8F0` | hairline borders | `#F8FAFD` / `#D3DEF9` | light blue tints |
| `#F4F3F2` | warm grey ("Where we lead" section bg) |
| `#121317` | footer bg |

### Verdict / status system (the matrix)
| status | fg | bg | border |
|--------|----|----|--------|
| `owned` | `#0F9D58` | `#DFF6E8` | `#0F9D58` |
| `ahead` | `#245AE2` | `#D3DEF9` | `#245AE2` |
| `partial` | `#D97706` | `#FEF3C7` | `#D97706` |
| `gap` | `#DC2626` | `#FEE2E2` | `#DC2626` |
| `unknown` | `#666666` | `#F4F3F2` | `#CCCCCC` |

Pills are a rounded bordered chip with a 6px filled dot + label (see `status_pill` in the renderer).

## Layout rhythm
- Page max-width `1296px`; section padding `px-6 py-14 md:px-12`.
- Sticky 12px top header (live stat counters) + sticky 56px left sidebar nav (8 numbered sections),
  both `no-print`. A scroll-progress bar tops the page; a small vanilla script drives progress +
  active-section highlight + mobile nav toggle.
- **Dark sections** (white text): hero (blue→navy gradient) and "decisions" (`#01194C`). Everything
  else is light, alternating white / `#F8FAFD` / `#F4F3F2` backgrounds.
- Charts (coverage bars, effort-vs-value scatter) are drawn with inline-styled HTML/CSS — the
  originals were React/Recharts SVG and aren't reproducible standalone, so the renderer redraws
  equivalents that need no runtime.
