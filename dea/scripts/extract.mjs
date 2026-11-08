#!/usr/bin/env node
/**
 * DEA extractor: capture a site's design with a real browser (Playwright).
 *
 *   node extract.mjs <url | local-file | http://localhost:3000> [options]
 *
 * Options
 *   --out DIR            output folder (default ./dea-out)
 *   --viewport WxH       desktop viewport (default 1440x900)
 *   --pages /a,/b        extra paths to capture on the same origin
 *   --crawl N            also capture up to N pages linked from the nav (default 2, 0 to disable)
 *   --no-dark            skip dark-mode capture
 *   --no-responsive      skip tablet/mobile capture
 *   --no-states          skip hover/focus capture
 *   --shots-only         only take screenshots (use this on YOUR rebuilt app, then run compare.py)
 *   --auth FILE          Playwright storage-state JSON for pages behind login
 *   --wait MS            extra settle time after load/scroll (default 700)
 *   --keep-banners       do not try to dismiss cookie banners
 *   --headed             show the browser (helps with bot checks)
 *   --ua STRING          custom user agent
 *   --timeout MS         navigation timeout (default 45000)
 *
 * Output: OUT/raw.json  +  OUT/screenshots/*.png   (then run synthesize.py on raw.json)
 * Read-only: the page is only observed (a temporary data-dea attribute marks sampled elements).
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { execSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

// ---------- args ----------
const argv = process.argv.slice(2);
const flag = (n) => argv.includes(`--${n}`);
const opt = (n, d) => { const i = argv.indexOf(`--${n}`); return i >= 0 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : d; };
const VALUE_OPTS = new Set(["out", "viewport", "pages", "crawl", "auth", "wait", "ua", "timeout"]);
const positional = argv.filter((a, i) => !a.startsWith("--") && !(i > 0 && argv[i - 1].startsWith("--") && VALUE_OPTS.has(argv[i - 1].slice(2))));
const target = positional[0];
if (!target || flag("help")) {
  console.log(fs.readFileSync(fileURLToPath(import.meta.url), "utf8").split("*/")[0].replace(/^#!.*\n/, "").replace(/^\/\*\*?|^ \* ?/gm, ""));
  process.exit(target ? 0 : 1);
}
const OUT = path.resolve(opt("out", "dea-out"));
const SHOTS = path.join(OUT, "screenshots");
const [VW, VH] = opt("viewport", "1440x900").split("x").map(Number);
const WAIT = +opt("wait", 700), TIMEOUT = +opt("timeout", 45000);
const CRAWL = +opt("crawl", 2);
const shotsOnly = flag("shots-only");
fs.mkdirSync(SHOTS, { recursive: true });

