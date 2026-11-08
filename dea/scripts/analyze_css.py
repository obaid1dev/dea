#!/usr/bin/env python3
"""
DEA static fallback: build a raw.json from saved HTML/CSS files (no browser needed).

Use when no browser is available (e.g. only web_fetch / curl). Less accurate than extract.mjs because
nothing is rendered: no computed styles, no area weighting, no hover capture, CSS-in-JS is invisible.
Output uses the same schema under key "static" so synthesize.py works unchanged.

  python analyze_css.py <dir-or-files...> --out raw.json [--url https://site]
"""
import argparse, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|rgba?\([^)]+\)|hsla?\([^)]+\)|oklch\([^)]+\)")
TAGS = ["h1", "h2", "h3", "h4", "h5", "h6", "p", "a", "button", "code", "pre", "small", "label", "li"]


def strip_comments(s): return re.sub(r"/\*.*?\*/", "", s, flags=re.S)


def blocks(css):
    """Yield (context, selector, body) for nested at-rules (one level of media/supports/layer)."""
    css = strip_comments(css); out = []; i = 0
    def parse(text, ctx):
        pos = 0
        while pos < len(text):
            o = text.find("{", pos)
            if o < 0: break
            sel = text[pos:o].strip(); depth = 1; j = o + 1
            while j < len(text) and depth:
                depth += (text[j] == "{") - (text[j] == "}"); j += 1
            body = text[o + 1:j - 1]
            if sel.startswith("@media") or sel.startswith("@supports") or sel.startswith("@layer"): parse(body, sel)
            elif sel.startswith("@font-face"): out.append((ctx, "@font-face", body))
            elif sel.startswith("@keyframes") or sel.startswith("@-webkit-keyframes"): out.append((ctx, sel, body))
            elif sel.startswith("@"): pass
            else: out.append((ctx, sel, body))
            pos = j
    parse(css, ""); return out


def decls(body):
    for m in re.finditer(r"([\w-]+)\s*:\s*([^;]+);?", body):
        yield m.group(1).strip().lower(), m.group(2).strip().rstrip("}")


def to_px(v):
    m = re.fullmatch(r"(-?[\d.]+)(px|rem|em)?", v.strip())
    if not m: return None
    n = float(m.group(1)); return n * (16 if m.group(2) in ("rem", "em") else 1) if m.group(2) else (n if n == 0 else None)


