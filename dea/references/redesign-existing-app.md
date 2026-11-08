# Redesigning an existing app with an extracted design

Rule one: change how it looks, not what it does. Preserve behavior, routes, data flow, copy (unless asked), accessibility, and tests.

## Steps
1. **Scan the project:** `python3 scripts/scan_project.py <dir>`. Note framework, styling system, token files, component folders, routes, hardcoded colors, fonts. Read 3-5 representative components and the global stylesheet.
2. **Capture "before":** run the app and `extract.mjs http://localhost:PORT --shots-only --out design/before` (or take screenshots) so you can show before/after and detect regressions.
3. **Capture the reference design** (see `extraction-playbook.md`) and refine `DESIGN.md`.
4. **Agree the adaptation level** (see `brand-fusion.md`): full adoption, structure only, palette swap, or blend. Default when the user says "use X's design": adopt tokens + component styling + layout patterns, keep the user's brand name, logo, copy and content.
5. **Plan the migration** in one short list: token files to add, global CSS to change, primitives to restyle, screens in order of traffic. Keep a running changelog in `design/CHANGELOG.md`.
6. **Pass 1: tokens and fonts.** Add `tokens.css`, theme config, fonts. Map old tokens to new in one table (old -> new) and replace in bulk where safe. Keep old variable names as aliases to avoid a flag day (`--old-bg: var(--background)`), remove aliases at the end.
7. **Pass 2: shell.** Header/nav, footer, page container, global typography, links, focus rings.
8. **Pass 3: primitives.** Button, input, select, checkbox/radio/switch, card, badge, modal, dropdown, tabs, tooltip, toast, table, empty states, skeletons. If the app uses a UI library (shadcn, MUI, Chakra, Mantine), theme it instead of rewriting components.
9. **Pass 4: screens.** One at a time, highest-traffic first. Replace hardcoded colors/spacings with tokens, align layout with the reference's anatomy where the screen type matches (landing, pricing, dashboard, settings, auth, list/detail).
10. **Pass 5: motion, responsive, dark mode, polish.** Hover/focus/active/disabled states everywhere, loading and empty states, mobile layouts, dark theme if the app has or should have one.
11. **Verify:** build, lint, type-check, run tests; screenshot every changed screen at desktop/tablet/mobile (and dark) and compare with the reference system using `compare.py` for visual consistency; check contrast with the DESIGN.md contrast table; check no layout shift or overflow; click through key flows.
12. **Deliver:** summary of what changed, before/after screenshots, files touched, assumptions, anything intentionally not adopted, and follow-ups.

## Mapping old to new (template)
| Old token/value | Role | New token |
|---|---|---|
| `#0a84ff` buttons | primary | `var(--primary)` |
| `16px` radius cards | radius | `var(--radius-lg)` |
| `Poppins` | heading font | `var(--font-heading)` |

## Safety
- Work on a branch or copy; commit per pass if git is available.
- Do not change business logic, API calls, state management, routing, or analytics while restyling.
- Keep ARIA, keyboard behavior and focus management; improve it if the reference system has better focus styling.
- Do not delete user content or assets.
- If a reference pattern conflicts with usability or accessibility (tiny text, low contrast), keep the look but fix the problem and say so.
