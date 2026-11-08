#!/usr/bin/env python3
"""
DEA synthesizer: turn raw extraction (extract.mjs or analyze_css.py) into a design system.

Usage:
  python synthesize.py raw.json --out ./design [--name "Site Name"]

Writes:
  tokens.json          every token with evidence + confidence (machine-readable source of truth)
  tokens.css           CSS variables (shadcn-compatible semantic names + type/space/radius/shadow/motion), light + dark
  site-variables.css   the site's own custom properties, resolved (to mirror its naming)
  tailwind.config.js   Tailwind v3 theme extension (references the CSS variables)
  tailwind-v4.css      Tailwind v4 @theme block
  DESIGN.md            human/agent-readable design system with auto-drafted summary and TODO markers

The numbers here are measured, the *naming and roles* are inferred (confidence is recorded).
The agent must still LOOK at the screenshots and correct anything that does not match.
"""
import argparse
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

# ----------------------------------------------------------------------------- colors
NAMED = {"white": "#ffffff", "black": "#000000", "transparent": "#00000000", "red": "#ff0000", "blue": "#0000ff", "green": "#008000"}


def _hsl_to_rgb(h, s, l):
    h = (h % 360) / 360.0
    if s == 0:
        v = round(l * 255); return (v, v, v)
    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q

    def f(t):
        t %= 1
        if t < 1 / 6: return p + (q - p) * 6 * t
        if t < 1 / 2: return q
        if t < 2 / 3: return p + (q - p) * (2 / 3 - t) * 6
        return p
    return tuple(round(f(h + d) * 255) for d in (1 / 3, 0, -1 / 3))


def _oklch_to_rgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bl = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s

    def gm(v):
        v = max(0.0, min(1.0, v))
        return 12.92 * v if v <= 0.0031308 else 1.055 * (v ** (1 / 2.4)) - 0.055
    return tuple(round(gm(v) * 255) for v in (r, g, bl))


def parse_color(s):
    """Return (r,g,b,a) or None. Handles hex, rgb(a), hsl(a), oklch, shadcn 'H S% L%' triplets."""
    if s is None: return None
    s = str(s).strip().lower()
    s = NAMED.get(s, s)
    m = re.fullmatch(r"#([0-9a-f]{3,8})", s)
    if m:
        h = m.group(1)
        if len(h) in (3, 4): h = "".join(c * 2 for c in h)
        if len(h) in (6, 8):
            r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
            return (r, g, b, round(int(h[6:8], 16) / 255, 3) if len(h) == 8 else 1.0)
        return None
    m = re.fullmatch(r"rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)", s)
    if m:
        a = 1.0 if m.group(4) is None else (float(m.group(4)[:-1]) / 100 if m.group(4).endswith("%") else float(m.group(4)))
        return (round(float(m.group(1))), round(float(m.group(2))), round(float(m.group(3))), a)
    m = re.fullmatch(r"hsla?\(\s*([\d.]+)(?:deg)?[\s,]+([\d.]+)%[\s,]+([\d.]+)%(?:\s*[,/]\s*([\d.]+%?))?\s*\)", s)
    if m:
        a = 1.0 if m.group(4) is None else (float(m.group(4)[:-1]) / 100 if m.group(4).endswith("%") else float(m.group(4)))
        return (*_hsl_to_rgb(float(m.group(1)), float(m.group(2)) / 100, float(m.group(3)) / 100), a)
    m = re.fullmatch(r"([\d.]+)(?:deg)?\s+([\d.]+)%\s+([\d.]+)%(?:\s*/\s*([\d.]+%?))?", s)  # shadcn triplet
    if m:
        a = 1.0 if m.group(4) is None else (float(m.group(4)[:-1]) / 100 if m.group(4).endswith("%") else float(m.group(4)))
        return (*_hsl_to_rgb(float(m.group(1)), float(m.group(2)) / 100, float(m.group(3)) / 100), a)
    m = re.fullmatch(r"oklch\(\s*([\d.]+%?)\s+([\d.]+%?)\s+([\d.]+)(?:deg)?(?:\s*/\s*([\d.]+%?))?\s*\)", s)
    if m:
        L = float(m.group(1)[:-1]) / 100 if m.group(1).endswith("%") else float(m.group(1))
        C = float(m.group(2)[:-1]) / 100 * 0.4 if m.group(2).endswith("%") else float(m.group(2))
        a = 1.0 if m.group(4) is None else (float(m.group(4)[:-1]) / 100 if m.group(4).endswith("%") else float(m.group(4)))
        return (*_oklch_to_rgb(L, C, float(m.group(3))), a)
    return None


def to_hex(c):
    if not c: return None
    h = "#%02x%02x%02x" % (c[0], c[1], c[2])
    return h + ("%02x" % round(c[3] * 255) if c[3] < 0.999 else "")


def hx(s):
    c = parse_color(s); return to_hex(c) if c else None


def hsl(c):
    r, g, b = c[0] / 255, c[1] / 255, c[2] / 255
    mx, mn = max(r, g, b), min(r, g, b); l = (mx + mn) / 2
    if mx == mn: return (0.0, 0.0, l)
    d = mx - mn; s = d / (2 - mx - mn) if l > 0.5 else d / (mx + mn)
    h = ((g - b) / d + (6 if g < b else 0)) if mx == r else ((b - r) / d + 2 if mx == g else (r - g) / d + 4)
    return (h * 60, s, l)


def lum(c):
    def f(v):
        v /= 255; return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def contrast(a, b):
    l1, l2 = lum(a), lum(b)
    return round((max(l1, l2) + 0.05) / (min(l1, l2) + 0.05), 2)


def hue_name(h, s=1.0):
    if s < 0.1: return "neutral"
    for lim, n in [(15, "red"), (40, "orange"), (65, "amber"), (90, "yellow"), (150, "green"), (175, "teal"), (200, "cyan"), (225, "blue"), (255, "indigo"), (285, "violet"), (315, "purple"), (345, "pink"), (361, "red")]:
        if h < lim: return n
    return "red"


def opaque(c): return c and c[3] >= 0.9


# ----------------------------------------------------------------------------- helpers
def fnum(x, nd=2):
    return round(float(x), nd)


def px_of(v):
    if v is None: return None
    m = re.match(r"^-?[\d.]+", str(v))
    if not m: return None
    n = float(m.group(0))
    if str(v).endswith("rem") or str(v).endswith("em"): n *= 16
    return n


def first_family(stack):
    return (stack or "").split(",")[0].strip().strip("\"'")


SYSTEM_FONTS = {"system-ui", "-apple-system", "blinkmacsystemfont", "segoe ui", "roboto", "helvetica", "helvetica neue", "arial", "ui-sans-serif", "ui-serif", "ui-monospace", "sf mono", "menlo", "consolas", "courier new", "monospace", "sans-serif", "serif", "georgia", "times new roman", "sfmono-regular", "ui-rounded"}
OPEN_ALTS = {  # proprietary / unavailable -> close open-licensed starting points (verify visually)
    "sf pro": "Inter", "sf pro display": "Inter", "sf pro text": "Inter", "helvetica neue": "Inter", "helvetica": "Inter", "arial": "Inter", "söhne": "Inter", "sohne": "Inter", "graphik": "Inter",
    "gt america": "Instrument Sans", "circular": "DM Sans", "circular std": "DM Sans", "avenir": "Nunito Sans", "avenir next": "Nunito Sans", "proxima nova": "Figtree", "gotham": "Montserrat",
    "futura": "Jost", "gt walsheim": "Outfit", "neue haas grotesk": "Inter", "aeonik": "Hanken Grotesk", "mona sans": "Mona Sans", "sf mono": "JetBrains Mono", "menlo": "JetBrains Mono", "consolas": "JetBrains Mono",
    "tiempos": "Source Serif 4", "tiempos text": "Source Serif 4", "georgia": "Source Serif 4", "canela": "Fraunces", "gt super": "Fraunces", "freight text": "Source Serif 4", "recoleta": "Fraunces",
    "ibm plex sans": "IBM Plex Sans", "inter": "Inter", "geist": "Geist", "geist mono": "Geist Mono", "dm sans": "DM Sans", "manrope": "Manrope", "poppins": "Poppins", "space grotesk": "Space Grotesk",
}
RATIOS = [(1.067, "minor second"), (1.125, "major second"), (1.2, "minor third"), (1.25, "major third"), (1.333, "perfect fourth"), (1.414, "augmented fourth"), (1.5, "perfect fifth"), (1.618, "golden ratio")]

