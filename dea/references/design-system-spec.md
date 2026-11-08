# Refining DESIGN.md

`synthesize.py` writes the measured skeleton. Your job is to make it correct, complete and useful as the single source of truth for rebuilding.

## Refinement pass (always do this)
1. **Compare with screenshots.** Do palette roles match what you see (is "primary" really the CTA color, is "card" the card surface)? Fix `tokens.json`/`DESIGN.md` where inference was wrong; keep the evidence line updated ("corrected by visual check").
2. **Replace every `<!-- AGENT: ... -->` marker** with real content: aesthetic summary (3-5 sentences) and 5-8 consistency rules.
3. **Resolve low-confidence roles** listed under Unknowns: sample real colors or read the relevant CSS variable.
4. **Fill gaps the scripts cannot see:** illustration/photo style, icon family, logo treatment, scroll/entrance animations, hero visuals (WebGL, video), special effects (grain, glow, glass).
5. **Name the type roles in terms of use** ("Section title = h2 36/650/-0.025em", "Eyebrow = 13px uppercase +0.08em").
6. **State hover/focus/active/disabled behavior** for button, link, card, input, nav. Use measured diffs; fill untested ones with the most consistent pattern and mark as assumed.
7. **Dark mode:** confirm strategy (media query or class) and that all roles have dark values.
8. **Record what you are NOT reproducing** (logo, photography, proprietary fonts, copy).

## Token conventions
- Semantic names, shadcn-compatible: `background foreground card popover primary secondary muted accent destructive border input ring` + `-foreground` pairs, plus `success warning info`.
- Type: `--font-sans/heading/mono`, `--text-{display,h1..h4,body,lead,small,label,overline}` with `--leading-*`, `--weight-*`, `--tracking-*`.
- Space: `--space-unit` and multiples; `--section-padding-y`, `--container-max`.
- Shape: `--radius-sm|md|lg|xl|full`, `--radius` (dominant).
- Elevation: `--shadow-xs..2xl`, `--shadow-glow`.
- Motion: `--duration-fast|base|slow`, `--ease`.
- Values are literal and measured; do not round to "nicer" numbers unless the system is clearly on a scale (then snap and say so).

## Quality bar for a finished DESIGN.md
- Someone could rebuild any page of the site from it without opening the original.
- Every number has a source (variable, measured, estimated) and every role has confidence.
- Includes anatomy for at least the homepage and one inner page type.
- Lists responsive rules, not just desktop.
- Contrast checks present; failures called out (and the decision: preserve or fix).
