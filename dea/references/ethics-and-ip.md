# Responsible use: what to copy and what not to

Design systems are not secret: color palettes, type scales, spacing, layouts, and interaction patterns are routinely studied and reused as inspiration. Rebuilding *your* product in a similar visual language is normal. Copying someone's brand, assets, or identity is not.

## Fine to reproduce
- Color values, type scale, spacing, radius, shadows, motion timing, grid and layout patterns, component proportions, interaction patterns.
- Open-licensed fonts and icon sets (Inter, Geist, IBM Plex, Lucide, Heroicons, etc.).
- The overall aesthetic as a starting point for the user's own product.

## Do not copy
- Logos, wordmarks, trademarks, brand names, taglines, product names.
- Photography, illustrations, videos, custom icons, 3D assets, Lottie files.
- Proprietary or licensed font files (use open alternatives; see `rebuild-guide.md`).
- Verbatim marketing copy, documentation, or legal text.
- Source code, markup structure, class names, or scripts lifted from the site. Build your own.

## Do not do
- Build deceptive look-alikes: phishing or credential-collecting pages, fake login screens, pages that pass as another company's site or product, fake support or checkout pages.
- Imply affiliation or endorsement. No "official" claims, no copied trust badges, no reuse of another brand's name in titles/metadata.
- Bypass access controls: no defeating paywalls, bot protection, logins, or rate limits. Capture only publicly visible pages (or ones the user is authorized to access via their own session).
- Hammer a server: the extractor loads a handful of pages; keep crawls small and polite.

## When the user wants "an exact copy of site X"
- If it is **their own** site/app: proceed fully, they own it.
- If it is **someone else's**: build a design-faithful redesign with the user's brand, copy and assets (levels 1-4 in `brand-fusion.md`), explain briefly that logos, imagery, fonts and copy are replaced, and offer open alternatives. Decline requests whose purpose is impersonation or deception.
- For client work, suggest confirming the client is comfortable with how close the result is to the reference.

## Notes to include in deliverables
- Source of the extracted tokens (URL, date) and that they are a design reference.
- Fonts substituted, assets replaced, and any licensed material the user must source themselves.