ROLE_NAMES = {
    "background": r"background|bg|bg-base|bg-default|bg-page|page|page-bg|canvas|body-bg|background-color|surface-base|surface-default|app-bg|base",
    "foreground": r"foreground|fg|fg-default|text|text-default|text-primary|body-color|ink|text-color|body-text|on-background|content|primary-text|fg-primary",
    "card": r"card|surface|surface-1|bg-card|bg-surface|surface-card|panel|elevated|bg-elevated|layer-1|bg-primary|bg-raised",
    "card-foreground": r"card-foreground|on-surface|surface-foreground",
    "popover": r"popover|bg-popover|menu|dropdown",
    "muted": r"muted|bg-muted|bg-subtle|subtle|surface-2|surface-muted|surface-subtle|layer-2|bg-secondary|bg-tertiary|surface-alt|bg-alt",
    "muted-foreground": r"muted-foreground|fg-muted|text-muted|text-secondary|text-subtle|text-tertiary|subtext|secondary-text|text-light|text-soft|fg-subtle|fg-secondary|text-dim|gray-text",
    "border": r"border|border-color|border-default|stroke|divider|line|hairline|outline-variant|separator|border-subtle|border-base",
    "input": r"input|input-border|border-input",
    "ring": r"ring|focus-ring|focus|focus-color|outline",
    "primary": r"primary|primary-color|brand|brand-primary|brand-color|cta|color-primary|accent-primary|primary-500|brand-500|action|interactive|accent-color|link|link-color",
    "primary-foreground": r"primary-foreground|on-primary|primary-fg|text-on-primary|brand-fg|accent-fg|on-brand|on-accent|button-text",
    "secondary": r"secondary|secondary-color|secondary-500",
    "secondary-foreground": r"secondary-foreground|on-secondary",
    "accent": r"accent|highlight",
    "accent-foreground": r"accent-foreground",
    "destructive": r"destructive|danger|error|critical|negative|red|red-500|red-600|color-error|color-danger",
    "success": r"success|positive|green|green-500|ok|valid|color-success",
    "warning": r"warning|caution|attention|color-warning",
    "info": r"info|information|notice|color-info",
}
PREFIX = re.compile(r"^(color|colors|clr|c|theme|tw|ds|semantic|sys|md-sys-color|palette|token)-")


def norm_var(name):
    n = name.lstrip("-").lower()
    for _ in range(2): n = PREFIX.sub("", n)
    return n


def resolve_vars(raw, extra=None):
    """Resolve var(--x) chains using resolved values."""
    vals = dict(raw)
    def res(v, depth=0):
        if depth > 6 or v is None: return v
        m = re.fullmatch(r"var\(\s*(--[\w-]+)\s*(?:,\s*(.+))?\)", v.strip())
        if m:
            ref = vals.get(m.group(1))
            return res(ref, depth + 1) if ref is not None else (res(m.group(2), depth + 1) if m.group(2) else v)
        return v
    return {k: res(v) for k, v in vals.items()}


# ----------------------------------------------------------------------------- palette
def roles_from_vars(varmap):
    roles, ramps, evidence = {}, defaultdict(dict), {}
    for name, value in varmap.items():
        n = norm_var(name)
        c = parse_color(value)
        m = re.fullmatch(r"([a-z][a-z-]*?)-(\d{2,3})", n)
        if c and m: ramps[m.group(1)][m.group(2)] = to_hex(c)
        if not c: continue
        for role, pat in ROLE_NAMES.items():
            if re.fullmatch(pat, n) and role not in roles:
                roles[role] = to_hex(c); evidence[role] = f"CSS variable {name}"
    return roles, {k: dict(sorted(v.items(), key=lambda kv: int(kv[0]))) for k, v in ramps.items() if len(v) >= 3}, evidence


def infer_palette(d, varmap=None, base_bg=None, base_fg=None, label="light"):
    """Return {role: {value, evidence, confidence}}, extras. d is a light/dark capture dict."""
    out, extras = {}, {}
    vroles, ramps, vevid = roles_from_vars(varmap or {})
    for r, v in vroles.items(): out[r] = dict(value=v, evidence=vevid[r], confidence="high")
    if ramps: extras["ramps"] = ramps
    colors = d.get("colors", {}) if d else {}
    layout = d.get("layout", {}) if d else {}
    bgs = [(parse_color(c["value"]), c.get("weight", 0)) for c in colors.get("background", [])]
    bgs = [(c, w) for c, w in bgs if c]
    page = parse_color(base_bg) or parse_color(layout.get("bodyBackground"))
    if "background" not in out:
        if page and opaque(page): out["background"] = dict(value=to_hex(page), evidence="body background", confidence="high")
        else:
            cand = [x for x in bgs if opaque(x[0])]
            out["background"] = dict(value=to_hex(cand[0][0]) if cand else "#ffffff", evidence="largest opaque surface" if cand else "assumed white", confidence="medium" if cand else "low")
    page = parse_color(out["background"]["value"]) or (255, 255, 255, 1)
    texts = [(parse_color(c["value"]), c.get("chars", 0)) for c in colors.get("text", [])]; texts = [(c, w) for c, w in texts if c]
    if "foreground" not in out:
        fg = parse_color(base_fg) or parse_color(layout.get("bodyColor")) or (texts[0][0] if texts else None)
        if texts: fg = texts[0][0]
        if fg: out["foreground"] = dict(value=to_hex(fg), evidence="most-used text color", confidence="high" if texts else "medium")
    if "muted-foreground" not in out and texts:
        fgc = parse_color(out["foreground"]["value"]) if "foreground" in out else None
        pool = [(c, w) for c, w in texts if fgc and to_hex(c) != to_hex(fgc) and hsl(c)[1] < 0.25 and 1.8 < contrast(c, page) < (contrast(fgc, page) - 0.5)]
        if pool: out["muted-foreground"] = dict(value=to_hex(pool[0][0]), evidence="secondary text color", confidence="medium")
    # surfaces (opaque bg different from page)
    surfaces = []
    for c, w in bgs:
        if opaque(c) and to_hex(c) != to_hex(page) and hsl(c)[1] < 0.2 and w > 0.003: surfaces.append((to_hex(c), w))
    if "card" not in out and surfaces:
        out["card"] = dict(value=surfaces[0][0], evidence="2nd largest neutral surface", confidence="medium")
    if "muted" not in out and len(surfaces) > 1:
        out["muted"] = dict(value=surfaces[1][0], evidence="3rd neutral surface", confidence="low")
    if "card" not in out: out["card"] = dict(value=out["background"]["value"], evidence="same as background", confidence="low")
    if "card-foreground" not in out and "foreground" in out: out["card-foreground"] = dict(value=out["foreground"]["value"], evidence="same as foreground", confidence="low")
    if "popover" not in out: out["popover"] = dict(value=out["card"]["value"], evidence="same as card", confidence="low")
    # border
    if "border" not in out:
        bc = [(parse_color(c["value"]), c.get("count", 0)) for c in colors.get("border", [])]; bc = [(c, w) for c, w in bc if c]
        if bc: out["border"] = dict(value=to_hex(bc[0][0]), evidence="most common border color", confidence="high")
    # primary: pick from button variants, then saturated candidates
    btns = (d.get("components", {}).get("buttons", []) if d else []) or (d.get("buttons", []) if d else [])
    def sat_score(c): h_, s_, l_ = hsl(c); return s_ * (1 - abs(l_ - 0.5))
    if "primary" not in out or vroles.get("primary") is None:
        cand = []
        for b in btns:
            st = b.get("style", {}); bg = parse_color(st.get("background")); fg = parse_color(st.get("color"))
            if bg and opaque(bg) and to_hex(bg) not in (to_hex(page), out.get("card", {}).get("value")):
                cand.append((bg, fg, b.get("count", 1), b))
        cand.sort(key=lambda t: (-(sat_score(t[0]) > 0.15), -t[2]))
        if cand and "primary" not in out:
            bg, fg, cnt, b = cand[0]
            out["primary"] = dict(value=to_hex(bg), evidence=f"button background ({cnt} uses)", confidence="high")
            if fg and "primary-foreground" not in out: out["primary-foreground"] = dict(value=to_hex(fg), evidence="text on primary button", confidence="high")
    if "primary" not in out:
        pool = []
        for lst, key in ((colors.get("text", []), "chars"), (colors.get("background", []), "weight"), (colors.get("svgFill", []), "count")):
            for c in lst:
                cc = parse_color(c["value"])
                if cc and opaque(cc) and hsl(cc)[1] > 0.3 and 0.12 < hsl(cc)[2] < 0.9: pool.append((cc, c.get(key, 0)))
        if pool: pool.sort(key=lambda t: -t[1]); out["primary"] = dict(value=to_hex(pool[0][0]), evidence="most-used saturated color", confidence="low")
    if "primary" in out and "primary-foreground" not in out:
        pc = parse_color(out["primary"]["value"]); w, k = (255, 255, 255, 1), (0, 0, 0, 1)
        out["primary-foreground"] = dict(value="#ffffff" if contrast(pc, w) >= contrast(pc, k) else "#000000", evidence="best contrast on primary", confidence="medium")
    # secondary button style
    for b in btns:
        st = b.get("style", {}); bg = parse_color(st.get("background"))
        if bg and "secondary" not in out and opaque(bg) and hsl(bg)[1] < 0.2 and to_hex(bg) != out.get("primary", {}).get("value"):
            out["secondary"] = dict(value=to_hex(bg), evidence="secondary button background", confidence="medium")
            fg = parse_color(st.get("color"))
            if fg: out["secondary-foreground"] = dict(value=to_hex(fg), evidence="secondary button text", confidence="medium")
    # accent candidates, semantic by hue
    pool = Counter()
    for lst, key in ((colors.get("text", []), "chars"), (colors.get("background", []), "weight"), (colors.get("svgFill", []), "count")):
        for c in lst:
            cc = parse_color(c["value"])
            if cc and opaque(cc) and hsl(cc)[1] > 0.35 and 0.15 < hsl(cc)[2] < 0.9: pool[to_hex(cc)] += max(c.get(key, 0), 0.0001) if key != "weight" else c.get(key, 0) * 1000
    extras["accents"] = [{"value": k, "hue": hue_name(hsl(parse_color(k))[0], hsl(parse_color(k))[1]), "weight": round(v, 3)} for k, v in pool.most_common(8)]
    for sem, names in (("destructive", ("red",)), ("success", ("green", "teal")), ("warning", ("amber", "orange", "yellow")), ("info", ("blue", "cyan"))):
        if sem in out: continue
        for a in extras["accents"]:
            if a["hue"] in names: out[sem] = dict(value=a["value"], evidence=f"{a['hue']} accent seen on page", confidence="low"); break
    if "ring" not in out and "primary" in out: out["ring"] = dict(value=out["primary"]["value"], evidence="assumed = primary", confidence="low")
    if "input" not in out and "border" in out: out["input"] = dict(value=out["border"]["value"], evidence="assumed = border", confidence="low")
    if "accent" not in out and "muted" in out: out["accent"] = dict(value=out["muted"]["value"], evidence="assumed = muted (subtle hover surface)", confidence="low")
    if "accent-foreground" not in out and "foreground" in out: out["accent-foreground"] = dict(value=out["foreground"]["value"], evidence="assumed = foreground", confidence="low")
    if "secondary" not in out and "muted" in out: out["secondary"] = dict(value=out["muted"]["value"], evidence="assumed = muted", confidence="low")
    if "secondary-foreground" not in out and "foreground" in out: out["secondary-foreground"] = dict(value=out["foreground"]["value"], evidence="assumed = foreground", confidence="low")
    # neutrals ramp
    neut = {}
    for lst in (colors.get("background", []), colors.get("text", []), colors.get("border", [])):
        for c in lst:
            cc = parse_color(c["value"])
            if cc and opaque(cc) and hsl(cc)[1] < 0.15: neut[to_hex(cc)] = hsl(cc)[2]
    extras["neutrals"] = [k for k, _ in sorted(neut.items(), key=lambda kv: -kv[1])]
    extras["gradients"] = [g["value"] for g in colors.get("gradients", [])][:6]
    return out, extras


