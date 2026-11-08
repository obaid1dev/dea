# Building with an extracted design

Order of work: tokens -> fonts -> global styles -> layout shell -> primitives -> sections -> pages -> motion -> responsive -> dark mode -> verify. Do not start with pages; they inherit everything from the first four steps.

## Contents
1. Setup per stack
2. Fonts
3. Global styles and layout shell
4. Primitives (recipes)
5. Sections and page assembly
6. Motion
7. Responsive and dark mode
8. Content, imagery and icons
9. Fidelity loop
10. Pitfalls

## 1. Setup per stack
- **Plain HTML/CSS:** link `tokens.css`, write `base.css` that applies tokens to `html, body, h1..h6, a, button, input`, then component classes using only variables.
- **Tailwind v3:** import `tokens.css` globally, merge `tailwind.config.js` theme.extend. Use semantic classes (`bg-background text-foreground bg-primary text-primary-foreground rounded-lg shadow-md`).
- **Tailwind v4:** `@import "tailwindcss";` then `@import "./tokens.css";` and `@import "./tailwind-v4.css";` (the `@theme` block). Dark: class strategy via the provided `@custom-variant`.
- **shadcn/ui:** semantic variable names already match; paste into `:root` and `.dark`, set `--radius`, then restyle `ui/button|card|input|badge|dialog|dropdown-menu|tabs` to the extracted specs (heights, padding, radius, weights, hover).
- **Next.js:** fonts via `next/font` (Google or local), tokens in `app/globals.css`.
- **React Native / Expo:** generate `theme.ts` from `tokens.json` (colors, spacing = unit multiples, radius, typography). Load fonts with `expo-font` / `@expo-google-fonts/*`. CSS shadows become `shadowColor/Offset/Opacity/Radius` + `elevation`; no `backdrop-filter` without a blur library (`expo-blur`); gradients via `expo-linear-gradient`.
- **Flutter:** `ColorScheme` + `TextTheme` + `ThemeData` from tokens; `google_fonts`.
- **Vue/Svelte/Astro:** same as plain CSS plus scoped component styles using variables.

## 2. Fonts
- Check `tokens.json > fonts`. Open-licensed families: self-host or use Google Fonts. Proprietary: use the listed `openAlternative` and tune size/weight/tracking to match optical size; say so in the summary.
- Match metrics: set `font-size-adjust` or adjust line-height; verify headline line breaks match the reference (same wrap width).
- Load only needed weights; `font-display: swap`; preload the main one.

## 3. Global styles and layout shell
- `html { font-size: 16px }`, body font/size/line-height/color/background from tokens, `-webkit-font-smoothing: antialiased`.
- Container: `max-width: var(--container-max)`, side padding from the measured gutter (or 24px desktop / 16-20px mobile).
- Header: copy measured position (sticky/fixed), height, background (+ blur), border, padding, link style, CTA placement.
- Vertical rhythm: section padding from `--section-padding-y`; consistent inner gaps from the spacing scale.
- Footer: columns, density, link color, border-top.

## 4. Primitives (build once, reuse everywhere)
- **Button:** height, padding-x, radius, font weight/size/tracking, variants (primary, secondary, outline, ghost, destructive), icon gap, hover (measured diff), focus-visible ring, active/disabled, loading.
- **Input/Textarea/Select:** height, padding, radius, border, placeholder color, focus ring (color, width, offset or shadow), error and disabled states, label style.
- **Card:** padding, radius, border or shadow, bg, hover treatment, internal structure (media, title, body, footer).
- **Badge/Pill, Tabs, Tooltip, Dialog, Dropdown, Table, Code block, Avatar, Skeleton, Toast** as the product needs; style from the nearest measured component.
- **Icons:** same family and stroke width as measured (`components.icons`), size grid (16/20/24), color via `currentColor`.

## 5. Sections and page assembly
Use `DESIGN.md > Page anatomy` as the wireframe: same section order, heights, alignment and column counts. Typical blocks: nav, hero (headline + sub + CTAs + visual), logo strip, feature grid, product showcase, testimonials, pricing, FAQ, CTA band, footer. Replace the original's copy and brand assets with the user's content or neutral placeholders.

## 6. Motion
Reproduce measured durations/easings, hover lifts/shadows, entrance animations (copy keyframes' shape, not necessarily names), scroll reveals (IntersectionObserver + CSS), sticky header blur on scroll. Respect `prefers-reduced-motion`. Heavy effects (WebGL, Lottie, parallax libs) only if the original clearly depends on them; otherwise approximate with CSS.

## 7. Responsive and dark mode
- Use the extracted breakpoints; follow measured behavior (nav to menu, grid to stack, type scale-down, section padding changes). Use `clamp()` for fluid type when the reference scales continuously.
- Dark: implement the extracted dark roles with the detected strategy (media or class). Re-check contrast, shadows (often replaced by borders), and images.

## 8. Content, imagery and icons
- Use the user's copy, logo and images. Without them use realistic placeholder text (not lorem ipsum if avoidable) and neutral shapes/gradients. Do not hotlink or copy the original's images, SVG logos or illustrations.
- Mimic the *treatment* (frame, radius, shadow, aspect ratio, grayscale logos) with your own assets.

## 9. Fidelity loop (do this, max 3 rounds)
1. Run the rebuild locally and capture it with the same viewports: `node scripts/extract.mjs http://localhost:3000 --shots-only --out design/rebuild`.
2. `python3 scripts/compare.py design/<site>/screenshots/desktop-full.png design/rebuild/screenshots/desktop-full.png --out design/compare` then open `side-by-side.png`.
3. Fix the worst bands first: wrong container width, section padding, type size/line-height, color roles, radius, shadow. Re-run. Repeat for mobile and dark.
4. Accept when structure, spacing, type hierarchy and color relationships match; content will differ.

## 10. Pitfalls
- Building pages before tokens/primitives (drifts immediately).
- Rounding values "to be tidy" and losing the character of the system.
- Copying class names or markup from the source; build your own structure.
- Ignoring hover/focus/disabled/empty/loading states.
- Forgetting the mobile layout or dark mode when the reference has them.
- Letting low-contrast pairs through without noting them.
- Pixel-chasing content differences instead of system differences.