function normalizeUrl(t) {
  if (/^https?:\/\//i.test(t) || /^file:\/\//i.test(t)) return t;
  if (fs.existsSync(t)) return pathToFileURL(path.resolve(t)).href;
  return "https://" + t;
}
const URL0 = normalizeUrl(target);

// ---------- load playwright from anywhere ----------
async function loadPlaywright() {
  try { return await import("playwright"); } catch {}
  const req = createRequire(import.meta.url);
  const roots = [process.cwd(), ...(process.env.NODE_PATH || "").split(path.delimiter).filter(Boolean)];
  try { roots.push(execSync("npm root -g", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim()); } catch {}
  for (const r of roots) {
    for (const base of [r, path.join(r, "node_modules")]) {
      try { const p = req.resolve("playwright", { paths: [base] }); return await import(pathToFileURL(p).href); } catch {}
    }
  }
  console.error("Playwright not found. Install once with:\n  npm i -D playwright && npx playwright install chromium\n(or run: npx -y playwright install chromium, then re-run with NODE_PATH pointing at a playwright install)");
  process.exit(2);
}
const pw = await loadPlaywright();
const chromium = pw.chromium || pw.default?.chromium;

async function launch() {
  const base = { headless: !flag("headed") };
  for (const extra of [{}, { channel: "chrome" }, { channel: "msedge" }]) {
    try { return await chromium.launch({ ...base, ...extra }); } catch (e) { var last = e; }
  }
  console.error("Could not launch a browser. Run: npx playwright install chromium\n" + (last && last.message));
  process.exit(3);
}

const inpageSrc = fs.readFileSync(path.join(here, "inpage.js"), "utf8");
const log = (...a) => console.error("[dea]", ...a);
const slug = (s) => (s.replace(/^https?:\/\/[^/]+/, "").replace(/[^a-z0-9]+/gi, "-").replace(/^-|-$/g, "") || "home").slice(0, 40);

// ---------- page helpers ----------
async function dismissBanners(page) {
  if (flag("keep-banners")) return;
  try {
    await page.evaluate(() => {
      const re = /^(accept( all)?( cookies)?|allow all|agree|got it|i agree|ok(ay)?|accept and close|continue)$/i;
      const cand = [...document.querySelectorAll("button, [role=button], a")].filter((b) => re.test((b.textContent || "").trim()) && b.closest("[class*=cookie i],[id*=cookie i],[class*=consent i],[id*=consent i],[class*=banner i],[role=dialog],[aria-label*=cookie i]"));
      if (cand[0]) cand[0].click();
    });
  } catch {}
}
async function autoScroll(page) {
  await page.evaluate(async () => {
    const h = () => Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0);
    const step = Math.max(300, Math.floor(innerHeight * 0.8)); let y = 0;
    while (y < Math.min(h(), 26000)) { scrollTo(0, y); y += step; await new Promise((r) => setTimeout(r, 140)); }
    scrollTo(0, 0); await new Promise((r) => setTimeout(r, 200));
  });
}
async function settle(page) {
  try { await page.waitForLoadState("networkidle", { timeout: 8000 }); } catch {}
  try { await page.evaluate(() => document.fonts && document.fonts.ready); } catch {}
  await dismissBanners(page);
  await autoScroll(page);
  await page.waitForTimeout(WAIT);
}
async function pageHeight(page) { return page.evaluate(() => Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0)); }
async function shoot(page, name, { full = true, maxH = 12000 } = {}) {
  const files = [];
  const fold = `${name}-fold.png`;
  try { await page.screenshot({ path: path.join(SHOTS, fold) }); files.push(fold); } catch (e) { log("fold shot failed", e.message); }
  if (full) {
    try {
      const h = Math.min(await pageHeight(page), maxH), w = (await page.viewportSize()).width;
      const f = `${name}-full.png`;
      await page.screenshot({ path: path.join(SHOTS, f), fullPage: true, clip: { x: 0, y: 0, width: w, height: h } }); files.push(f);
    } catch (e) { log("full shot failed", e.message); }
  }
  return files;
}
async function go(page, url) {
  const resp = await page.goto(url, { waitUntil: "domcontentloaded", timeout: TIMEOUT });
  const status = resp ? resp.status() : null;
  await settle(page);
  const title = await page.title();
  const blocked = (status && status >= 400) || /just a moment|access denied|attention required|verify you are human|captcha/i.test(title);
  if (blocked) log(`WARNING: page may be blocked (status ${status}, title "${title}"). Try --headed, --auth, or provide screenshots.`);
  return { status, title, blocked };
}