def analyze(texts, url=None):
    parts, raw_html = [], ""
    for t in texts:
        if re.search(r"<(html|head|body|style)\b", t, re.I):
            raw_html += t
            parts += re.findall(r"<style[^>]*>(.*?)</style>", t, flags=re.S | re.I)
        else:
            parts.append(t)
    css = "\n".join(parts)
    bl = blocks(css)
    # pass 1: collect root-level custom properties so var() can be substituted
    rootvars = {}
    for ctx, sel, body in bl:
        if sel.strip() in (":root", "html", ":host") and "prefers-color-scheme" not in ctx:
            for p_, v_ in decls(body):
                if p_.startswith("--"): rootvars[p_] = v_
    def subst(v, depth=0):
        if depth > 5: return v
        return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]+))?\)", lambda m: subst(rootvars.get(m.group(1), m.group(2) or m.group(0)), depth + 1), v)
    cssvars, bgs, txt, brd = defaultdict(dict), Counter(), Counter(), Counter()
    spacing, radii, shadows, trans, typo, faces, kfs, bps = Counter(), Counter(), Counter(), Counter(), {}, [], [], Counter()
    grads, durs = Counter(), Counter()
    for ctx, sel, body in bl:
        if ctx:
            for m in re.finditer(r"(min|max)-width:\s*([\d.]+)(px|em|rem)", ctx): bps[f"{m.group(1)}:{round(float(m.group(2)) * (1 if m.group(3) == 'px' else 16))}"] += 1
        if sel == "@font-face":
            d = dict(decls(body)); faces.append({"family": d.get("font-family", "").strip("\"' "), "weight": d.get("font-weight", "400"), "style": d.get("font-style", "normal"), "display": d.get("font-display"), "src": re.sub(r"\s+", " ", d.get("src", ""))[:200]}); continue
        if sel.startswith("@") and "keyframes" in sel: kfs.append({"name": sel.split()[-1], "css": re.sub(r"\s+", " ", body)[:700]}); continue
        key = ("@dark " if "prefers-color-scheme: dark" in ctx or "prefers-color-scheme:dark" in ctx else "") + sel
        ent = {}
        for p, v in decls(body):
            if p.startswith("--"): cssvars[key][p] = v; continue
            if "var(" in v and "color-mix" not in v: v = subst(v)
            if p == "font":
                fm = re.match(r"(?:(\d{3}|bold|normal)\s+)?([\d.]+(?:px|rem|em))(?:/([\d.]+(?:px|rem|em)?))?\s+(.+)", v)
                if fm:
                    if fm.group(1): ent["font-weight"] = fm.group(1)
                    ent["font-size"] = fm.group(2)
                    if fm.group(3): ent["line-height"] = fm.group(3)
                    ent["font-family"] = fm.group(4)
            ent[p] = v
            if p in ("background", "background-color"):
                if "gradient" not in v:
                    for c in COLOR.findall(v): bgs[c.lower()] += 1
                if "gradient" in v: grads[v[:240]] += 1
            elif p == "color":
                for c in COLOR.findall(v): txt[c.lower()] += 1
            elif p.startswith("border") and "radius" not in p:
                for c in COLOR.findall(v): brd[c.lower()] += 1
            elif p.startswith("border") and p.endswith("radius"):
                for x in v.split():
                    n = to_px(x)
                    if n: radii["full" if n >= 999 else str(round(n, 1))] += 1
            elif p in ("padding", "margin", "gap", "row-gap", "column-gap") or re.fullmatch(r"(padding|margin)-(top|bottom|left|right)", p):
                if "margin" in p and not re.search(r"top|bottom|^margin$", p): continue
                for x in v.split():
                    n = to_px(x)
                    if n and 1 < n <= 400: spacing[round(n, 1)] += 1
            elif p == "box-shadow" and v != "none": shadows[v] += 1
            elif p in ("transition", "transition-duration"):
                for m in re.finditer(r"([\d.]+)(ms|s)\b", v): durs[round(float(m.group(1)) * (1 if m.group(2) == "ms" else 1000))] += 1
                pm = re.match(r"([a-z-]+)\s+[\d.]+m?s\s*(.*)", v)
                trans[(pm.group(1) if pm else "all", (pm.group(2) if pm else "ease") or "ease", durs and max(durs, key=durs.get) or 0)] += 1
        # typography per rule
        if "font-size" in ent or "font-family" in ent:
            fs = to_px(ent.get("font-size", "")) if "font-size" in ent else None
            tags = {t: 1 for t in TAGS if re.search(rf"(^|[\s,>+~]){t}($|[\s,.:#\[>+~])", sel)} or {"div": 1}
            fam = ent.get("font-family", "").split(",")[0].strip("\"' ")
            if fam in ("inherit", "initial", "unset") or (not fs and not fam): continue
            lh = ent.get("line-height", ""); lhr = float(lh) if re.fullmatch(r"[\d.]+", lh) else None
            ls = ent.get("letter-spacing", ""); lse = (float(ls[:-2]) if ls.endswith("em") else 0)
            k = (fam, fs, ent.get("font-weight"), lhr, lse)
            e = typo.setdefault(k, {"family": fam or "inherit", "stack": ent.get("font-family", "")[:160], "size": fs, "weight": int(ent["font-weight"]) if str(ent.get("font-weight", "")).isdigit() else ent.get("font-weight", 400), "lineHeight": None, "lineHeightRatio": lhr, "letterSpacing": 0, "letterSpacingEm": lse, "transform": ent.get("text-transform", "none"), "fontStyle": "normal", "chars": 0, "count": 0, "tags": {}, "sample": sel[:40], "colors": []})
            e["chars"] += 10; e["count"] += 1
            for t in tags: e["tags"][t] = e["tags"].get(t, 0) + 1
    # resolved root vars
    n_bg = sum(bgs.values()) or 1
    colors = {"background": [{"value": c, "weight": round(n / n_bg, 4)} for c, n in bgs.most_common(24)], "text": [{"value": c, "chars": n} for c, n in txt.most_common(24)],
              "border": [{"value": c, "count": n} for c, n in brd.most_common(12)], "svgFill": [], "gradients": [{"value": g, "count": n} for g, n in grads.most_common(8)]}
    bodyrule = next((dict(decls(b)) for c, s, b in bl if re.fullmatch(r"(html\s*,\s*)?body", s.strip())), {})
    return {"meta": {"url": url, "title": None, "prefersDarkRules": any("@dark" in k for k in cssvars), "darkClassSelectors": [k for k in cssvars if re.search(r"\.dark|data-theme", k)][:5]},
            "techHints": ["static CSS analysis (no render)"], "cssVariables": dict(cssvars), "rootResolved": rootvars, "fonts": {"fontFaces": faces[:40], "loaded": [], "links": re.findall(r'href="([^"]*(?:fonts\.googleapis|fonts\.bunny|typekit|fontshare)[^"]*)"', css)[:6]},
            "colors": colors, "typography": sorted(typo.values(), key=lambda t: -t["chars"])[:70], "spacing": [{"px": k, "count": v} for k, v in spacing.most_common(40)],
            "radii": [{"value": k, "count": v} for k, v in radii.most_common(14)], "borders": [], "shadows": {"box": [{"value": k, "count": v} for k, v in shadows.most_common(14)], "text": [], "filter": [], "backdrop": []},
            "motion": {"transitions": [{"property": p, "duration": f"{d}ms", "easing": e, "count": n} for (p, e, d), n in trans.most_common(20)], "animations": [], "keyframes": kfs[:30], "scrollBehavior": None},
            "layout": {"rootFontSize": "16px", "bodyFont": (subst(bodyrule.get("font-family") or "")).split(",")[0].strip("\"' "), "bodyBackground": subst(bodyrule.get("background-color") or bodyrule.get("background") or ""), "bodyColor": subst(bodyrule.get("color") or ""), "containerMaxWidths": [], "grids": [], "header": None, "stickyOrFixed": [], "zIndexes": []},
            "sections": [], "components": {}, "breakpoints": bps.most_common(14), "stateRules": {"total": 0, "sample": []}, "contrast": [], "assets": {}, "stylesheets": {"count": 0}}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("paths", nargs="+"); ap.add_argument("--out", default="raw.json"); ap.add_argument("--url")
    a = ap.parse_args(); texts = []
    for p in a.paths:
        pp = Path(p)
        files = [f for f in pp.rglob("*") if f.suffix.lower() in (".css", ".html", ".htm", ".scss")] if pp.is_dir() else [pp]
        for f in files: texts.append(f.read_text(errors="ignore"))
    if not texts: sys.exit("no css/html files found")
    d = analyze(texts, a.url)
    Path(a.out).write_text(json.dumps({"tool": "dea/analyze_css", "version": "1.0.0", "url": a.url, "static": d, "notes": ["Static analysis only: no rendering, no computed styles, no screenshots. Verify visually."]}, indent=1))
    print(f"Wrote {a.out}: {len(d['cssVariables'])} var scopes, {len(d['typography'])} type styles, {len(d['colors']['background'])} bg colors")


if __name__ == "__main__":
    main()