# ----------------------------------------------------------------------------- typography
def build_typography(d, resp):
    ty = d.get("typography", [])
    if not ty: return {}
    fam_chars = Counter(); fam_stack = {}
    for t in ty:
        fam_chars[t["family"]] += t["chars"]; fam_stack.setdefault(t["family"], t.get("stack"))
    lay_ = d.get("layout", {})
    base_px = px_of(lay_.get("bodyFontSize")) or px_of(lay_.get("rootFontSize")) or 16
    plain = [t for t in sorted(ty, key=lambda t: -t["chars"]) if not any(h in t["tags"] for h in ("h1", "h2", "h3", "h4", "h5", "h6", "code", "pre", "button")) and t["chars"] >= 12]
    body = next((t for t in plain if t["size"] == base_px and str(t["weight"]) == str(lay_.get("bodyFontWeight") or 400)), None) or next((t for t in plain if t["size"] == base_px), None)
    paragraph = next(iter(plain), None)
    if body is None:  # body text itself carries little copy: synthesize it from the <body> computed style
        lhp = px_of(lay_.get("bodyLineHeight")); bw = lay_.get("bodyFontWeight") or 400
        body = {"family": lay_.get("bodyFont") or (paragraph or ty[0])["family"], "stack": (paragraph or ty[0]).get("stack"), "size": base_px, "weight": int(bw) if str(bw).isdigit() else bw,
                "lineHeightRatio": round(lhp / base_px, 3) if lhp and base_px else None, "letterSpacingEm": 0, "transform": "none", "tags": {"body": 1}, "chars": 0, "sample": "(page body default)"}
    fam_chars[body["family"]] += 1
    heads = [t for t in ty if any(h in t["tags"] for h in ("h1", "h2", "h3"))]
    head_fam = Counter()
    for t in heads: head_fam[t["family"]] += t["chars"]
    mono_fam = next((f for f in fam_chars if re.search(r"mono|code|courier|consolas|menlo", (fam_stack.get(f) or f), re.I)), None)
    fams = {"sans": body["family"], "heading": head_fam.most_common(1)[0][0] if head_fam else body["family"], "mono": mono_fam}
    stacks = {k: fam_stack.get(v) for k, v in fams.items() if v}

    def best(tag):
        c = [t for t in ty if tag in t["tags"]]
        return max(c, key=lambda t: t["chars"]) if c else None
    def style(t, role):
        if not t: return None
        return {"role": role, "family": t["family"], "size": t["size"], "weight": t["weight"], "lineHeight": t.get("lineHeightRatio"), "letterSpacingEm": t.get("letterSpacingEm", 0), "transform": t.get("transform") if t.get("transform") not in (None, "none") else None, "sample": t.get("sample")}
    roles = []
    for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        s = style(best(tag), tag); 
        if s: roles.append(s)
    big = [t for t in ty if t["size"] and t["size"] > (best("h1") or {"size": 0})["size"]] if best("h1") else []
    if big: roles.insert(0, style(max(big, key=lambda t: t["size"]), "display"))
    roles.append(style(body, "body"))
    if paragraph and paragraph is not body and paragraph.get("size") != body.get("size"): roles.append(style(paragraph, "paragraph"))
    lead = [t for t in ty if t["size"] and body["size"] and t["size"] > body["size"] and t["size"] <= body["size"] * 1.5 and not any(h in t["tags"] for h in ("h1", "h2", "h3", "h4", "h5", "h6", "button", "a"))]
    if lead: roles.append(style(max(lead, key=lambda t: t["chars"]), "lead"))
    small = [t for t in ty if t["size"] and body["size"] and t["size"] < body["size"] and not any(h in t["tags"] for h in ("code", "pre"))]
    if small: roles.append(style(max(small, key=lambda t: t["chars"]), "small"))
    btn = best("button") or best("a")
    if btn: roles.append(style(btn, "button/label"))
    over = [t for t in ty if t.get("transform") == "uppercase" and (t.get("letterSpacingEm") or 0) > 0.02]
    if over: roles.append(style(max(over, key=lambda t: t["chars"]), "overline"))
    cd = best("code") or best("pre")
    if cd: roles.append(style(cd, "code"))
    roles = [r for r in roles if r]
    sizes = sorted({t["size"] for t in ty if t["size"] and t["chars"] >= 3})
    ratios = [sizes[i + 1] / sizes[i] for i in range(len(sizes) - 1) if sizes[i] >= (body["size"] or 16) - 0.1]
    mod = None
    if len(ratios) >= 2:
        med = statistics.median(ratios); near = min(RATIOS, key=lambda r: abs(r[0] - med)); mod = {"median": round(med, 3), "nearest": near[1], "ratio": near[0]}
    wts = Counter()
    for t in ty: wts[str(t["weight"])] += t["chars"]
    tracking = [t["letterSpacingEm"] for t in heads if t.get("letterSpacingEm") is not None]
    return {
        "families": fams, "stacks": stacks, "baseSize": body["size"], "baseLineHeight": body.get("lineHeightRatio"), "styles": roles, "sizes": sizes, "modularScale": mod,
        "weights": [{"weight": k, "share": round(v / sum(wts.values()), 3)} for k, v in wts.most_common()],
        "headingTrackingEm": round(statistics.median(tracking), 4) if tracking else 0,
        "fluid": ({"h1": {k: resp[k].get("h1Size") for k in resp}} if resp else None),
    }


