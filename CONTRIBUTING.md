# Contributing

Thanks for helping make DEA better.

## Setup
```bash
git clone https://github.com/obaid1dev/dea.git && cd dea
npm i && npx playwright install chromium     # for the browser tests
pip install pillow                           # for the image tool tests
python3 -m unittest discover -s tests -v
```

## Good contributions
- **Extraction accuracy:** new detections in `dea/scripts/inpage.js` (components, section kinds, tech hints, effects such as grain, glass, marquee).
- **Role inference:** better palette/typography/spacing heuristics in `synthesize.py`. Add a fixture or test case that fails first.
- **Stack guides:** Vue, Svelte, Astro, SwiftUI, Compose recipes in `references/rebuild-guide.md`.
- **Hard cases:** playbook notes for sites that break capture (and how to handle them politely).
- **Docs and examples:** more worked examples with original, fictional pages.

## Rules
- Examples and fixtures must be **original or fictional**. Never commit another company's logos, copy, images, fonts or markup.
- No network calls in scripts except `extract.mjs` (page capture) and `fetch_assets.py` (the page the user names).
- Python scripts: standard library only (Pillow is optional and only for the two image tools). Keep Python 3.9+ compatible (no nested same-quote f-strings, no `match`).
- Keep `dea/SKILL.md` under 500 lines and its `description` under 1024 characters; the tests check this.
- Never weaken the responsible-use guidance (no deceptive look-alikes, no brand-asset copying, no bypassing protections).

## Pull requests
Describe the site type or case you improved, what the extractor saw before and after, and include test updates. Run the full test suite before opening the PR.
