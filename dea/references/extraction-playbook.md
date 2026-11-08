# Extraction playbook

Goal: capture enough of the target's design to rebuild it faithfully. Measured data first, then your eyes on the screenshots. Never guess a hex value, size or font from memory.

## Contents
1. Resolve the target
2. Pick the capture tier
3. Tier A: Playwright (best)
4. Tier B: a browser tool you already have
5. Tier C: static fallback
6. Tier D: screenshots only
7. What a complete capture contains
8. Hard cases
9. Output folder convention

## 1. Resolve the target
- URL given: use it. Use the homepage plus 2-4 representative inner pages (pricing, docs/blog, a form/app screen) because marketing and product surfaces often differ.
- Only a name ("Vercel", "Linear", "Stripe"): web-search for the official site, confirm the domain, then proceed. Prefer the product site over a blog or docs subdomain unless the user asked for those.
- Several targets (blend): capture each into its own folder `design/<site>/`.
- A running local app (user's own): use `http://localhost:PORT` as a target for the "before" capture.
- Screenshots or a Figma export only: go to Tier D.

## 2. Pick the capture tier
Try in order; stop at the first that works and say which tier you used.
| Tier | Needs | Gives you |
|---|---|---|
| A. `extract.mjs` | Node + Playwright/Chromium and network | Everything: rendered computed styles, screenshots at 3 viewports, dark mode, hover/focus, extra pages, network fonts |
| B. Browser tool | Claude in Chrome, Playwright MCP, DevTools MCP, or any tool that can run JS in a page and screenshot | Same data via `inpage.js`, screenshots from the tool |
| C. Static | `web_fetch`/curl only | CSS variables, colors, fonts, radii, shadows, motion declared in CSS. No render, no states |
| D. Screenshots | Images from the user or a screenshot tool | Palette by pixel sampling, layout and type read visually |
Be explicit about limits of lower tiers in the final notes.

## 3. Tier A: Playwright
```bash
# once: npm i -D playwright && npx playwright install chromium
node scripts/extract.mjs https://example.com --out design/example
python3 scripts/synthesize.py design/example/raw.json --out design/example --name "Example"
```
Useful flags: `--pages /pricing,/docs` (specific routes), `--crawl 3` (follow nav links), `--auth state.json` (logged-in screens; create with `npx playwright codegen --save-storage=state.json URL`), `--headed` (bot checks), `--no-dark`, `--viewport 1280x800`.
It scrolls the page to trigger lazy content, dismisses cookie banners, waits for fonts, and records tokens, section anatomy, component variants, hover/focus diffs, breakpoints, network fonts, and screenshots (`desktop`, `tablet`, `mobile`, per-section, dark).

## 4. Tier B: browser tool
1. Navigate, wait for load, scroll through the page once (lazy content), return to top.
2. Evaluate the full text of `scripts/inpage.js` in the page and save the returned JSON as `raw.json` shape `{ "light": <result> }` (add `"url"`).
3. Screenshots: viewport at 1440 wide, full page, 820 (tablet), 390 (mobile); a dark-mode shot if the site has one (toggle the theme or emulate `prefers-color-scheme`).
4. Hover the primary button, a nav link and a card; note what changes (color, shadow, transform).
5. Run `synthesize.py` on the saved file.
Browser tools often truncate large return values: if so, evaluate and print one top-level key at a time (`colors`, `typography`, `components`, ...) and assemble the JSON.

## 5. Tier C: static fallback
```bash
python3 scripts/fetch_assets.py https://example.com --out design/example/src
python3 scripts/analyze_css.py design/example/src --out design/example/raw.json --url https://example.com
python3 scripts/synthesize.py design/example/raw.json --out design/example
```
Blind spots: CSS-in-JS and runtime-injected styles, computed values, area weighting, states, screenshots. If the site is a JS-rendered app, expect thin results; try Tier A/B or ask for screenshots.

## 6. Tier D: screenshots only
- Ask for (or take) a desktop full page, a mobile view, and close-ups of buttons/cards/forms if available.
- `python3 scripts/image_palette.py shot.png --colors 8 --sample X,Y ... --grid 6x4` to measure real colors: background, surfaces, text, accent, borders.
- Read type and spacing from the pixels (see `visual-analysis.md`); identify likely font families, mark confidence low.
- Write tokens by hand into `DESIGN.md`; flag everything as estimated.

## 7. What a complete capture contains
Palette with roles (+dark), type families/scale/weights/tracking, spacing base and section rhythm, radius scale, borders, shadows/elevation, motion durations/easings and hover patterns, layout (container, grid, header behavior, breakpoints), components (buttons, inputs, cards, badges, nav, footer, icons), page anatomy, responsive behavior, assets style (photo/illustration/icon), tech hints, and a list of unknowns.

## 8. Hard cases
- **Bot protection / 403 / CAPTCHA:** try `--headed`; do not attempt to defeat protections. Fall back to user screenshots.
- **Login-walled apps:** user supplies `--auth` state or screenshots. Never ask for passwords.
- **SPA with route transitions:** pass routes via `--pages`; wait longer with `--wait 1500`.
- **Canvas/WebGL/3D heavy sites:** DOM tokens capture the chrome only; describe the hero visual from screenshots/video frames and rebuild it with CSS/SVG/three.js separately.
- **Cross-origin stylesheets blocked in-page:** computed styles still work; variable names may be missing. Tier A `network` lists the CSS URLs; fetch with Tier C to recover names.
- **Fonts:** check `tokens.json > fonts` for source. Self-hosted proprietary fonts: do not copy files; use the open alternative.
- **Cookie banners, modals in screenshots:** re-run with `--keep-banners` off (default dismisses), or crop around them.
- **A/B tests and geolocated variants:** note which variant you captured.

## 9. Output folder convention
```
design/<site>/
  raw.json            measured capture
  tokens.json         roles + evidence + confidence
  tokens.css  tailwind.config.js  tailwind-v4.css
  DESIGN.md           the design system document (agent-refined)
  screenshots/        desktop-*, tablet-*, mobile-*, dark-*, section-*, page-*
```