def font_sources(d, tech):
    f = d.get("fonts", {}); fams = {t["family"] for t in d.get("typography", [])}
    face = {x["family"].lower() for x in f.get("fontFaces", [])}
    links = f.get("links", []); net = (tech or {}).get("fonts", [])
    out = []
    for fam in sorted(fams, key=lambda x: x.lower()):
        low = fam.lower()
        if low in ("inherit", "initial", "unset", ""): continue
        if low in SYSTEM_FONTS: src = "system"
        elif any(low.replace(" ", "+") in l.lower() or low.replace(" ", "") in l.lower() for l in links): src = "web font link (Google/Bunny/Adobe)"
        elif low in face: src = "@font-face (self-hosted or CDN)"
        else: src = "installed locally or unresolved"
        alt = OPEN_ALTS.get(low)
        out.append({"family": fam, "source": src, "openAlternative": alt if (alt and alt.lower() != low) else None, "note": "Likely proprietary or licensed; verify license before shipping the font files." if src.startswith("@font-face") else None})
    return out


# ----------------------------------------------------------------------------- spacing/radius/shadow/motion
def build_spacing(d):
    sp = d.get("spacing", [])
    vals = [(float(s["px"]), s["count"]) for s in sp if s.get("px")]
    if not vals: return {}
    total = sum(c for _, c in vals)
    fits = {b: sum(c for v, c in vals if abs(v / b - round(v / b)) < 0.01) / total for b in (4, 8, 6, 5, 10)}
    base = 8 if fits[8] >= 0.72 else (4 if fits[4] >= 0.7 else max(fits, key=fits.get))
    scale = sorted({round(v, 1) for v, c in vals if c >= 2 and v >= 2})
    secs = d.get("sections", [])
    pads = [px_of(p) for s in secs for p in (s.get("paddingY") or "").split() if px_of(p)]
    pads = [p for p in pads if p >= 24]
    grids = d.get("layout", {}).get("grids", [])
    gaps = Counter()
    for g in grids:
        m = re.search(r"gap:(\d+(?:\.\d+)?)px", g["value"])
        if m: gaps[float(m.group(1))] += g["count"]
    return {"baseUnit": base, "baseFit": round(fits[base], 2), "scale": scale[:20], "usage": [{"px": v, "count": c, "x": round(v / base, 2)} for v, c in sorted(vals, key=lambda t: -t[1])[:14]],
            "sectionPaddingY": sorted(set(pads)), "commonGaps": [g for g, _ in gaps.most_common(4)]}


def build_radius(d):
    rs = d.get("radii", []); vals = []
    full = any(r["value"] == "full" for r in rs)
    for r in rs:
        if r["value"] == "full": continue
        v = float(r["value"]); vals.append((v, r["count"]))
    merged = []
    for v, c in sorted(vals):
        if merged and abs(merged[-1][0] - v) <= 1.5: merged[-1] = (merged[-1][0], merged[-1][1] + c)
        else: merged.append((v, c))
    top = sorted(merged, key=lambda t: -t[1])[:5]; top = sorted(top)
    names = ["sm", "md", "lg", "xl", "2xl"]
    scale = {names[i]: f"{int(v) if v == int(v) else v}px" for i, (v, _) in enumerate(top)}
    if full: scale["full"] = "9999px"
    base = max(merged, key=lambda t: t[1])[0] if merged else None
    desc = "pill-heavy" if full and (not merged or sum(c for _, c in merged) < 2 * next((r["count"] for r in rs if r["value"] == "full"), 0)) else None
    med = statistics.median([v for v, c in merged for _ in range(c)]) if merged else 0
    char = desc or ("sharp (square corners)" if med <= 3 else "slightly rounded" if med <= 8 else "rounded" if med <= 16 else "very rounded")
    return {"scale": scale, "dominant": base, "character": char, "usage": rs[:8]}


def shadow_size(s):
    m = re.search(r"(-?[\d.]+)px\s+(-?[\d.]+)px\s+(-?[\d.]+)px", s)
    if not m: return 0
    return abs(float(m.group(2))) + float(m.group(3))


def split_top(v, sep=","):
    out, depth, cur = [], 0, ""
    for ch in v:
        depth += (ch == "(") - (ch == ")")
        if ch == sep and depth == 0: out.append(cur.strip()); cur = ""
        else: cur += ch
    if cur.strip(): out.append(cur.strip())
    return out


def canon_shadow(v, varmap=None):
    """Canonicalize a box-shadow value. Returns (css, meta) or None. Resolves var() colors."""
    layers = []
    for layer in split_top(re.sub(r"\s+", " ", v.strip().rstrip(";"))):
        inset = bool(re.search(r"\binset\b", layer)); l2 = re.sub(r"\binset\b", "", layer).strip()
        cm = re.search(r"rgba?\([^)]*\)|hsla?\([^)]*\)|oklch\([^)]*\)|#[0-9a-fA-F]{3,8}\b|var\([^)]*\)|\b[a-z]+\b(?=\s*$)", l2)
        col = None
        if cm:
            ctext = cm.group(0)
            if ctext.startswith("var(") and varmap:
                ref = re.match(r"var\(\s*(--[\w-]+)", ctext)
                ctext = (resolve_vars(varmap).get(ref.group(1)) if ref else None) or ctext
            col = parse_color(ctext)
            l2 = (l2[:cm.start()] + " " + l2[cm.end():]).strip()
        nums = [float(x) for x in re.findall(r"-?\d*\.?\d+(?=px|\s|$)", l2)]
        if len(nums) < 2: return None
        nums += [0.0] * (4 - len(nums)); x, y, b, sp = nums[:4]
        layers.append({"x": x, "y": y, "b": b, "s": sp, "c": col, "inset": inset})
    if not layers: return None
    css = ", ".join(("inset " if L["inset"] else "") + f"{L['x']:g}px {L['y']:g}px {L['b']:g}px " + (f"{L['s']:g}px " if L["s"] else "") + (f"rgba({L['c'][0]}, {L['c'][1]}, {L['c'][2]}, {L['c'][3]:g})" if L["c"] else "currentColor") for L in layers)
    ring = len(layers) == 1 and layers[0]["x"] == 0 and layers[0]["y"] == 0 and layers[0]["b"] == 0 and layers[0]["s"] > 0
    glow = any(L["c"] and hsl(L["c"])[1] > 0.3 and L["c"][3] > 0.12 for L in layers if not L["inset"])
    size = max((abs(L["y"]) + L["b"] for L in layers if not L["inset"]), default=0)
    inset_only = all(L["inset"] for L in layers)
    return css, {"kind": "ring" if ring else ("inset" if inset_only else ("glow" if glow else "drop")), "size": size}


