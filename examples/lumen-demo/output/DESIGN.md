# Design System: Lumen (demo)
_Extracted by DEA on 2026-11-07 from file:///examples/lumen-demo/index.html. Tokens are measured; role names are inferred (see confidence)._

## 1. Visual summary (auto-draft: AGENT must verify against screenshots and rewrite in your own words)
- **Mode:** light base with dark theme support
- **Accent:** indigo on warm-tinted neutrals
- **Corners:** rounded  |  **Elevation:** soft + colored glow on featured elements  |  **Density:** airy
- **Headline style:** 64px / 700 / tracking -0.035em  |  **Motion:** snappy (<=150ms)
- **Tech/stack hints:** n/a

<!-- AGENT: replace with a 3-5 sentence description of the aesthetic, what makes it recognizable (layout, imagery, type voice, signature details) and the 5 rules that keep it consistent. -->

## 2. Color
### Semantic roles (light)
| Role | Value | Evidence | Confidence |
|---|---|---|---|
| background | `#fafaf9` | CSS variable --bg | high |
| foreground | `#1c1917` | CSS variable --fg | high |
| card | `#ffffff` | CSS variable --surface | high |
| card-foreground | `#1c1917` | same as foreground | low |
| popover | `#ffffff` | same as card | low |
| primary | `#4f46e5` | button background (2 uses) | high |
| primary-foreground | `#ffffff` | CSS variable --accent-fg | high |
| secondary | `#ffffff` | secondary button background | medium |
| secondary-foreground | `#1c1917` | secondary button text | medium |
| muted | `#f3f2ef` | CSS variable --surface-2 | high |
| muted-foreground | `#6b6560` | CSS variable --fg-muted | high |
| accent | `#4f46e5` | CSS variable --accent | high |
| accent-foreground | `#1c1917` | assumed = foreground | low |
| destructive | `#dc2626` | CSS variable --danger | high |
| success | `#16a34a` | CSS variable --success | high |
| warning | `#d97706` | CSS variable --warning | high |
| border | `#e7e5e0` | CSS variable --border | high |
| input | `#e7e5e0` | assumed = border | low |
| ring | `#4f46e5` | assumed = primary | low |

### Dark theme (strategy: prefers-color-scheme media query)
| Role | Value | Evidence |
|---|---|---|
| background | `#0c0a09` | CSS variable --bg |
| foreground | `#f5f5f4` | CSS variable --fg |
| card | `#171412` | CSS variable --surface |
| card-foreground | `#f5f5f4` | same as foreground |
| popover | `#171412` | same as card |
| primary | `#818cf8` | button background (2 uses) |
| primary-foreground | `#0c0a09` | CSS variable --accent-fg |
| secondary | `#171412` | secondary button background |
| secondary-foreground | `#f5f5f4` | secondary button text |
| muted | `#211d1a` | CSS variable --surface-2 |
| muted-foreground | `#a8a29e` | CSS variable --fg-muted |
| accent | `#818cf8` | CSS variable --accent |
| accent-foreground | `#f5f5f4` | assumed = foreground |
| destructive | `#dc2626` | CSS variable --danger |
| success | `#16a34a` | CSS variable --success |
| warning | `#d97706` | CSS variable --warning |
| border | `#2a2522` | CSS variable --border |
| input | `#2a2522` | assumed = border |
| ring | `#818cf8` | assumed = primary |

### Accent colors seen
`#4f46e5` (indigo)

### Neutral ramp (light -> dark)
`#ffffff` `#f3f2ef` `#e7e5e0` `#6b6560` `#1c1917`

### Gradients
- `linear-gradient(135deg, rgb(79, 70, 229), rgb(167, 139, 250))`
- `radial-gradient(at 50% 0%, rgb(238, 242, 255), rgba(0, 0, 0, 0) 60%)`

### Contrast (WCAG)
| Pair | Ratio | AA text | AA large |
|---|---|---|---|
| foreground on background | 16.74 | pass | pass |
| muted text on background | 5.5 | pass | pass |
| text on primary | 6.29 | pass | pass |
| primary on background (links/icons) | 6.02 | pass | pass |

## 3. Typography
- **Families:** sans: `Inter`, heading: `Inter`, mono: `ui-monospace`
- **Base:** 16.0px / line-height 1.6
- **Scale ratio:** ~1.414 (augmented fourth), measured median 1.455
- **Heading tracking:** -0.025em  |  **Weights used:** 400 (64%), 600 (12%), 500 (9%), 650 (7%), 700 (5%)
- **Responsive H1 size:** tablet: 40px, mobile: 40px

