/*
 * DEA in-page extractor.
 * A single JavaScript EXPRESSION that runs inside a rendered page and RETURNS a JSON-serializable
 * object describing its design: tokens, typography, colors (area/char weighted), spacing, radii,
 * shadows, motion, layout, section anatomy, component variants, fonts, CSS variables, breakpoints,
 * contrast, tech hints.
 *
 * Use it three ways:
 *   1. extract.mjs (Playwright) evaluates this file for you.
 *   2. Browser tools (Claude in Chrome, Playwright MCP, DevTools MCP): paste/evaluate this file's
 *      contents in the page and read the returned value.
 *   3. DevTools console: paste it, then `copy(JSON.stringify(await <paste>))`.
 *
 * It only READS computed styles and stylesheet rules. It never modifies the page.
 */
(() => {
  const MAX_EL = 6000;
  const doc = document, root = doc.documentElement, body = doc.body;
  const cs = (el, p) => getComputedStyle(el, p);
  const out = {
    meta: {}, techHints: [], cssVariables: {}, rootResolved: {}, fonts: {}, colors: {}, typography: [],
    spacing: [], radii: [], borders: [], shadows: {}, motion: {}, layout: {}, sections: [], components: {},
    breakpoints: [], stateRules: { total: 0, sample: [] }, stylesheets: {}, assets: {}, contrast: [], truncated: false
  };

  // ---------- helpers ----------
  const cvs = doc.createElement("canvas"); cvs.width = cvs.height = 1;
  const ctx = cvs.getContext("2d", { willReadFrequently: true });
  const colorCache = new Map();
  function toRGBA(str) {
    if (!str) return null;
    if (colorCache.has(str)) return colorCache.get(str);
    let r = null;
    const m = str.match(/^rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:\s*[,/]\s*([\d.]+%?))?\s*\)$/);
    if (m) {
      const a = m[4] === undefined ? 1 : (m[4].endsWith("%") ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
      r = [Math.round(+m[1]), Math.round(+m[2]), Math.round(+m[3]), a];
    } else if (str === "transparent") r = [0, 0, 0, 0];
    else {
      try {
        ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = "#010203"; ctx.fillStyle = str; ctx.fillRect(0, 0, 1, 1);
        const d = ctx.getImageData(0, 0, 1, 1).data;
        r = [d[0], d[1], d[2], +(d[3] / 255).toFixed(3)];
      } catch (e) { r = null; }
    }
    colorCache.set(str, r); return r;
  }
  const h2 = (n) => n.toString(16).padStart(2, "0");
  const hex = (c) => !c ? null : "#" + h2(c[0]) + h2(c[1]) + h2(c[2]) + (c[3] < 1 ? h2(Math.round(c[3] * 255)) : "");
  const hexOf = (s) => hex(toRGBA(s));
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const ratio = (a, b) => { const l1 = lum(a), l2 = lum(b); return +((Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)).toFixed(2); };
  const px = (v) => { const n = parseFloat(v); return isFinite(n) ? n : null; };
  const bump = (map, key, w = 1) => { if (key == null || key === "") return; map.set(key, (map.get(key) || 0) + w); };
  const top = (map, n, mapper) => [...map.entries()].sort((a, b) => b[1] - a[1]).slice(0, n).map(([k, v]) => mapper ? mapper(k, v) : [k, v]);
  const firstFamily = (ff) => (ff || "").split(",")[0].trim().replace(/^["']|["']$/g, "");
  const trunc = (s, n) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s);
  const visible = (el, st, r) => r.width > 0 && r.height > 0 && st.visibility !== "hidden" && st.display !== "none" && +st.opacity > 0;

  // ---------- meta ----------
  const mt = (n) => (doc.querySelector(`meta[name="${n}"]`) || doc.querySelector(`meta[property="${n}"]`) || {}).content || null;
  out.meta = {
    url: location.href, title: doc.title, lang: root.lang || null, description: mt("description"),
    themeColor: mt("theme-color"), colorSchemeMeta: mt("color-scheme"), generator: mt("generator"), ogImage: mt("og:image"),
    viewportMeta: mt("viewport"), htmlClass: root.className || null,
    htmlDataAttrs: [...root.attributes].filter((a) => a.name.startsWith("data-")).map((a) => `${a.name}=${a.value}`),
    colorScheme: cs(root).colorScheme, viewport: { w: innerWidth, h: innerHeight, dpr: devicePixelRatio },
    pageHeight: Math.max(root.scrollHeight, body ? body.scrollHeight : 0), horizontalOverflow: root.scrollWidth > innerWidth + 1,
    favicons: [...doc.querySelectorAll('link[rel~="icon"],link[rel="apple-touch-icon"]')].map((l) => l.href).slice(0, 5)
  };

  // ---------- stylesheet walk ----------
  const varsBySel = {}; let varCount = 0, rulesSeen = 0, blocked = 0, inline = 0;
  const hrefs = [], faces = [], keyframes = [], bpCount = new Map(), stateSample = [];
  let stateTotal = 0, hasPrefersDark = false, hasReducedMotion = false;
  const darkSelectors = new Set();
  function bpFrom(cond) {
    const toPx = (v, u) => Math.round(parseFloat(v) * (u === "px" ? 1 : 16));
    for (const m of cond.matchAll(/(min|max)-width:\s*([\d.]+)(px|em|rem)/g)) bump(bpCount, `${m[1]}:${toPx(m[2], m[3])}`);
    for (const m of cond.matchAll(/width\s*(>=|<=|>|<)\s*([\d.]+)(px|em|rem)/g)) bump(bpCount, `${m[1].startsWith(">") ? "min" : "max"}:${toPx(m[2], m[3])}`);
  }
  function walk(rules, ctxCond) {
    for (const r of rules) {
      rulesSeen++;
      const t = r.constructor.name;
      if (r.type === 1 || t === "CSSStyleRule") {
        const sel = r.selectorText || "";
        if (/:(hover|focus|focus-visible|focus-within|active|disabled|checked)/.test(sel)) {
          stateTotal++;
          if (stateSample.length < 120) stateSample.push({ selector: trunc(sel, 120), css: trunc(r.style.cssText, 220), media: ctxCond || null });
        }
        let has = false;
        for (let i = 0; i < r.style.length; i++) {
          const name = r.style[i];
          if (name.startsWith("--") && varCount < 2500) {
            const key = (ctxCond && /prefers-color-scheme:\s*dark/.test(ctxCond) ? "@dark " : "") + sel;
            (varsBySel[key] = varsBySel[key] || {})[name] = r.style.getPropertyValue(name).trim(); varCount++; has = true;
          }
        }
        if (has && /(^|[\s,])(\.dark|\[data-theme=["']?dark|\[data-mode=["']?dark|\.theme-dark|\[data-color-mode=["']?dark)/.test(sel)) darkSelectors.add(sel);
      } else if (r.type === 4 || t === "CSSMediaRule") {
        const cond = r.conditionText || (r.media && r.media.mediaText) || "";
        if (/prefers-color-scheme:\s*dark/.test(cond)) hasPrefersDark = true;
        if (/prefers-reduced-motion/.test(cond)) hasReducedMotion = true;
        bpFrom(cond); walk(r.cssRules, cond);
      } else if (r.type === 5 || t === "CSSFontFaceRule") {
        const s = r.style;
        faces.push({ family: (s.getPropertyValue("font-family") || "").replace(/["']/g, "").trim(), weight: s.getPropertyValue("font-weight") || "400", style: s.getPropertyValue("font-style") || "normal", display: s.getPropertyValue("font-display") || null, src: trunc((s.getPropertyValue("src") || "").replace(/\s+/g, " "), 200) });
      } else if (r.type === 7 || t === "CSSKeyframesRule") {
        if (keyframes.length < 30) keyframes.push({ name: r.name, css: trunc(r.cssText.replace(/\s+/g, " "), 700) });
      } else if (r.cssRules) { try { walk(r.cssRules, ctxCond); } catch (e) {} }
    }
  }
  for (const sh of doc.styleSheets) {
    try {
      const rules = sh.cssRules; if (sh.href) hrefs.push(sh.href); else inline++;
      walk(rules, "");
    } catch (e) { blocked++; if (sh.href) hrefs.push(sh.href + " (blocked)"); }
  }
  out.cssVariables = varsBySel;
  const allVarNames = new Set(); Object.values(varsBySel).forEach((o) => Object.keys(o).forEach((n) => allVarNames.add(n)));
  const rcs = cs(root);
  allVarNames.forEach((n) => { const v = rcs.getPropertyValue(n).trim(); if (v) out.rootResolved[n] = v; });
  out.stylesheets = { count: doc.styleSheets.length, inlineStyleTags: inline, crossOriginBlocked: blocked, hrefs: hrefs.slice(0, 25), rulesSeen };
  out.breakpoints = top(bpCount, 14);
  out.stateRules = { total: stateTotal, sample: stateSample };
  out.motion.keyframes = keyframes;
  out.meta.prefersDarkRules = hasPrefersDark; out.meta.reducedMotionRules = hasReducedMotion; out.meta.darkClassSelectors = [...darkSelectors].slice(0, 8);

  // ---------- fonts ----------
  const loaded = []; try { doc.fonts.forEach((f) => loaded.push({ family: f.family.replace(/["']/g, ""), weight: f.weight, style: f.style, status: f.status })); } catch (e) {}
  out.fonts = {
    fontFaces: faces.slice(0, 40), loaded: loaded.slice(0, 40),
    links: [...doc.querySelectorAll('link[href*="fonts.googleapis"],link[href*="fonts.bunny"],link[href*="typekit"],link[href*="fonts.adobe"],link[href*="fontshare"],link[href*="use.fontawesome"]')].map((l) => l.href).slice(0, 8)
  };

  // ---------- element walk ----------
  const all = [...doc.querySelectorAll("body *")]; if (all.length > MAX_EL) out.truncated = true;
  const els = all.slice(0, MAX_EL);
  const bgW = new Map(), textW = new Map(), borderW = new Map(), accentW = new Map(), svgFillW = new Map();
  const typo = new Map(), spacing = new Map(), radii = new Map(), borders = new Map(), shadows = new Map(), textShadows = new Map();
  const filters = new Map(), backdrops = new Map(), trans = new Map(), anims = new Map(), grids = new Map(), zs = new Map(), maxWs = new Map();
  const gradients = new Map(), cursors = new Map(), svgSizes = new Map(), contrastMap = new Map();
  let flexN = 0, gridN = 0, visN = 0, stickyEls = [];
  const info = new Map(); // el -> {st, r}
  const pageArea = Math.max(1, innerWidth * Math.max(root.scrollHeight, innerHeight));

  for (const el of els) {
    const st = cs(el), r = el.getBoundingClientRect();
    if (!visible(el, st, r)) continue;
    visN++; info.set(el, { st, r });
    const tag = el.tagName.toLowerCase();
    // backgrounds weighted by area
    const bg = toRGBA(st.backgroundColor);
    if (bg && bg[3] > 0.05) bump(bgW, hex(bg), Math.min(r.width * r.height, pageArea) / pageArea);
    if (st.backgroundImage && st.backgroundImage !== "none" && /gradient/.test(st.backgroundImage)) bump(gradients, trunc(st.backgroundImage, 240));
    // text color weighted by chars
    let chars = 0; for (const n of el.childNodes) if (n.nodeType === 3) chars += n.textContent.trim().length;
    if (chars > 0) {
      const col = toRGBA(st.color); if (col) bump(textW, hex(col), chars);
      const fs = px(st.fontSize), lhRaw = st.lineHeight, lh = lhRaw === "normal" ? null : px(lhRaw), ls = st.letterSpacing === "normal" ? 0 : px(st.letterSpacing);
      const key = [firstFamily(st.fontFamily), fs, st.fontWeight, lh, ls, st.textTransform, st.fontStyle].join("|");
      let o = typo.get(key);
      if (!o) { o = { family: firstFamily(st.fontFamily), stack: trunc(st.fontFamily, 160), size: fs, weight: +st.fontWeight || st.fontWeight, lineHeight: lh, lineHeightRatio: lh && fs ? +(lh / fs).toFixed(3) : null, letterSpacing: ls, letterSpacingEm: ls && fs ? +(ls / fs).toFixed(4) : 0, transform: st.textTransform, fontStyle: st.fontStyle, chars: 0, count: 0, tags: {}, sample: trunc((el.textContent || "").trim().replace(/\s+/g, " "), 48), colors: {} }; typo.set(key, o); }
      o.chars += chars; o.count++; o.tags[tag] = (o.tags[tag] || 0) + 1; const ch = hex(col); o.colors[ch] = (o.colors[ch] || 0) + chars;
      // contrast
      if (contrastMap.size < 400) {
        const eb = effBg(el); if (eb && !eb.uncertain) { const k = hex(col) + "|" + hex(eb.c); const c = contrastMap.get(k) || { fg: hex(col), bg: hex(eb.c), ratio: ratio(col, eb.c), chars: 0, size: fs, weight: +st.fontWeight }; c.chars += chars; contrastMap.set(k, c); }
      }
    }
    // borders
    const sides = ["Top", "Right", "Bottom", "Left"].filter((s) => px(st["border" + s + "Width"]) > 0 && st["border" + s + "Style"] !== "none");
    if (sides.length) {
      const s0 = sides[0]; const bc = hexOf(st["border" + s0 + "Color"]);
      bump(borders, `${px(st["border" + s0 + "Width"])}px ${st["border" + s0 + "Style"]} ${bc} [${sides.length === 4 ? "all" : sides.map((s) => s[0].toLowerCase()).join("")}]`);
      bump(borderW, bc, r.width * r.height > 0 ? 1 : 0);
    }
    // radius
    const rs = ["TopLeft", "TopRight", "BottomRight", "BottomLeft"].map((c) => st["border" + c + "Radius"]);
    const rmax = rs.reduce((a, v) => { const n = v.endsWith("%") ? (parseFloat(v) >= 50 ? 9999 : 0) : (px(v) || 0); return Math.max(a, n); }, 0);
    if (rmax > 0) bump(radii, rmax >= 999 ? "full" : String(+rmax.toFixed(1)));
    // spacing
    for (const p of ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft", "rowGap", "columnGap", "marginTop", "marginBottom"]) {
      const v = px(st[p]); if (v && v > 0 && v <= 400 && st[p].endsWith("px")) bump(spacing, +v.toFixed(1));
    }
    // shadows etc.
    if (st.boxShadow && st.boxShadow !== "none") bump(shadows, st.boxShadow);
    if (st.textShadow && st.textShadow !== "none") bump(textShadows, st.textShadow);
    if (st.filter && st.filter !== "none") bump(filters, st.filter);
    if (st.backdropFilter && st.backdropFilter !== "none") bump(backdrops, st.backdropFilter);
    // motion
    if (st.transitionDuration && st.transitionDuration !== "0s") {
      const props = st.transitionProperty.split(",").map((s) => s.trim()), durs = st.transitionDuration.split(",").map((s) => s.trim()), eases = st.transitionTimingFunction.split(/,(?![^(]*\))/).map((s) => s.trim());
      props.forEach((p, i) => { const d = durs[i % durs.length]; bump(trans, `${p}|${Math.round(parseFloat(d) * (d.endsWith("ms") ? 1 : 1000))}ms|${eases[i % eases.length]}`); });
    }
    if (st.animationName && st.animationName !== "none") bump(anims, `${st.animationName}|${st.animationDuration}|${st.animationTimingFunction}|${st.animationIterationCount}`);
    // layout
    if (st.display.includes("flex")) flexN++;
    if (st.display.includes("grid")) { gridN++; bump(grids, `${trunc(st.gridTemplateColumns, 80)}|gap:${st.columnGap}`); }
    if (st.zIndex !== "auto") bump(zs, st.zIndex);
    if (st.maxWidth !== "none" && st.maxWidth.endsWith("px") && r.width >= 480) bump(maxWs, st.maxWidth);
    if ((st.position === "sticky" || st.position === "fixed") && stickyEls.length < 8) stickyEls.push({ tag, position: st.position, top: st.top, rect: rectOf(r), cls: trunc(el.className && el.className.baseVal === undefined ? String(el.className) : "", 60) });
    if (st.cursor && st.cursor !== "auto") bump(cursors, st.cursor);
    if (tag === "svg") { bump(svgSizes, `${Math.round(r.width)}x${Math.round(r.height)}`); const f = hexOf(st.fill), sk = hexOf(st.stroke); if (f && st.fill !== "none") bump(svgFillW, f); if (sk && st.stroke !== "none") bump(accentW, sk, 0.0); }
  }

  function rectOf(r) { return { x: Math.round(r.x), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height) }; }
  function effBg(el) {
    const layers = []; let uncertain = false;
    for (let e = el; e; e = e.parentElement) {
      const s = cs(e); if (s.backgroundImage && s.backgroundImage !== "none") uncertain = true;
      const c = toRGBA(s.backgroundColor); if (c && c[3] > 0) { layers.push(c); if (c[3] >= 0.99) break; }
    }
    let base = [255, 255, 255, 1]; // assume white canvas unless opaque found
    if (layers.length && layers[layers.length - 1][3] >= 0.99) base = layers.pop();
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i], a = l[3]; base = [Math.round(l[0] * a + base[0] * (1 - a)), Math.round(l[1] * a + base[1] * (1 - a)), Math.round(l[2] * a + base[2] * (1 - a)), 1]; }
    return { c: base, uncertain };
  }

  out.colors = {
    background: top(bgW, 24, (k, v) => ({ value: k, weight: +v.toFixed(4) })),
    text: top(textW, 24, (k, v) => ({ value: k, chars: v })),
    border: top(borderW, 12, (k, v) => ({ value: k, count: v })),
    svgFill: top(svgFillW, 8, (k, v) => ({ value: k, count: v })),
    gradients: top(gradients, 10, (k, v) => ({ value: k, count: v }))
  };
  out.typography = [...typo.values()].sort((a, b) => b.chars - a.chars).slice(0, 70).map((o) => ({ ...o, colors: Object.entries(o.colors).sort((a, b) => b[1] - a[1]).slice(0, 3).map((x) => x[0]) }));
  out.spacing = top(spacing, 40, (k, v) => ({ px: k, count: v }));
  out.radii = top(radii, 14, (k, v) => ({ value: k, count: v }));
  out.borders = top(borders, 14, (k, v) => ({ value: k, count: v }));
  out.shadows = {
    box: top(shadows, 14, (k, v) => ({ value: k, count: v })), text: top(textShadows, 5, (k, v) => ({ value: k, count: v })),
    filter: top(filters, 5, (k, v) => ({ value: k, count: v })), backdrop: top(backdrops, 5, (k, v) => ({ value: k, count: v }))
  };
  out.motion.transitions = top(trans, 24, (k, v) => { const [prop, dur, ease] = k.split("|"); return { property: prop, duration: dur, easing: ease, count: v }; });
  out.motion.animations = top(anims, 12, (k, v) => { const [name, dur, ease, iter] = k.split("|"); return { name, duration: dur, easing: ease, iterations: iter, count: v }; });
  out.motion.scrollBehavior = cs(root).scrollBehavior;
  out.contrast = [...contrastMap.values()].sort((a, b) => b.chars - a.chars).slice(0, 18);

  // ---------- layout ----------
  const bodySt = cs(body);
  const header = doc.querySelector("header, [role=banner]") || doc.querySelector("nav");
  const hdr = header ? (() => { const s = cs(header), r = header.getBoundingClientRect(); return { tag: header.tagName.toLowerCase(), position: s.position, height: Math.round(r.height), width: Math.round(r.width), background: hexOf(s.backgroundColor), backdropFilter: s.backdropFilter, borderBottom: `${s.borderBottomWidth} ${s.borderBottomStyle} ${hexOf(s.borderBottomColor)}`, boxShadow: s.boxShadow, paddingX: s.paddingLeft, links: header.querySelectorAll("a").length, buttons: header.querySelectorAll("button, [class*=btn i]").length }; })() : null;
  out.layout = {
    rootFontSize: rcs.fontSize, bodyFont: firstFamily(bodySt.fontFamily), bodyFontSize: bodySt.fontSize, bodyFontWeight: bodySt.fontWeight, bodyLineHeight: bodySt.lineHeight, bodyBackground: hexOf(bodySt.backgroundColor) || hexOf(rcs.backgroundColor), bodyColor: hexOf(bodySt.color),
    containerMaxWidths: top(maxWs, 6, (k, v) => ({ value: k, count: v })), grids: top(grids, 8, (k, v) => ({ value: k, count: v })),
    flexShare: visN ? +(flexN / visN).toFixed(3) : 0, gridShare: visN ? +(gridN / visN).toFixed(3) : 0, zIndexes: top(zs, 8, (k, v) => ({ value: k, count: v })),
    header: hdr, stickyOrFixed: stickyEls, cursors: top(cursors, 5, (k, v) => ({ value: k, count: v })), visibleElements: visN
  };

  // ---------- sections (page anatomy) ----------
  const main = doc.querySelector("main") || body;
  let blocks = [...main.children].filter((e) => info.has(e) && info.get(e).r.height > 60);
  if (blocks.length <= 1 && blocks[0]) blocks = [...blocks[0].children].filter((e) => info.has(e) && info.get(e).r.height > 60);
  const outer = [...body.children].filter((e) => /^(HEADER|NAV)$/.test(e.tagName) && info.has(e));
  const footer = [...body.querySelectorAll("footer")].pop(); if (footer && info.has(footer) && !blocks.includes(footer)) blocks.push(footer);
  [...outer.reverse()].forEach((e) => { if (!blocks.includes(e)) blocks.unshift(e); });
  blocks.slice(0, 28).forEach((el, i) => {
    const { st, r } = info.get(el); const h = el.querySelector("h1,h2,h3"); const imgs = el.querySelectorAll("img,svg,video,canvas,picture").length;
    const cards = el.querySelectorAll("[class*=card i], article, li").length; const grid = [...el.querySelectorAll("*")].slice(0, 120).find((c) => info.has(c) && info.get(c).st.display.includes("grid"));
    const cols = grid ? info.get(grid).st.gridTemplateColumns.split(/\s+(?![^(]*\))/).length : 0;
    const tag = el.tagName.toLowerCase(); let kind = "section";
    const label = el.id + " " + el.className + " " + (h ? h.textContent : "");
    if (tag === "header" || tag === "nav") kind = "nav"; else if (tag === "footer") kind = "footer";
    else if (i <= 2 && el.querySelector("h1")) kind = "hero";
    else if (/pric|plans/i.test(label) && cards >= 2) kind = "pricing";
    else if (/faq|question/i.test(label)) kind = "faq";
    else if (el.querySelectorAll("blockquote, [class*=testimonial i], [class*=quote i]").length) kind = "testimonials";
    else if ((imgs >= 4 && r.height < 260) || (!h && r.height < 180 && el.querySelectorAll("span, img, svg, a").length >= 4)) kind = "logo-strip";
    else if (cols >= 3 && cards >= 3) kind = "feature-grid";
    else if (el.querySelectorAll("button, a[class*=btn i], a[class*=button i]").length >= 1 && r.height < 420 && i > 2 && !cards) kind = "cta";
    out.sections.push({ index: i, tag, id: el.id || null, kind, y: Math.round(r.y + scrollY), h: Math.round(r.height), w: Math.round(r.width), background: hexOf(st.backgroundColor), bgImage: st.backgroundImage !== "none" ? trunc(st.backgroundImage, 100) : null, paddingY: `${st.paddingTop} ${st.paddingBottom}`, heading: h ? trunc(h.textContent.trim().replace(/\s+/g, " "), 60) : null, headingTag: h ? h.tagName.toLowerCase() : null, media: imgs, buttons: el.querySelectorAll("button, a[class*=btn i], a[class*=button i]").length, links: el.querySelectorAll("a").length, gridColumns: cols || null, align: st.textAlign });
  });

  // ---------- components ----------
  const sn = (el) => {
    const x = info.get(el) || { st: cs(el), r: el.getBoundingClientRect() }, st = x.st, r = x.r;
    const bg = toRGBA(st.backgroundColor);
    const bsides = ["Top", "Right", "Bottom", "Left"].filter((s) => px(st["border" + s + "Width"]) > 0 && st["border" + s + "Style"] !== "none");
    return {
      tag: el.tagName.toLowerCase(), role: el.getAttribute("role"), text: trunc((el.textContent || "").trim().replace(/\s+/g, " "), 36),
      size: { w: Math.round(r.width), h: Math.round(r.height) },
      style: {
        display: st.display, position: st.position, color: hexOf(st.color), background: bg && bg[3] > 0 ? hex(bg) : "transparent",
        backgroundImage: st.backgroundImage !== "none" ? trunc(st.backgroundImage, 120) : undefined,
        border: bsides.length ? `${st["border" + bsides[0] + "Width"]} ${st["border" + bsides[0] + "Style"]} ${hexOf(st["border" + bsides[0] + "Color"])} [${bsides.length === 4 ? "all" : bsides.map((s) => s[0].toLowerCase()).join("")}]` : "none",
        radius: st.borderTopLeftRadius, padding: st.padding, margin: st.margin !== "0px" ? st.margin : undefined, gap: st.gap !== "normal" ? st.gap : undefined,
        fontFamily: firstFamily(st.fontFamily), fontSize: st.fontSize, fontWeight: st.fontWeight, lineHeight: st.lineHeight, letterSpacing: st.letterSpacing, textTransform: st.textTransform !== "none" ? st.textTransform : undefined,
        boxShadow: st.boxShadow !== "none" ? st.boxShadow : undefined, backdropFilter: st.backdropFilter !== "none" ? st.backdropFilter : undefined, opacity: +st.opacity < 1 ? st.opacity : undefined,
        transition: st.transitionDuration !== "0s" ? `${st.transitionProperty} ${st.transitionDuration} ${st.transitionTimingFunction}` : undefined, cursor: st.cursor !== "auto" ? st.cursor : undefined,
        textDecoration: st.textDecorationLine !== "none" ? st.textDecorationLine : undefined, outline: st.outlineStyle !== "none" ? `${st.outlineWidth} ${st.outlineStyle} ${hexOf(st.outlineColor)}` : undefined
      }
    };
  };
  const sig = (s) => [s.style.background, s.style.color, s.style.border, s.style.radius, s.style.fontSize, s.style.fontWeight, s.style.padding].join("|");
  const groupBy = (els, limit = 6, ex = 3) => {
    const g = new Map();
    for (const el of els) { if (!info.has(el)) continue; const s = sn(el), k = sig(s); const o = g.get(k) || { count: 0, examples: [], sample: s }; o.count++; if (o.examples.length < ex && s.text) o.examples.push(s.text); g.set(k, o); }
    return [...g.values()].sort((a, b) => b.count - a.count).slice(0, limit).map((o) => ({ count: o.count, examples: o.examples, ...o.sample }));
  };
  const isBtnLike = (a) => { const x = info.get(a); if (!x) return false; const st = x.st, r = x.r, bg = toRGBA(st.backgroundColor); const pxl = px(st.paddingLeft) || 0; return r.height >= 24 && r.height <= 84 && pxl >= 10 && ((bg && bg[3] > 0.3) || px(st.borderTopWidth) > 0) && (px(st.borderTopLeftRadius) || 0) >= 0; };
  const qa = (sel) => [...doc.querySelectorAll(sel)];
  const btnEls = new Set([...qa('button, [role=button], input[type=submit], input[type=button], [class*="btn" i], [class*="button" i]'), ...qa("a").filter(isBtnLike)].filter((e) => info.has(e) && !e.closest("svg")));
  out.components.buttons = groupBy([...btnEls].filter((e) => (info.get(e).r.height <= 90)), 8);
  out.components.inputs = groupBy(qa('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea, select'), 4).map((c, i) => c);
  const firstInput = qa('input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea').find((e) => info.has(e));
  if (firstInput) { try { out.components.inputPlaceholderColor = hexOf(cs(firstInput, "::placeholder").color); } catch (e) {} }
  const navLinks = qa("header a, nav a").filter((e) => info.has(e) && !btnEls.has(e)), bodyLinks = qa("main a, article a, p a, li a").filter((e) => info.has(e) && !btnEls.has(e) && !e.closest("nav, header"));
  out.components.navLinks = groupBy(navLinks, 2); out.components.inlineLinks = groupBy(bodyLinks, 3);
  const cardCandidates = qa("div, article, li, a, section").filter((e) => { const x = info.get(e); if (!x) return false; const { st, r } = x; if (r.width < 160 || r.width > 760 || r.height < 90 || r.height > 760) return false; const rad = px(st.borderTopLeftRadius) || 0; const bg = toRGBA(st.backgroundColor); const hasBorder = px(st.borderTopWidth) > 0 && st.borderTopStyle !== "none"; const hasSh = st.boxShadow !== "none"; const par = e.parentElement ? effBg(e.parentElement).c : [255, 255, 255, 1]; const differs = bg && bg[3] > 0.2 && (Math.abs(bg[0] - par[0]) + Math.abs(bg[1] - par[1]) + Math.abs(bg[2] - par[2])) > 6; return (rad > 0 || hasBorder) && (differs || hasBorder || hasSh) && e.querySelector("h1,h2,h3,h4,h5,p,img"); });
  const innerMost = cardCandidates.filter((e) => !cardCandidates.some((o) => o !== e && e.contains(o)));
  out.components.cards = groupBy(innerMost, 4).map((c, i) => ({ ...c, structure: (() => { const el = innerMost.find((e) => sig(sn(e)) === sig(c)); return el ? [...el.children].slice(0, 6).map((k) => k.tagName.toLowerCase()).join(" > ") : null; })() }));
  out.components.badges = groupBy(qa("span, a, div, li").filter((e) => { const x = info.get(e); if (!x) return false; const { st, r } = x; const t = (e.textContent || "").trim(); return t.length > 0 && t.length <= 26 && r.height <= 34 && r.width <= 190 && px(st.fontSize) <= 14 && (px(st.borderTopLeftRadius) || 0) >= 6 && ((toRGBA(st.backgroundColor) || [0, 0, 0, 0])[3] > 0.05 || px(st.borderTopWidth) > 0) && !btnEls.has(e) && e.children.length <= 2; }), 3);
  out.components.headings = {}; ["h1", "h2", "h3", "h4", "h5", "h6"].forEach((t) => { const e = qa(t).find((x) => info.has(x)); if (e) out.components.headings[t] = sn(e); });
  const para = qa("main p, article p, p").find((e) => info.has(e) && (e.textContent || "").length > 60); if (para) out.components.paragraph = sn(para);
  const small = qa("small, figcaption, caption, [class*=caption i], [class*=muted i]").find((e) => info.has(e)); if (small) out.components.small = sn(small);
  const code = qa("pre, code, kbd").find((e) => info.has(e)); if (code) out.components.code = sn(code);
  const bq = qa("blockquote").find((e) => info.has(e)); if (bq) out.components.blockquote = sn(bq);
  const th = qa("th").find((e) => info.has(e)); if (th) out.components.tableHead = sn(th);
  const dlg = qa("[role=dialog], dialog").find((e) => info.has(e)); if (dlg) out.components.dialog = sn(dlg);
  const tabs = qa("[role=tablist]").find((e) => info.has(e)); if (tabs) out.components.tabs = sn(tabs);
  const hr = qa("hr").find((e) => info.has(e)); if (hr) out.components.divider = sn(hr);
  if (footer && info.has(footer)) out.components.footer = sn(footer);
  if (header && info.has(header)) out.components.header = sn(header);
  const imgs = qa("img").filter((e) => info.has(e) && info.get(e).r.width > 80);
  out.components.images = groupBy(imgs, 3).map((c) => c);
  const avatars = qa("img").filter((e) => info.has(e) && info.get(e).r.width <= 72 && /50%|9999|999/.test(info.get(e).st.borderTopLeftRadius)); if (avatars[0]) out.components.avatar = sn(avatars[0]);
  const svgs = qa("svg").filter((e) => info.has(e)); const strokeW = new Map(), fillMode = new Map();
  svgs.slice(0, 200).forEach((s) => { const st = info.get(s).st; if (px(st.strokeWidth)) bump(strokeW, st.strokeWidth); bump(fillMode, st.fill === "none" ? "outline(stroke)" : "filled"); });
  out.components.icons = { count: svgs.length, sizes: top(svgSizes, 6, (k, v) => ({ size: k, count: v })), strokeWidths: top(strokeW, 4, (k, v) => ({ value: k, count: v })), style: top(fillMode, 2, (k, v) => ({ value: k, count: v })) };

  // ---------- assets & tech ----------
  const logoEl = header ? header.querySelector("a img, a svg, img, svg") : null;
  out.assets = {
    img: qa("img").length, svg: qa("svg").length, video: qa("video").length, canvas: qa("canvas").length, iframe: qa("iframe").length, picture: qa("picture").length,
    logoCandidate: logoEl ? { type: logoEl.tagName.toLowerCase(), src: logoEl.src || null, w: Math.round(logoEl.getBoundingClientRect().width), h: Math.round(logoEl.getBoundingClientRect().height), note: "reference only; do not copy brand assets" } : null,
    backgroundImages: els.filter((e) => info.has(e) && /url\(/.test(info.get(e).st.backgroundImage)).length,
    objectFit: (() => { const m = new Map(); imgs.forEach((e) => bump(m, info.get(e).st.objectFit)); return top(m, 3); })(),
    themeToggles: qa('[aria-label*="theme" i],[aria-label*="dark" i],[aria-label*="light mode" i],[title*="theme" i]').slice(0, 3).map((e) => trunc(e.getAttribute("aria-label") || e.title, 40))
  };
  const classBag = new Map(); els.slice(0, 2500).forEach((e) => { const c = e.getAttribute("class"); if (c) c.split(/\s+/).forEach((k) => bump(classBag, k)); });
  const classNames = [...classBag.keys()]; const util = classNames.filter((k) => /^(flex|grid|px-|py-|p-|m[xytrbl]?-|text-(xs|sm|base|lg|xl|\d)|bg-|rounded|gap-|items-|justify-|w-|h-|font-|border|shadow|space-)/.test(k)).length;
  const H = [];
  if (window.__NEXT_DATA__ || qa("#__next, next-route-announcer").length) H.push("Next.js");
  if (qa("#__nuxt, [data-n-head]").length) H.push("Nuxt");
  if (qa("astro-island, [data-astro-cid-]").length || classNames.some((k) => k.startsWith("astro-"))) H.push("Astro");
  if (qa("[ng-version]").length) H.push("Angular");
  if (qa("[data-reactroot]").length || window.React || [...doc.querySelectorAll("div")].slice(0, 50).some((d) => Object.keys(d).some((k) => k.startsWith("__reactContainer")))) H.push("React");
  if (qa("[data-v-app], [data-server-rendered]").length || classNames.some((k) => /^data-v-/.test(k))) H.push("Vue");
  if (classNames.some((k) => k.startsWith("svelte-"))) H.push("Svelte");
  if (classNames.length && util / Math.max(1, classNames.length) > 0.3 && util > 25) H.push("Tailwind CSS (utility-class heavy)");
  if (qa("[data-radix-collection-item], [data-radix-popper-content-wrapper], [data-state], [data-slot]").length) H.push("Radix/shadcn-style primitives");
  if (classNames.includes("btn") && classNames.some((k) => /^btn-(primary|secondary|success|danger|outline-)/.test(k)) && (classNames.some((k) => /^(navbar|navbar-expand.*|container-fluid)$/.test(k) || /^col-(sm|md|lg|xl|xxl)?-?\d/.test(k)) || hrefs.some((h) => /bootstrap/i.test(h)))) H.push("Bootstrap");
  if (qa("[data-framer-name], [data-framer-component-type]").length) H.push("Framer");
  if (qa("[data-wf-page], html.w-mod-js").length) H.push("Webflow");
  if (classNames.some((k) => /^wp-/.test(k)) || /wordpress/i.test(out.meta.generator || "")) H.push("WordPress");
  if (window.Shopify) H.push("Shopify");
  ["gsap", "ScrollTrigger", "Lenis", "THREE", "lottie", "Swiper", "AOS", "anime", "Alpine", "htmx", "Webflow"].forEach((n) => { if (window[n]) H.push("lib:" + n); });
  if (qa("[data-aos]").length) H.push("AOS scroll animations");
  const iconLib = classNames.find((k) => /^(lucide|feather|bi-|fa-|fas|far|fab|material-icons|ri-|ph-|tabler|heroicon)/.test(k)); if (iconLib) H.push("icons:" + iconLib);
  out.techHints = H;
  return out;
})()