def build_shadows(d, raw=None, varmap=None):
    resolved = resolve_vars(varmap or {})
    cand = [(s_["value"], s_["count"]) for s_ in d.get("shadows", {}).get("box", [])]
    for name, v in (varmap or {}).items():
        if "shadow" in name and v and "var(" not in v[:4]: cand.append((v, 1))
    for r in (d.get("stateRules", {}) or {}).get("sample", []):
        m = re.search(r"box-shadow:\s*([^;]+)", r.get("css", ""))
        if m: cand.append((m.group(1), 1))
    for st in (raw or {}).get("states", []) or []:
        b = (st.get("hover") or {}).get("boxShadow")
        if b and b.get("to"): cand.append((b["to"], 1))
    merged = {}
    for v, n in cand:
        if not v or v.strip() == "none": continue
        c = canon_shadow(v, resolved)
        if not c: continue
        css, meta = c
        e = merged.setdefault(css, {"value": css, "count": 0, **meta}); e["count"] += n
    items = sorted(merged.values(), key=lambda i: -i["count"])
    drops = sorted([i for i in items if i["kind"] == "drop"], key=lambda i: i["size"])[:6]
    names = {1: ["sm"], 2: ["sm", "md"], 3: ["sm", "md", "lg"], 4: ["xs", "sm", "md", "lg"], 5: ["xs", "sm", "md", "lg", "xl"], 6: ["xs", "sm", "md", "lg", "xl", "2xl"]}.get(len(drops), [])
    levels = {n: it["value"] for n, it in zip(names, drops)}
    mx = max([i["size"] for i in drops], default=0)
    weight = "none (flat)" if not drops else "subtle" if mx <= 12 else "soft" if mx <= 40 else "dramatic"
    if any(i["kind"] == "glow" for i in items): weight += " + colored glow on featured elements"
    return {"levels": levels, "rings": [i["value"] for i in items if i["kind"] == "ring"][:2], "glows": [i["value"] for i in items if i["kind"] == "glow"][:2], "all": items[:10], "character": weight,
            "backdrop": [b["value"] for b in d.get("shadows", {}).get("backdrop", [])][:2], "filter": [b["value"] for b in d.get("shadows", {}).get("filter", [])][:2]}


def build_motion(d, states):
    tr = d.get("motion", {}).get("transitions", [])
    durs = Counter(); ease = Counter(); props = Counter()
    for t in tr:
        ms = int(re.sub(r"\D", "", t["duration"]) or 0); durs[ms] += t["count"]; ease[t["easing"]] += t["count"]; props[t["property"]] += t["count"]
    scale = {}
    for ms in sorted(durs):
        k = "fast" if ms <= 120 else "base" if ms <= 250 else "slow" if ms <= 500 else "slower"
        scale.setdefault(k, ms)
    hover = []
    for s in states or []:
        if s.get("hover"): hover.append({"kind": s["kind"], "text": s.get("text"), "changes": {k: v for k, v in s["hover"].items() if k not in ("outline", "outlineOffset")}})
    return {"durations": scale, "durationUsage": [{"ms": k, "count": v} for k, v in durs.most_common(6)], "easings": [{"value": k, "count": v} for k, v in ease.most_common(4)], "properties": [{"property": k, "count": v} for k, v in props.most_common(8)],
            "keyframes": d.get("motion", {}).get("keyframes", [])[:12], "animations": d.get("motion", {}).get("animations", [])[:8], "scrollBehavior": d.get("motion", {}).get("scrollBehavior"), "hoverPatterns": hover[:10]}


def describe_change(k, v):
    a, b = v.get("from"), v.get("to")
    if k in ("backgroundColor", "color", "borderTopColor"):
        ca, cb = parse_color(a), parse_color(b)
        if ca and cb:
            la, lb = hsl(ca)[2], hsl(cb)[2]
            return f"{k}: {to_hex(ca)} -> {to_hex(cb)} ({'darker' if lb < la else 'lighter'})"
    if k == "transform" and b and b != "none":
        m = re.search(r"matrix\(([^)]+)\)", b)
        if m:
            p = [float(x) for x in m.group(1).split(",")]
            return f"transform: translateY({p[5]:g}px)" + (f" scale({p[0]:g})" if abs(p[0] - 1) > 0.001 else "")
    return f"{k}: {str(a)[:50]} -> {str(b)[:60]}"