| Role | Size | Weight | Line-height | Tracking | Family | Notes |
|---|---|---|---|---|---|---|
| h1 | 64px | 700 | 1.05 | -0.035em | Inter |  |
| h2 | 36px | 650 | 1.15 | -0.025em | Inter |  |
| h3 | 20px | 600 | 1.3 | -0.01em | Inter |  |
| body | 16px | 400 | 1.6 | 0em | Inter |  |
| paragraph | 15px | 400 | 1.6 | 0em | Inter |  |
| lead | 20px | 400 | 1.6 | 0em | Inter |  |
| small | 15px | 400 | 1.6 | 0em | Inter |  |
| button/label | 14px | 500 | - | 0em | Inter |  |
| overline | 13px | 600 | 1.6 | 0.08em | Inter | uppercase |
| code | 13px | 400 | 1.6 | 0em | ui-monospace |  |

### Font sourcing
| Family | Source | Open alternative | Note |
|---|---|---|---|
| Inter | installed locally or unresolved | - |  |
| ui-monospace | system | - |  |

## 4. Spacing & layout
- **Base unit:** 4px (fits 83% of measured values)
- **Scale in use (px):** 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 26, 28, 40, 48, 96
- **Section vertical padding:** 40px, 48px, 96px, 120px
- **Common grid gaps:** 24px
- **Container max-width:** 1120px
- **Breakpoints (min-width):** n/a
- **Header:** sticky, 65px tall, bg `#fafaf9cc`, backdrop `blur(12px)`, border-bottom `1px solid #e7e5e0`
- **Grids:** `40px|gap:normal`; `341.328px 341.328px 341.344px|gap:24px`

## 5. Shape, borders, elevation
- **Radius scale:** sm=6px, md=10px, lg=12px, xl=16px, full=9999px (rounded)
- **Border patterns:** `1px solid #e7e5e0 [all]`; `1px solid #00000000 [all]`; `1px solid #e7e5e0 [b]`; `1px solid #e7e5e0 [tb]`
- **Shadows:** sm: `0px 1px 2px rgba(28, 25, 23, 0.06)`, md: `0px 4px 12px rgba(28, 25, 23, 0.08), 0px 1px 3px rgba(28, 25, 23, 0.06)`; glows: ['0px 20px 40px -12px rgba(79, 70, 229, 0.25)']; backdrop: ['blur(12px)']

## 6. Motion
- **Durations:** base=150ms  |  **Easing:** `cubic-bezier(0.2, 0.8, 0.2, 1)`, `ease`
- **Transitioned properties:** box-shadow, transform, background, color, border-color
- **Scroll behavior:** smooth
- keyframes `rise`: `@keyframes rise { 0% { opacity: 0; transform: translateY(12px); } 100% { opacity: 1; transform: none; } }`