// ---------- state probing (hover / focus) ----------
async function probeStates(page) {
  // mark representative interactive elements (unique by visual signature)
  const marked = await page.evaluate(() => {
    document.querySelectorAll("[data-dea]").forEach((e) => e.removeAttribute("data-dea"));
    const vis = (e) => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 8 && r.height > 8 && s.visibility !== "hidden" && s.display !== "none"; };
    const sigOf = (e) => { const s = getComputedStyle(e); return [e.tagName, s.backgroundColor, s.color, s.borderTopColor, s.borderTopLeftRadius, s.fontSize, s.fontWeight, s.paddingLeft].join("|"); };
    const groups = [
      ["button", 'button, [role=button], a[class*="btn" i], a[class*="button" i], input[type=submit]'],
      ["nav-link", "header a, nav a"], ["link", "main a, article a, p a"],
      ["card", "[class*=card i], article"], ["input", "input:not([type=hidden]):not([type=checkbox]):not([type=radio]), textarea, select"]
    ];
    const picked = []; let n = 0;
    for (const [kind, sel] of groups) {
      const seen = new Set(); let k = 0;
      for (const e of document.querySelectorAll(sel)) {
        if (!vis(e) || k >= (kind === "button" ? 4 : 2)) continue;
        if (e.hasAttribute("data-dea")) continue;
        const s = sigOf(e); if (seen.has(s)) continue; seen.add(s); k++;
        e.setAttribute("data-dea", String(n)); picked.push({ id: n, kind, text: (e.textContent || e.placeholder || "").trim().slice(0, 28) }); n++;
      }
    }
    return picked;
  });
  const props = ["backgroundColor", "color", "borderTopColor", "boxShadow", "transform", "opacity", "textDecorationLine", "outline", "outlineOffset", "filter", "translate", "scale", "borderTopWidth"];
  const read = (id) => page.evaluate(([i, ps]) => { const e = document.querySelector(`[data-dea="${i}"]`); if (!e) return null; const s = getComputedStyle(e); const o = {}; ps.forEach((p) => (o[p] = s[p])); o.transition = s.transitionDuration + " " + s.transitionTimingFunction; return o; }, [id, props]);
  const results = [];
  for (const m of marked) {
    try {
      const loc = page.locator(`[data-dea="${m.id}"]`).first();
      await page.evaluate((i) => { const e = document.querySelector(`[data-dea="${i}"]`); if (e) e.scrollIntoView({ block: "center", behavior: "instant" }); }, m.id);
      await page.waitForTimeout(120);
      const base = await read(m.id);
      await loc.hover({ timeout: 3000, force: true }); await page.waitForTimeout(320);
      const hov = await read(m.id);
      await page.mouse.move(2, 2); await page.waitForTimeout(80);
      let foc = null;
      try { await loc.focus({ timeout: 1000 }); await page.keyboard.press("Shift+Tab"); await page.keyboard.press("Tab"); await page.waitForTimeout(200); foc = await read(m.id); await page.evaluate(() => document.activeElement && document.activeElement.blur()); } catch {}
      const diff = (a, b) => { const d = {}; if (a && b) for (const k of props) if (a[k] !== b[k]) d[k] = { from: a[k], to: b[k] }; return d; };
      results.push({ kind: m.kind, text: m.text, base, hover: diff(base, hov), focus: foc ? diff(base, foc) : {}, transition: base && base.transition });
    } catch (e) { results.push({ kind: m.kind, text: m.text, error: String(e.message).slice(0, 80) }); }
  }
  await page.evaluate(() => document.querySelectorAll("[data-dea]").forEach((e) => e.removeAttribute("data-dea")));
  await page.evaluate(() => scrollTo(0, 0));
  return results;
}

// ---------- responsive probe ----------
const probeSrc = `(() => {
  const q = (s) => [...document.querySelectorAll(s)];
  const vis = (e) => { const r = e.getBoundingClientRect(), s = getComputedStyle(e); return r.width > 0 && r.height > 0 && s.display !== 'none' && s.visibility !== 'hidden'; };
  const h1 = q('h1').find(vis), body = document.body, hdr = document.querySelector('header, nav');
  const grid = q('*').slice(0, 800).filter(vis).find((e) => getComputedStyle(e).display.includes('grid') && getComputedStyle(e).gridTemplateColumns.split(' ').length > 1) || null;
  const menuBtn = q('button, [role=button]').filter(vis).find((b) => /menu|navigation|hamburger|toggle/i.test((b.getAttribute('aria-label') || '') + b.className + (b.getAttribute('aria-controls') || '')));
  const main = document.querySelector('main') || body; const kids = [...main.children].filter(vis);
  return { vw: innerWidth, h1Size: h1 ? getComputedStyle(h1).fontSize : null, h1Lines: h1 ? Math.round(h1.getBoundingClientRect().height / parseFloat(getComputedStyle(h1).lineHeight || 1)) : null,
    bodyFont: getComputedStyle(body).fontSize, bodyPadX: getComputedStyle(body).paddingLeft,
    navLinksVisible: hdr ? [...hdr.querySelectorAll('a')].filter(vis).length : 0, hamburger: !!menuBtn,
    gridColumns: grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').length : 0,
    sectionPadY: kids[1] ? getComputedStyle(kids[1]).paddingTop : null, horizontalOverflow: document.documentElement.scrollWidth > innerWidth + 1,
    pageHeight: Math.max(document.documentElement.scrollHeight, body.scrollHeight) };
})()`;