# ----------------------------------------------------------------------------- orchestration
def build(raw, name=None):
    d = raw.get("light") or raw.get("static") or {}
    if not d: sys.exit("raw.json has no 'light' or 'static' capture")
    resolved = d.get("rootResolved", {})
    varmap = resolve_vars(resolved) if resolved else {}
    light_vars = {k: v for k, v in varmap.items()}
    pal, extras = infer_palette(d, light_vars, label="light")
    dark_pal = None
    dk = raw.get("dark")
    dark_strategy = None
    if dk and dk.get("differs"):
        dvars = resolve_vars(dk.get("rootResolved", {}))
        dd = {"colors": dk.get("colors", {}), "layout": {"bodyBackground": dk.get("bodyBackground"), "bodyColor": dk.get("bodyColor")}, "components": {"buttons": dk.get("buttons", [])}}
        dark_pal, _ = infer_palette(dd, dvars, base_bg=dk.get("bodyBackground"), base_fg=dk.get("bodyColor"), label="dark")
        dark_strategy = "prefers-color-scheme media query"
    elif raw.get("darkMode", {}).get("forced"):
        f = raw["darkMode"]["forced"]; dark_strategy = f["strategy"]
        dark_pal = {"background": {"value": hx(f["bodyBackground"]), "evidence": "forced dark probe", "confidence": "medium"}, "foreground": {"value": hx(f["bodyColor"]), "evidence": "forced dark probe", "confidence": "medium"}}
    dvars_static = {}
    for sel, vs in d.get("cssVariables", {}).items():
        if sel.startswith("@dark ") or re.search(r"\.dark|data-theme=.?dark|theme-dark", sel):
            dvars_static.update(vs)
    if dvars_static and not (dark_pal and len(dark_pal) > 4):
        r_, _, ev = roles_from_vars(resolve_vars({**light_vars, **dvars_static}))
        dark_pal = dark_pal or {}
        for k, v in r_.items(): dark_pal[k] = {"value": v, "evidence": ev[k] + " (dark)", "confidence": "high"}
        dark_strategy = dark_strategy or "dark selector in stylesheet"

    resp = raw.get("responsive", {})
    typo = build_typography(d, resp)
    spacing = build_spacing(d); radius = build_radius(d); shadows = build_shadows(d, raw, light_vars); motion = build_motion(d, raw.get("states"))
    lay = d.get("layout", {}); cont = None
    for c in lay.get("containerMaxWidths", []):
        v = px_of(c["value"])
        if v and v >= 700 and (cont is None or c["count"] > cont[1]): cont = (v, c["count"])
    bps = sorted({int(k.split(":")[1]) for k, _ in d.get("breakpoints", []) if k.startswith("min:")})
    tw_default = {640, 768, 1024, 1280, 1536}.issubset(set(bps)) if bps else False
    layout = {"containerMax": f"{int(cont[0])}px" if cont else None, "header": lay.get("header"), "stickyOrFixed": lay.get("stickyOrFixed", [])[:4], "grids": lay.get("grids", [])[:5], "flexShare": lay.get("flexShare"), "gridShare": lay.get("gridShare"),
              "zIndex": [z["value"] for z in lay.get("zIndexes", [])], "breakpoints": {"min": bps, "max": sorted({int(k.split(":")[1]) for k, _ in d.get("breakpoints", []) if k.startswith("max:")}), "tailwindDefaults": tw_default}}

    # contrast checks on palette
    checks = []
    def chk(a, b, label):
        ca, cb = parse_color((pal.get(a) or {}).get("value")), parse_color((pal.get(b) or {}).get("value"))
        if ca and cb:
            r = contrast(ca, cb); checks.append({"pair": label, "ratio": r, "AA": r >= 4.5, "AAlarge": r >= 3})
    chk("foreground", "background", "foreground on background"); chk("muted-foreground", "background", "muted text on background"); chk("primary-foreground", "primary", "text on primary"); chk("primary", "background", "primary on background (links/icons)")

    # buttons labelled
    labelled = []
    prim = (pal.get("primary") or {}).get("value")
    for b in d.get("components", {}).get("buttons", []):
        st = b.get("style", {}); bg = parse_color(st.get("background")); border = st.get("border", "none"); role = "other"
        if bg and opaque(bg) and to_hex(bg) == prim: role = "primary"
        elif bg and bg[3] < 0.05 and border != "none": role = "outline"
        elif bg and bg[3] < 0.05: role = "ghost"
        elif bg and opaque(bg) and hsl(bg)[1] > 0.5 and hue_name(hsl(bg)[0]) == "red": role = "destructive"
        elif bg and opaque(bg): role = "secondary"
        labelled.append({"variant": role, **b})

    # state summary
    states = []
    for s in raw.get("states", []) or []:
        if s.get("error"): continue
        states.append({"kind": s["kind"], "text": s.get("text"), "hover": [describe_change(k, v) for k, v in (s.get("hover") or {}).items() if k not in ("outline", "outlineOffset")], "focus": [describe_change(k, v) for k, v in (s.get("focus") or {}).items()], "transition": s.get("transition")})

    # character summary
    bg_c = parse_color(pal["background"]["value"]); mode = "dark" if bg_c and lum(bg_c) < 0.2 else "light"
    prim_c = parse_color(prim) if prim else None
    neut = [parse_color(x) for x in extras.get("neutrals", [])]; warm = [hsl(c) for c in neut if c and 0.03 < hsl(c)[1] < 0.3]
    tint = "neutral gray"
    if warm:
        mh = statistics.median([w[0] for w in warm])
        tint = "warm-tinted neutrals" if (15 <= mh <= 70) else "cool-tinted neutrals" if (180 <= mh <= 270) else "neutral gray"
    sec_pad = max(spacing.get("sectionPaddingY", [0]) or [0])
    density = "unknown (no section data)" if not sec_pad else "airy" if sec_pad >= 112 else "comfortable" if sec_pad >= 64 else "compact"
    h1 = next((s for s in typo.get("styles", []) if s["role"] in ("display", "h1")), None)
    summary = {"mode": mode, "darkSupport": bool(dark_pal), "accent": (hue_name(hsl(prim_c)[0], hsl(prim_c)[1]) if prim_c else None), "neutralTint": tint, "corners": radius["character"], "elevation": shadows["character"], "density": density,
               "headline": f"{h1['size']:g}px / {h1['weight']} / tracking {h1['letterSpacingEm']:g}em" if h1 else None, "motion": ("snappy (<=150ms)" if motion["durations"].get("base", 200) <= 160 else "smooth (150-300ms)" if motion["durations"].get("base", 200) <= 320 else "slow/dramatic") if motion["durations"] else "minimal/none detected"}

    unknowns = []
    st = d.get("stylesheets", {})
    if st.get("crossOriginBlocked"): unknowns.append(f"{st['crossOriginBlocked']} cross-origin stylesheet(s) were unreadable; values come from computed styles instead (CSS variable names/media rules may be incomplete).")
    if not raw.get("states"): unknowns.append("Hover/focus states were not captured.")
    if not dark_pal: unknowns.append("No dark mode detected (none, or toggled by JS the probe could not trigger).")
    if d.get("truncated"): unknowns.append("Page had more than 6000 elements; extraction sampled the first 6000.")
    if raw.get("http", {}).get("blocked"): unknowns.append("Page may have been served a bot-check or error page. Verify with screenshots.")
    low = [k for k, v in pal.items() if v["confidence"] == "low"]
    if low: unknowns.append("Low-confidence palette roles (inferred, verify against screenshots): " + ", ".join(low))
    fonts = font_sources(d, raw.get("network"))
    for f in fonts:
        if f["source"] == "installed locally or unresolved" and f["family"].lower() not in SYSTEM_FONTS: unknowns.append(f"Font '{f['family']}' was not found as a web font; it may be installed on the capture machine or blocked.")

    anatomy = [{"index": s["index"], "kind": s["kind"], "height": s["h"], "heading": s.get("heading"), "background": s.get("background"), "columns": s.get("gridColumns"), "buttons": s.get("buttons"), "media": s.get("media"), "align": s.get("align")} for s in d.get("sections", [])]
    meta = d.get("meta", {})
    tokens = {
        "meta": {"name": name or meta.get("title"), "url": meta.get("url") or raw.get("url"), "capturedAt": raw.get("capturedAt"), "tech": d.get("techHints", []), "generatedBy": "dea/synthesize.py", "themeColor": meta.get("themeColor"), "source": "browser" if raw.get("light") else "static-css"},
        "summary": summary,
        "color": {"light": pal, "dark": dark_pal, "darkStrategy": dark_strategy, "neutrals": extras.get("neutrals", []), "accents": extras.get("accents", []), "gradients": extras.get("gradients", []), "ramps": extras.get("ramps", {})},
        "typography": typo, "fonts": fonts, "spacing": spacing, "radius": radius, "shadow": shadows, "border": {"patterns": d.get("borders", [])[:8]}, "motion": motion, "layout": layout,
        "components": {**{k: v for k, v in d.get("components", {}).items() if k != "buttons"}, "buttons": labelled}, "states": states, "anatomy": anatomy, "responsive": resp,
        "contrast": {"palette": checks, "observed": d.get("contrast", [])[:10]}, "siteVariables": {"light": light_vars, "dark": dvars_static}, "assets": d.get("assets", {}), "network": raw.get("network", {}), "screenshots": raw.get("screenshots", {}), "unknowns": unknowns,
    }
    return tokens


# ----------------------------------------------------------------------------- writers
SEMANTIC_ORDER = ["background", "foreground", "card", "card-foreground", "popover", "primary", "primary-foreground", "secondary", "secondary-foreground", "muted", "muted-foreground", "accent", "accent-foreground", "destructive", "success", "warning", "info", "border", "input", "ring"]


def css_block(pal, indent="  "):
    return "\n".join(f"{indent}--{k}: {pal[k]['value']};" for k in SEMANTIC_ORDER if k in pal and pal[k].get("value"))


def write_css(t, out):
    tp, sp, rd, sh, mo = t["typography"], t["spacing"], t["radius"], t["shadow"], t["motion"]
    L = ["/* Generated by DEA (dea/synthesize.py). Source: " + str(t["meta"].get("url")) + " */", ":root {", "  /* color (shadcn/Tailwind-compatible semantic names) */", css_block(t["color"]["light"])]
    L.append("\n  /* typography */")
    fam = tp.get("families", {}); st = tp.get("stacks", {})
    if fam.get("sans"): L.append(f"  --font-sans: {st.get('sans') or fam['sans']};")
    if fam.get("heading") and fam["heading"] != fam.get("sans"): L.append(f"  --font-heading: {st.get('heading') or fam['heading']};")
    if fam.get("mono"): L.append(f"  --font-mono: {st.get('mono') or fam['mono']};")
    names = {"display": "display", "h1": "h1", "h2": "h2", "h3": "h3", "h4": "h4", "body": "body", "paragraph": "paragraph", "lead": "lead", "small": "small", "overline": "overline", "code": "code", "button/label": "label"}
    for s in tp.get("styles", []):
        n = names.get(s["role"])
        if n and s.get("size"):
            L.append(f"  --text-{n}: {s['size']:g}px;"); 
            if s.get("lineHeight"): L.append(f"  --leading-{n}: {s['lineHeight']:g};")
            L.append(f"  --weight-{n}: {s['weight']};")
            if s.get("letterSpacingEm"): L.append(f"  --tracking-{n}: {s['letterSpacingEm']:g}em;")
    L.append("\n  /* spacing */")
    base = sp.get("baseUnit", 8); L.append(f"  --space-unit: {base}px;")
    for m in (0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24):
        L.append(f"  --space-{str(m).replace('.', '_')}: {base * m:g}px;")
    if sp.get("sectionPaddingY"): L.append(f"  --section-padding-y: {max(sp['sectionPaddingY']):g}px;")
    if t["layout"].get("containerMax"): L.append(f"  --container-max: {t['layout']['containerMax']};")
    L.append("\n  /* radius */")
    for k, v in rd.get("scale", {}).items(): L.append(f"  --radius-{k}: {v};")
    if rd.get("dominant") is not None: L.append(f"  --radius: {rd['dominant']:g}px;")
    L.append("\n  /* elevation */")
    for k, v in sh.get("levels", {}).items(): L.append(f"  --shadow-{k}: {v};")
    for i, g in enumerate(sh.get("glows", [])): L.append(f"  --shadow-glow{'' if i == 0 else i + 1}: {g};")
    if sh.get("rings"): L.append(f"  --ring-shadow: {sh['rings'][0]};")
    L.append("\n  /* motion */")
    for k, v in mo.get("durations", {}).items(): L.append(f"  --duration-{k}: {v}ms;")
    if mo.get("easings"): L.append(f"  --ease: {mo['easings'][0]['value']};")
    L.append("}")
    dk = t["color"].get("dark")
    if dk:
        L.append("\n/* dark mode */")
        strat = t["color"].get("darkStrategy") or ""
        L.append("@media (prefers-color-scheme: dark) {\n  :root:not([data-theme=\"light\"]):not(.light) {\n" + css_block(dk, "    ") + "\n  }\n}")
        L.append(".dark, [data-theme=\"dark\"] {\n" + css_block(dk) + "\n}")
        L.append(f"/* detected strategy: {strat} */")
    (out / "tokens.css").write_text("\n".join(L) + "\n")