### Interaction states (measured)
- **button** "Sign in": hover -> none | focus -> outline: rgb(107, 101, 96) none 3px -> rgb(16, 16, 16) auto 1px; outlineOffset: 0px -> 1px
- **button** "Start free": hover -> backgroundColor: #4f46e5 -> #4338ca (darker); boxShadow: rgba(28, 25, 23, 0.06) 0px 1px 2px 0px -> rgba(28, 25, 23, 0.08) 0px 4px 12px 0px, rgba(28, 25, 23, 0.; transform: translateY(-1px) | focus -> outline: rgb(255, 255, 255) none 3px -> rgb(16, 16, 16) auto 1px; outlineOffset: 0px -> 1px
- **button** "Get started": hover -> backgroundColor: #4f46e5 -> #4338ca (darker); boxShadow: rgba(28, 25, 23, 0.06) 0px 1px 2px 0px -> rgba(28, 25, 23, 0.08) 0px 4px 12px 0px, rgba(28, 25, 23, 0.; transform: translateY(-1px) | focus -> outline: rgb(255, 255, 255) none 3px -> rgb(16, 16, 16) auto 1px; outlineOffset: 0px -> 1px
- **button** "Book a demo": hover -> backgroundColor: #ffffff -> #f3f2ef (darker) | focus -> outline: rgb(28, 25, 23) none 3px -> rgb(16, 16, 16) auto 1px; outlineOffset: 0px -> 1px
- **nav-link** "Lumen": hover -> none | focus -> outline: rgb(28, 25, 23) none 3px -> rgb(16, 16, 16) auto 1px; outlineOffset: 0px -> 1px
- **nav-link** "Product": hover -> color: #6b6560 -> #1c1917 (darker); borderTopColor: #6b6560 -> #1c1917 (darker) | focus -> outline: rgb(107, 101, 96) none 3px -> rgb(16, 16, 16) auto 1px; outlineOffset: 0px -> 1px
- **card** "Live eventsSee what is happe": hover -> boxShadow: rgba(28, 25, 23, 0.06) 0px 1px 2px 0px -> rgba(28, 25, 23, 0.08) 0px 4px 12px 0px, rgba(28, 25, 23, 0.; transform: translateY(-2px) | focus -> none
- **card** "Starter$0 /moUp to 10k event": hover -> boxShadow: rgba(28, 25, 23, 0.06) 0px 1px 2px 0px -> rgba(28, 25, 23, 0.08) 0px 4px 12px 0px, rgba(28, 25, 23, 0.; transform: translateY(-2px) | focus -> none
- **input** "you@company.com": hover -> borderTopColor: #e2e0e0 -> #e7e5e0 (lighter); boxShadow: rgba(238, 242, 255, 0.03) 0px 0px 0px 0.0918px -> none | focus -> borderTopColor: #e2e0e0 -> #4f46e5 (darker); boxShadow: rgba(238, 242, 255, 0.03) 0px 0px 0px 0.0918px -> rgb(238, 242, 255) 0px 0px 0px 3px

## 7. Components
### Buttons
| Variant | Uses | Label | Size | Background | Text | Border | Radius | Padding | Font |
|---|---|---|---|---|---|---|---|---|---|
| primary | 2 | Start free | 101x40 | `#4f46e5` | `#ffffff` | 1px solid #00000000 [all] | 10px | 0px 18px | 14px/500 |
| outline | 1 | Sign in | 83x40 | `transparent` | `#6b6560` | 1px solid #00000000 [all] | 10px | 0px 18px | 14px/500 |
| primary | 1 | Get started | 134x48 | `#4f46e5` | `#ffffff` | 1px solid #00000000 [all] | 12px | 0px 26px | 15px/500 |
| secondary | 1 | Book a demo | 147x48 | `#ffffff` | `#1c1917` | 1px solid #e7e5e0 [all] | 12px | 0px 26px | 15px/500 |

### Cards
- x5: bg `#ffffff`, text `#1c1917`, border 1px solid #e7e5e0 [all], radius 16px, padding 28px, font 16px/400, shadow `rgba(28, 25, 23, 0.06) 0px 1px 2px 0px`, structure `div > h3 > p`
- x1: bg `#ffffff`, text `#1c1917`, border 1px solid #4f46e5 [all], radius 16px, padding 28px, font 16px/400, shadow `rgba(79, 70, 229, 0.25) 0px 20px 40px -12px`, structure `span > h3 > div > p`

### Inputs
- x1: bg `#ffffff`, text `#1c1917`, border 1px solid #e7e5e0 [all], radius 10px, padding 0px 14px, font 15px/400

### Badges/pills
- x2: bg `#eef2ff`, text `#4f46e5`, border none, radius 999px, padding 4px 12px, font 12px/600

### Nav links
- x4: bg `transparent`, text `#6b6560`, border none, radius 0px, padding 0px, font 14px/500
- x1: bg `transparent`, text `#1c1917`, border none, radius 0px, padding 0px, font 20px/700

### Icons
- 3 inline SVGs; sizes 20x20; style outline(stroke); stroke widths 1.75px

## 8. Page anatomy (top to bottom)
| # | Kind | Height | Heading | Bg | Cols | Buttons | Media | Align |
|---|---|---|---|---|---|---|---|---|
| 1 | nav | 65px |  | #fafaf9cc |  | 2 |  | start |
| 2 | hero | 566px | Analytics that stay out of your way | #00000000 |  | 2 |  | center |
| 3 | logo-strip | 103px |  | #00000000 |  |  |  | start |
| 4 | feature-grid | 477px | Everything you need, nothing you don't | #00000000 | 3 |  | 3 | start |
| 5 | pricing | 531px | Simple pricing | #f3f2ef | 3 |  |  | start |
| 6 | cta | 349px | Ready when you are | #00000000 |  | 1 |  | center |
| 7 | footer | 119px |  | #00000000 |  |  |  | start |

## 9. Responsive behavior
| Viewport | H1 | Nav links shown | Hamburger | Grid cols | Section pad | H-overflow |
|---|---|---|---|---|---|---|
| tablet (820) | 40px | 3 | no | stacked | 40px | no |
| mobile (390) | 40px | 3 | no | stacked | 40px | no |

## 10. Assets & tech
- Images: 0, inline SVG: 3, video: 0, canvas: 0
- Brand assets (logo, photography, illustration) are **references only**. Do not copy them; use placeholders or the user's own.

## 11. Unknowns & verification notes
- Low-confidence palette roles (inferred, verify against screenshots): card-foreground, popover, ring, input, accent-foreground
- Font 'Inter' was not found as a web font; it may be installed on the capture machine or blocked.

## 12. Rules to keep it consistent
<!-- AGENT: write 5-8 concrete do/don't rules inferred from the tokens and screenshots (e.g. 'accent only on primary actions', 'headings always tracked -0.03em', 'cards: 1px border, no shadow until hover'). -->