// ---------- dark-mode forced probe ----------
async function forcedDarkProbe(page) {
  const baseline = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  const tries = [["class", "dark"], ["data-theme", "dark"], ["data-mode", "dark"], ["class", "theme-dark"], ["data-color-mode", "dark"], ["data-bs-theme", "dark"]];
  for (const [attr, val] of tries) {
    const res = await page.evaluate(([a, v]) => {
      const el = document.documentElement, had = el.getAttribute(a);
      if (a === "class") el.classList.add(v); else el.setAttribute(a, v);
      return new Promise((r) => setTimeout(() => {
        const s = getComputedStyle(document.body), out = { bg: s.backgroundColor, color: s.color };
        if (a === "class") { if (!had || !had.split(/\s+/).includes(v)) el.classList.remove(v); } else if (had === null) el.removeAttribute(a); else el.setAttribute(a, had);
        r(out);
      }, 350));
    }, [attr, val]);
    if (res && res.bg !== baseline) return { strategy: attr === "class" ? `class:.${val}` : `attr:[${attr}="${val}"]`, bodyBackground: res.bg, bodyColor: res.color, attr, val };
  }
  return null;
}

// ================= main =================
const browser = await launch();
const ctxOpts = { viewport: { width: VW, height: VH }, deviceScaleFactor: 1, colorScheme: "light", locale: "en-US" };
if (opt("ua")) ctxOpts.userAgent = opt("ua");
if (opt("auth") && fs.existsSync(opt("auth"))) ctxOpts.storageState = opt("auth");
const context = await browser.newContext(ctxOpts);
const page = await context.newPage();

const net = { fonts: [], stylesheets: [], images: 0, scripts: 0, hosts: {}, imageTypes: {}, failed: 0 };
page.on("response", (r) => {
  try {
    const u = r.url(), t = r.request().resourceType(), host = new URL(u).host; if (u.startsWith("data:")) return;
    net.hosts[host] = (net.hosts[host] || 0) + 1;
    if (t === "font") net.fonts.push({ url: u.slice(0, 200), bytes: +r.headers()["content-length"] || null });
    else if (t === "stylesheet") net.stylesheets.push(u.slice(0, 200));
    else if (t === "image") { net.images++; const ct = (r.headers()["content-type"] || "").split(";")[0]; net.imageTypes[ct] = (net.imageTypes[ct] || 0) + 1; }
    else if (t === "script") net.scripts++;
    if (r.status() >= 400) net.failed++;
  } catch {}
});

const result = { tool: "dea/extract", version: "1.0.0", capturedAt: new Date().toISOString(), url: URL0, viewport: { w: VW, h: VH }, screenshots: {}, notes: [] };
log("opening", URL0);
const nav = await go(page, URL0);
result.http = nav;
if (nav.blocked) result.notes.push("Page may be behind bot protection or an error page. Verify screenshots before trusting tokens.");

// desktop screenshots
result.screenshots.desktop = await shoot(page, "desktop");