def write_site_vars(t, out):
    lv, dv = t["siteVariables"].get("light", {}), t["siteVariables"].get("dark", {})
    if not lv and not dv: return
    L = ["/* The site's OWN custom properties, resolved. Use when you want to mirror its naming; otherwise use tokens.css. */", ":root {"]
    L += [f"  {k}: {v};" for k, v in list(lv.items())[:500]]
    L.append("}")
    if dv:
        L += ["\n/* dark overrides (as declared by the site) */", ".dark, [data-theme=\"dark\"] {"] + [f"  {k}: {v};" for k, v in list(dv.items())[:500]] + ["}"]
    (out / "site-variables.css").write_text("\n".join(L) + "\n")


def write_tailwind(t, out):
    tp, sp, rd, sh, mo, lay = t["typography"], t["spacing"], t["radius"], t["shadow"], t["motion"], t["layout"]
    fam = tp.get("families", {}); st = tp.get("stacks", {})
    colors = {k: f"var(--{k})" for k in SEMANTIC_ORDER if k in t["color"]["light"]}
    font = {}
    if fam.get("sans"): font["sans"] = [f"var(--font-sans)"]
    if fam.get("mono"): font["mono"] = ["var(--font-mono)"]
    if fam.get("heading") and fam["heading"] != fam.get("sans"): font["heading"] = ["var(--font-heading)"]
    fs = {}
    for s in tp.get("styles", []):
        key = {"display": "display", "h1": "h1", "h2": "h2", "h3": "h3", "h4": "h4", "lead": "lead", "small": "sm", "body": "base", "overline": "overline"}.get(s["role"])
        if key and s.get("size"):
            o = {"lineHeight": str(s["lineHeight"]) if s.get("lineHeight") else "1.5", "fontWeight": str(s["weight"])}
            if s.get("letterSpacingEm"): o["letterSpacing"] = f"{s['letterSpacingEm']:g}em"
            fs[key] = [f"{s['size']:g}px", o]
    cfg = {"darkMode": "class" if (t["color"].get("darkStrategy") or "").startswith("class") or t["color"].get("dark") else "media",
           "theme": {"extend": {"colors": colors, "fontFamily": font, "fontSize": fs, "borderRadius": {k: f"var(--radius-{k})" for k in rd.get("scale", {})}, "boxShadow": {k: f"var(--shadow-{k})" for k in sh.get("levels", {})}, "transitionDuration": {k: f"var(--duration-{k})" for k in mo.get("durations", {})}, "maxWidth": {"container": lay.get("containerMax") or "1200px"}}}}
    if lay["breakpoints"]["min"] and not lay["breakpoints"]["tailwindDefaults"]:
        cfg["theme"]["extend"]["screens"] = {f"bp{v}": f"{v}px" for v in lay["breakpoints"]["min"][:6]}
    js = "/** Generated by DEA. Requires tokens.css to be imported globally. */\nmodule.exports = " + json.dumps(cfg, indent=2) + ";\n"
    (out / "tailwind.config.js").write_text(js)
    # v4
    L = ["/* Generated by DEA. Tailwind v4: @import \"tailwindcss\"; then paste/import this file. */", "@theme {"]
    for k in SEMANTIC_ORDER:
        if k in t["color"]["light"]: L.append(f"  --color-{k}: var(--{k});")
    for k in font: L.append(f"  --font-{k}: var(--font-{k});")
    for k in rd.get("scale", {}): L.append(f"  --radius-{k}: var(--radius-{k});")
    for k in sh.get("levels", {}): L.append(f"  --shadow-{k}: var(--shadow-{k});")
    for k, v in mo.get("durations", {}).items(): L.append(f"  --duration-{k}: {v}ms;")
    if mo.get("easings"): L.append(f"  --ease-brand: {mo['easings'][0]['value']};")
    for v in lay["breakpoints"]["min"][:6]: L.append(f"  --breakpoint-bp{v}: {v}px;")
    L.append("}")
    if t["color"].get("dark"): L.append("@custom-variant dark (&:where(.dark, .dark *, [data-theme=\"dark\"], [data-theme=\"dark\"] *));")
    (out / "tailwind-v4.css").write_text("\n".join(L) + "\n")


def md_table(headers, rows):
    L = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    for r in rows: L.append("| " + " | ".join(str(x).replace("|", "\\|") for x in r) + " |")
    return "\n".join(L)


