#!/usr/bin/env python3
"""
DEA fetch fallback: download a page's HTML and linked stylesheets (stdlib only) for analyze_css.py.

  python fetch_assets.py https://example.com --out ./site-src

Fallback for when no browser is available. Prefer extract.mjs (rendered, computed styles).
Polite: one request per file, identifies itself, caps at 30 stylesheets, follows one level of @import.
"""
import argparse, re, sys, urllib.request, urllib.parse
from pathlib import Path

UA = "Mozilla/5.0 (compatible; dea-design-extractor/1.0)"


def get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,text/css,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="ignore")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("url"); ap.add_argument("--out", default="site-src"); a = ap.parse_args()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    try: html = get(a.url)
    except Exception as e: sys.exit(f"fetch failed: {e}")
    (out / "index.html").write_text(html)
    hrefs = re.findall(r'<link[^>]+rel=["\']?stylesheet["\']?[^>]*href=["\']([^"\']+)["\']', html, flags=re.I) + re.findall(r'<link[^>]+href=["\']([^"\']+\.css[^"\']*)["\']', html, flags=re.I)
    seen = []; n = 0
    for h in hrefs:
        u = urllib.parse.urljoin(a.url, h)
        if u in seen or n >= 30: continue
        seen.append(u)
        try:
            css = get(u); n += 1; (out / f"style-{n:02d}.css").write_text(f"/* {u} */\n" + css)
            for imp in re.findall(r"@import\s+(?:url\()?['\"]?([^'\")\s;]+)", css)[:5]:
                iu = urllib.parse.urljoin(u, imp)
                if iu not in seen and n < 30:
                    seen.append(iu)
                    try: n += 1; (out / f"style-{n:02d}.css").write_text(f"/* {iu} */\n" + get(iu))
                    except Exception: pass
        except Exception as e: print("skip", u, e, file=sys.stderr)
    print(f"Saved index.html + {n} stylesheet(s) to {out}\nNext: python3 analyze_css.py {out} --out raw.json --url {a.url}\n"
          "Note: CSS-in-JS and JS-injected styles are not captured; confirm visually with screenshots.")


if __name__ == "__main__":
    main()
