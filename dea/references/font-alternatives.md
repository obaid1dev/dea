# Font alternatives (starting points)

When a site uses a proprietary or unavailable font, use an open-licensed near match, then tune size, weight, line-height and tracking until line breaks and optical size match the screenshot. These are suggestions to verify visually, not exact matches.

| Reference (typical) | Open alternative | Notes |
|---|---|---|
| SF Pro / system-ui, Helvetica Neue, Arial, Graphik, Söhne, Neue Haas Grotesk | Inter | Tight neutral grotesque; reduce tracking slightly for display sizes |
| Geist | Geist (open source) | Use directly via `next/font` or the package |
| GT America | Instrument Sans | Slightly warmer |
| Circular | DM Sans | Geometric, friendly |
| Avenir / Avenir Next | Nunito Sans | |
| Proxima Nova | Figtree | |
| Gotham | Montserrat | Wider; reduce weight one step |
| Futura | Jost | |
| GT Walsheim | Outfit | |
| Aeonik | Hanken Grotesk | |
| Tiempos, Georgia, Freight Text | Source Serif 4 | Editorial serif |
| Canela, GT Super, Recoleta | Fraunces | Soft display serif |
| SF Mono, Menlo, Consolas | JetBrains Mono, Geist Mono, IBM Plex Mono | |
| IBM Plex, Manrope, Poppins, Space Grotesk, DM Sans | same (all open) | Use directly |

Process: install the alternative, render the same headline at the same size/width, compare line wraps and x-height to the reference screenshot, adjust `font-size`, `letter-spacing`, `font-weight` (variable fonts allow in-between weights), and `line-height`.

Always check the license of any font you ship. Google Fonts families are OFL/Apache licensed and safe to self-host.