def write_md(t, out):
    m, s = t["meta"], t["summary"]; tp = t["typography"]; c = t["color"]
    L = [f"# Design System: {m.get('name') or m.get('url')}", f"_Extracted by DEA on {str(m.get('capturedAt') or date.today())[:10]} from {m.get('url')}. Tokens are measured; role names are inferred (see confidence)._\n"]
    L += ["## 1. Visual summary (auto-draft: AGENT must verify against screenshots and rewrite in your own words)",
          f"- **Mode:** {s['mode']} base" + (" with dark theme support" if s["darkSupport"] else ", no dark theme detected"),
          f"- **Accent:** {s['accent'] or 'n/a'} on {s['neutralTint']}", f"- **Corners:** {s['corners']}  |  **Elevation:** {s['elevation']}  |  **Density:** {s['density']}",
          f"- **Headline style:** {s['headline'] or 'n/a'}  |  **Motion:** {s['motion']}", f"- **Tech/stack hints:** {', '.join(m.get('tech') or []) or 'n/a'}",
          "\n<!-- AGENT: replace with a 3-5 sentence description of the aesthetic, what makes it recognizable (layout, imagery, type voice, signature details) and the 5 rules that keep it consistent. -->\n"]
    L += ["## 2. Color", "### Semantic roles (light)", md_table(["Role", "Value", "Evidence", "Confidence"], [[k, f"`{c['light'][k]['value']}`", c['light'][k]['evidence'], c['light'][k]['confidence']] for k in SEMANTIC_ORDER if k in c["light"]])]
    if c.get("dark"):
        L += [f"\n### Dark theme (strategy: {c.get('darkStrategy')})", md_table(["Role", "Value", "Evidence"], [[k, f"`{c['dark'][k]['value']}`", c['dark'][k]['evidence']] for k in SEMANTIC_ORDER if k in c["dark"] and c["dark"][k].get("value")])]
    if c.get("accents"): L += ["\n### Accent colors seen", ", ".join(f"`{a['value']}` ({a['hue']})" for a in c["accents"])]
    if c.get("neutrals"): L += ["\n### Neutral ramp (light -> dark)", " ".join(f"`{x}`" for x in c["neutrals"][:14])]
    if c.get("gradients"): L += ["\n### Gradients", "\n".join(f"- `{g}`" for g in c["gradients"])]
    if c.get("ramps"): L += ["\n### Named color ramps from CSS variables", "\n".join(f"- **{k}**: " + ", ".join(f"{s_}:`{v}`" for s_, v in list(r.items())[:11]) for k, r in c["ramps"].items())]
    L += ["\n### Contrast (WCAG)", md_table(["Pair", "Ratio", "AA text", "AA large"], [[x["pair"], x["ratio"], "pass" if x["AA"] else "FAIL", "pass" if x["AAlarge"] else "FAIL"] for x in t["contrast"]["palette"]])]
    L += ["\n## 3. Typography", f"- **Families:** " + ", ".join(f"{k}: `{v}`" for k, v in tp.get("families", {}).items() if v), f"- **Base:** {tp.get('baseSize')}px / line-height {tp.get('baseLineHeight')}"]
    if tp.get("modularScale"): L.append(f"- **Scale ratio:** ~{tp['modularScale']['ratio']} ({tp['modularScale']['nearest']}), measured median {tp['modularScale']['median']}")
    L.append(f"- **Heading tracking:** {tp.get('headingTrackingEm')}em  |  **Weights used:** " + ", ".join(f"{w['weight']} ({int(w['share'] * 100)}%)" for w in tp.get("weights", [])[:5]))
    if tp.get("fluid"): L.append("- **Responsive H1 size:** " + ", ".join(f"{k}: {v}" for k, v in tp["fluid"]["h1"].items()))
    L += ["", md_table(["Role", "Size", "Weight", "Line-height", "Tracking", "Family", "Notes"], [[x["role"], f"{x['size']:g}px", x["weight"], x.get("lineHeight") or "-", f"{x.get('letterSpacingEm') or 0:g}em", x["family"], x.get("transform") or ""] for x in tp.get("styles", [])])]
    L += ["\n### Font sourcing", md_table(["Family", "Source", "Open alternative", "Note"], [[f["family"], f["source"], f.get("openAlternative") or "-", f.get("note") or ""] for f in t["fonts"]])]
    sp = t["spacing"]
    if sp:
        L += ["\n## 4. Spacing & layout", f"- **Base unit:** {sp['baseUnit']}px (fits {int(sp['baseFit'] * 100)}% of measured values)", f"- **Scale in use (px):** {', '.join(f'{v:g}' for v in sp.get('scale', []))}", f"- **Section vertical padding:** {', '.join(f'{v:g}px' for v in sp.get('sectionPaddingY', [])) or 'n/a'}", f"- **Common grid gaps:** {', '.join(f'{v:g}px' for v in sp.get('commonGaps', [])) or 'n/a'}",
              f"- **Container max-width:** {t['layout'].get('containerMax') or 'n/a'}", f"- **Breakpoints (min-width):** {', '.join(str(b) for b in t['layout']['breakpoints']['min']) or 'n/a'}" + (" (Tailwind defaults)" if t['layout']['breakpoints']['tailwindDefaults'] else "")]
    h = t["layout"].get("header")
    if h: L.append(f"- **Header:** {h['position']}, {h['height']}px tall, bg `{h['background']}`, backdrop `{h['backdropFilter']}`, border-bottom `{h['borderBottom']}`")
    if t["layout"].get("grids"): L.append("- **Grids:** " + "; ".join(f"`{g['value']}`" for g in t["layout"]["grids"][:4]))
    L += ["\n## 5. Shape, borders, elevation", f"- **Radius scale:** " + ", ".join(f"{k}={v}" for k, v in t["radius"]["scale"].items()) + f" ({t['radius']['character']})", f"- **Border patterns:** " + "; ".join(f"`{b['value']}`" for b in t["border"]["patterns"][:4])]
    sh = t["shadow"]
    L.append("- **Shadows:** " + (", ".join(f"{k}: `{v}`" for k, v in sh["levels"].items()) or "none") + (f"; glows: {sh['glows']}" if sh["glows"] else "") + (f"; backdrop: {sh['backdrop']}" if sh["backdrop"] else ""))
    mo = t["motion"]
    L += ["\n## 6. Motion", f"- **Durations:** " + ", ".join(f"{k}={v}ms" for k, v in mo["durations"].items()) + "  |  **Easing:** " + ", ".join(f"`{e['value']}`" for e in mo["easings"][:2]),
          "- **Transitioned properties:** " + ", ".join(p["property"] for p in mo["properties"][:6]), f"- **Scroll behavior:** {mo.get('scrollBehavior')}"]
    for k in mo.get("keyframes", [])[:4]: L.append(f"- keyframes `{k['name']}`: `{k['css'][:160]}`")
    if t["states"]:
        L += ["\n### Interaction states (measured)"]
        for st_ in t["states"]:
            if st_["hover"] or st_["focus"]: L.append(f"- **{st_['kind']}** \"{st_['text']}\": hover -> {'; '.join(st_['hover']) or 'none'} | focus -> {'; '.join(st_['focus']) or 'none'}")
    L += ["\n## 7. Components"]
    btn = t["components"].get("buttons", [])
    if btn: L += ["### Buttons", md_table(["Variant", "Uses", "Label", "Size", "Background", "Text", "Border", "Radius", "Padding", "Font"], [[b["variant"], b["count"], b["examples"][0] if b.get("examples") else "", f"{b['size']['w']}x{b['size']['h']}", f"`{b['style']['background']}`", f"`{b['style']['color']}`", b['style']['border'], b['style']['radius'], b['style']['padding'], f"{b['style']['fontSize']}/{b['style']['fontWeight']}"] for b in btn[:7]])]
    for key, title in (("cards", "Cards"), ("inputs", "Inputs"), ("badges", "Badges/pills"), ("navLinks", "Nav links"), ("inlineLinks", "Inline links")):
        items = t["components"].get(key) or []
        if items:
            L += [f"\n### {title}"]
            for b in items[:3]:
                stl = b["style"]; L.append(f"- x{b['count']}: bg `{stl['background']}`, text `{stl['color']}`, border {stl['border']}, radius {stl['radius']}, padding {stl['padding']}, font {stl['fontSize']}/{stl['fontWeight']}" + (f", shadow `{stl['boxShadow'][:70]}`" if stl.get("boxShadow") else "") + (f", structure `{b['structure']}`" if b.get("structure") else ""))
    ic = t["components"].get("icons")
    if ic and ic.get("count"): L += ["\n### Icons", f"- {ic['count']} inline SVGs; sizes {', '.join(x['size'] for x in ic['sizes'][:3])}; style {', '.join(x['value'] for x in ic['style'])}; stroke widths {', '.join(x['value'] for x in ic['strokeWidths'][:2]) or 'n/a'}"]
    L += ["\n## 8. Page anatomy (top to bottom)", md_table(["#", "Kind", "Height", "Heading", "Bg", "Cols", "Buttons", "Media", "Align"], [[a["index"] + 1, a["kind"], f"{a['height']}px", a.get("heading") or "", a.get("background") or "", a.get("columns") or "", a.get("buttons") or "", a.get("media") or "", a.get("align") or ""] for a in t["anatomy"]])]
    if t["responsive"]:
        L += ["\n## 9. Responsive behavior", md_table(["Viewport", "H1", "Nav links shown", "Hamburger", "Grid cols", "Section pad", "H-overflow"], [[f"{k} ({v['vw']})", v.get("h1Size"), v.get("navLinksVisible"), "yes" if v.get("hamburger") else "no", v.get("gridColumns") or "stacked", v.get("sectionPadY"), "YES" if v.get("horizontalOverflow") else "no"] for k, v in t["responsive"].items()])]
    L += ["\n## 10. Assets & tech", f"- Images: {t['assets'].get('img', 0)}, inline SVG: {t['assets'].get('svg', 0)}, video: {t['assets'].get('video', 0)}, canvas: {t['assets'].get('canvas', 0)}", "- Brand assets (logo, photography, illustration) are **references only**. Do not copy them; use placeholders or the user's own."]
    L += ["\n## 11. Unknowns & verification notes", "\n".join(f"- {u}" for u in t["unknowns"]) or "- none", "\n## 12. Rules to keep it consistent\n<!-- AGENT: write 5-8 concrete do/don't rules inferred from the tokens and screenshots (e.g. 'accent only on primary actions', 'headings always tracked -0.03em', 'cards: 1px border, no shadow until hover'). -->"]
    (out / "DESIGN.md").write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("raw"); ap.add_argument("--out", default="."); ap.add_argument("--name")
    a = ap.parse_args()
    raw = json.loads(Path(a.raw).read_text()); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    t = build(raw, a.name)
    (out / "tokens.json").write_text(json.dumps(t, indent=1))
    write_css(t, out); write_site_vars(t, out); write_tailwind(t, out); write_md(t, out)
    s = t["summary"]
    print(f"Wrote tokens.json, tokens.css, site-variables.css (if any), tailwind.config.js, tailwind-v4.css, DESIGN.md -> {out}")
    print(f"Summary: {s['mode']} mode, {s['accent']} accent, {s['corners']} corners, {s['elevation']} elevation, {s['density']} density, dark={s['darkSupport']}")
    pal = t["color"]["light"]; print("Palette:", ", ".join(f"{k}={pal[k]['value']}" for k in ("background", "foreground", "primary", "border") if k in pal))
    if t["unknowns"]: print("Check:", " | ".join(t["unknowns"][:3]))


if __name__ == "__main__":
    main()