if (!shotsOnly) {
  log("extracting design data");
  result.light = await page.evaluate(inpageSrc);
  result.tech = result.light.techHints;

  // per-section screenshots
  const secFiles = [];
  const ph = await pageHeight(page);
  for (const s of (result.light.sections || []).slice(0, 10)) {
    try {
      const h = Math.min(s.h, 1400, ph - s.y); if (h < 40) continue;
      const f = `section-${String(s.index + 1).padStart(2, "0")}-${s.kind}.png`;
      await page.screenshot({ path: path.join(SHOTS, f), fullPage: true, clip: { x: 0, y: Math.max(0, s.y), width: VW, height: h } }); secFiles.push(f);
    } catch (e) { /* skip */ }
  }
  result.screenshots.sections = secFiles;

  if (!flag("no-states")) { log("probing hover/focus states"); result.states = await probeStates(page); }

  // forced dark probe on light context (class/attr toggles)
  if (!flag("no-dark")) {
    result.darkMode = { prefersColorScheme: !!result.light.meta.prefersDarkRules, forced: await forcedDarkProbe(page) };
  }
  await page.evaluate(() => scrollTo(0, 0));

  // responsive
  if (!flag("no-responsive")) {
    result.responsive = {};
    for (const [name, w, h] of [["tablet", 820, 1180], ["mobile", 390, 844]]) {
      log("responsive:", name);
      await page.setViewportSize({ width: w, height: h }); await page.waitForTimeout(500);
      await page.evaluate(() => scrollTo(0, 0));
      result.responsive[name] = await page.evaluate(probeSrc);
      result.screenshots[name] = await shoot(page, name, { maxH: 9000 });
    }
    await page.setViewportSize({ width: VW, height: VH }); await page.waitForTimeout(300);
  }

  // dark via prefers-color-scheme
  if (!flag("no-dark")) {
    log("dark scheme (prefers-color-scheme)");
    const dctx = await browser.newContext({ ...ctxOpts, colorScheme: "dark" });
    const dp = await dctx.newPage();
    try {
      await go(dp, URL0);
      const d = await dp.evaluate(inpageSrc);
      const lb = result.light.layout.bodyBackground, db = d.layout.bodyBackground;
      result.dark = { differs: lb !== db, bodyBackground: db, bodyColor: d.layout.bodyColor, colors: d.colors, rootResolved: d.rootResolved, buttons: (d.components.buttons || []).slice(0, 4), contrast: d.contrast, shadows: d.shadows };
      if (result.dark.differs) { const prev = SHOTS; result.screenshots.dark = []; for (const f of ["fold"]) { const fn = `dark-${f}.png`; await dp.screenshot({ path: path.join(SHOTS, fn) }); result.screenshots.dark.push(fn); } try { const h = Math.min(await pageHeight(dp), 12000); await dp.screenshot({ path: path.join(SHOTS, "dark-full.png"), fullPage: true, clip: { x: 0, y: 0, width: VW, height: h } }); result.screenshots.dark.push("dark-full.png"); } catch {} }
    } catch (e) { result.notes.push("dark capture failed: " + e.message); }
    await dctx.close();
  }

  // extra pages
  const origin = new URL(page.url()).origin;
  let paths = (opt("pages", "") || "").split(",").map((s) => s.trim()).filter(Boolean);
  if (CRAWL > 0 && !origin.startsWith("file")) {
    const links = await page.evaluate((o) => [...new Set([...document.querySelectorAll("header a, nav a")].map((a) => { try { const u = new URL(a.href, location.href); return u.origin === o && u.pathname !== "/" && !u.hash && !/\.(pdf|zip|png|jpg|svg|xml)$/i.test(u.pathname) && !/login|sign-?in|sign-?up|register|logout|cart|account/i.test(u.pathname) ? u.pathname + u.search : null; } catch { return null; } }).filter(Boolean))], origin);
    paths = [...paths, ...links.filter((p) => !paths.includes(p))].slice(0, Math.max(CRAWL, paths.length));
  }
  result.pages = [];
  for (const p of paths.slice(0, 8)) {
    try {
      const u = new URL(p, origin).href; log("page:", u);
      const info = await go(page, u); const d = await page.evaluate(inpageSrc);
      const files = await shoot(page, `page-${slug(p)}`, { maxH: 9000 });
      result.pages.push({ url: u, path: p, ...info, title: d.meta.title, sections: d.sections, typography: d.typography.slice(0, 14), components: { buttons: d.components.buttons, cards: d.components.cards, inputs: d.components.inputs, headings: d.components.headings }, screenshots: files });
    } catch (e) { result.pages.push({ path: p, error: String(e.message).slice(0, 100) }); }
  }
} else {
  // shots-only: tablet, mobile, dark for comparison runs
  for (const [name, w, h] of [["tablet", 820, 1180], ["mobile", 390, 844]]) {
    await page.setViewportSize({ width: w, height: h }); await page.waitForTimeout(400); await page.evaluate(() => scrollTo(0, 0));
    result.screenshots[name] = await shoot(page, name, { maxH: 9000 });
  }
}

result.network = { fonts: net.fonts.slice(0, 20), stylesheets: net.stylesheets.slice(0, 20), images: net.images, imageTypes: net.imageTypes, scripts: net.scripts, failed: net.failed, hosts: Object.entries(net.hosts).sort((a, b) => b[1] - a[1]).slice(0, 15) };
await browser.close();
fs.writeFileSync(path.join(OUT, "raw.json"), JSON.stringify(result, null, 1));

const n = (result.screenshots.desktop || []).length + (result.screenshots.sections || []).length;
console.log(`Saved ${path.join(OUT, "raw.json")} and screenshots in ${SHOTS}`);
if (!shotsOnly) {
  const L = result.light;
  console.log(`Tech: ${result.tech.join(", ") || "n/a"} | sections: ${L.sections.length} | CSS vars: ${Object.values(L.cssVariables).reduce((a, o) => a + Object.keys(o).length, 0)} | button variants: ${(L.components.buttons || []).length} | dark: ${result.dark ? (result.dark.differs ? "yes" : "same") : "skipped"}`);
  console.log(`Next: python3 ${path.join(here, "synthesize.py")} ${path.join(OUT, "raw.json")} --out ${OUT}`);
}
