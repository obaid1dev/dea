# Applying a design to someone else's content (brand fusion)

Decide the adaptation level before building. If the user did not specify, choose the default and state it in one sentence.

| Level | What you take from the reference | What stays the user's | Use when |
|---|---|---|---|
| **1. Full system (default)** | Colors, type, spacing, radius, shadows, motion, component styling, layout patterns, page anatomy | Brand name, logo, copy, imagery, product content | "Redesign my app using X's design", "make it look like X" |
| **2. Structure and feel** | Layout, spacing, type scale, motion, component shapes | The user's palette and fonts | "Same layout/feel as X but my brand colors" |
| **3. Palette and type only** | Colors, fonts (or alternatives) | Existing layout and components | "Use X's colors and fonts" |
| **4. Blend** | Chosen aspects from 2+ references | Content, brand | "Linear's layout with Stripe's color softness" |
| **5. Inspired-by** | Principles (restraint, whitespace, tracking) rebuilt originally | Everything concrete | Public-facing client work where lookalike risk matters |

## Rules
- The user's **identity** (name, logo, tagline, product copy) always replaces the reference's. Never leave the reference brand's name, logo, trademarks or distinctive copy in the output.
- Map reference roles onto the user's needs: their primary action gets the reference's primary style; their data tables/forms use the reference's input and table styles; if the reference lacks a component the product needs (data table, chart, calendar), extend it using the system's rules (same radius, borders, spacing, type roles) and say you extrapolated.
- If the user's brand color must stay, derive the full role set around it (foreground on it, hover, soft tint, ring) and re-check contrast; keep the reference's usage pattern (where and how much accent).
- Blending: pick one source of truth per axis (e.g. layout from A, color from B, motion from A) and write the mapping at the top of `DESIGN.md`. Avoid mixing radii or type scales from different systems inside one screen.
- Mismatch of domain (consumer playful vs enterprise dense): keep the system, adjust density and copy tone, flag the tension.
- Always preserve accessibility: if the reference fails contrast (light gray text), keep the vibe but meet AA for body text, and note it.
- When asked for an exact visual clone of a site the user does not own, build the design-faithful version with the user's own content and branding (levels 1-4) rather than a deceptive copy; see `ethics-and-ip.md`.
