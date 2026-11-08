# Reading a screenshot like a design engineer

Numbers describe a design; the screenshot shows why it feels the way it does. Look at every screenshot (fold, full page, sections, mobile, dark) before writing the summary. For each, answer the checklist, then write findings into `DESIGN.md`.

## Checklist
1. **Grid and width:** content column width vs viewport, number of columns, gutters, alignment (left, centered, asymmetric). Is there a visible baseline or consistent left edge?
2. **Hierarchy:** what is the single most prominent thing per section? How is hierarchy made (size, weight, color, space, contrast)? Count distinct text styles on screen (usually 4-6).
3. **Density and rhythm:** gap between sections vs gap inside components. Repeating vertical rhythm? Tight (dashboard) vs airy (marketing)?
4. **Type voice:** geometric / grotesque / humanist / serif / mono accents. Heading tracking (tight negative = modern), weight contrast (700 vs 400), uppercase micro-labels, numerals style.
5. **Color behavior:** how much of the page is neutral vs accent? Where does the accent appear (CTA only, links, highlights, illustrations)? Surface layering (page, card, popover) and border vs shadow vs tone to separate surfaces.
6. **Shape language:** corner radius consistency (one value or a system), pill buttons, outlines vs fills, borders (1px hairlines) and dividers.
7. **Depth:** flat, bordered, soft shadows, glass blur, glow, gradients, noise/grain, inner highlights.
8. **Imagery:** product screenshots in frames (browser chrome? shadow?), photography treatment, illustration style (flat, line, 3D, isometric), icon family (stroke width, filled/outline, size), logos strip treatment (grayscale, opacity).
9. **Components signature:** buttons (height, padding, radius, icon placement), inputs, cards (padding, header/body/footer), nav (sticky, blur, border), footer (columns, density), badges, tabs, tables, code blocks.
10. **Motion cues:** entrance reveals, parallax, marquee, hover lifts, gradient animations, cursor effects. Anything animated should be rebuilt, not ignored.
11. **Responsive moves:** what collapses, stacks, hides, scales (hero type, nav to menu, grid to single column, section padding).
12. **Dark mode:** pure black vs tinted, elevation by lightness vs borders, accent adjustments, image treatments.

## Estimating when you only have pixels
- Spacing: measure gaps in px against a known size (button height ~40-48, body text ~16). Snap to 4 or 8 multiples.
- Font size: x-height / cap-height against a known size; compare with a rendered sample in the candidate font.
- Colors: sample with `image_palette.py --sample`, never by eye. Check text/background contrast ratio.
- Radius: compare corner arc to element height (pill if arc = half height).
- Shadow: describe offset-y, blur, color alpha; start `0 1px 2px rgba(0,0,0,.06)` for subtle, `0 10px 30px -10px rgba(0,0,0,.2)` for soft.

## Vocabulary for the aesthetic summary
Pick specifics, not "clean and modern": technical-minimal, editorial/serif-led, brutalist/raw, playful/rounded, enterprise/dense, luxury/airy, glassy/gradient, dark-neon, paper/print-like, retro-terminal. Name the signature details (e.g. "1px hairline borders, no shadows until hover, mono micro-labels, one electric accent used only on CTAs").
