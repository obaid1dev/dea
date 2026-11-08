#!/usr/bin/env python3
"""
DEA project scanner: understand the app you are about to redesign.

  python scan_project.py <project-dir> [--out project.json]

Detects framework, styling system (Tailwind v3/v4, CSS modules, styled-components, shadcn/ui, plain CSS,
React Native StyleSheet, Flutter), existing theme/token files, component and route folders, fonts, and
prints a token-injection plan. Read-only.
"""
import argparse, json, re, sys
from pathlib import Path

SKIP = {"node_modules", ".git", "dist", "build", ".next", ".expo", "ios", "android", "Pods", "venv", ".venv", "__pycache__", ".turbo", "coverage", ".dart_tool"}


def walk(root, exts, limit=4000):
    n = 0
    for p in root.rglob("*"):
        if any(s in p.parts for s in SKIP): continue
        if p.is_file() and p.suffix in exts:
            yield p; n += 1
            if n >= limit: return


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("--out"); a = ap.parse_args()
    root = Path(a.project)
    if not root.exists(): sys.exit("project not found")
    info = {"root": str(root), "framework": [], "styling": [], "uiLibs": [], "tokenFiles": [], "globalCss": [], "componentDirs": [], "routes": [], "fonts": [], "hardcodedColors": 0, "hardcodedColorFiles": [], "notes": []}
    pj = root / "package.json"; deps = {}
    if pj.exists():
        try:
            j = json.loads(pj.read_text()); deps = {**j.get("dependencies", {}), **j.get("devDependencies", {})}
        except Exception: pass
    for k, name in (("next", "Next.js"), ("react", "React"), ("vue", "Vue"), ("nuxt", "Nuxt"), ("svelte", "Svelte"), ("@sveltejs/kit", "SvelteKit"), ("astro", "Astro"), ("expo", "Expo"), ("react-native", "React Native"), ("vite", "Vite"), ("@remix-run/react", "Remix"), ("@angular/core", "Angular")):
        if k in deps: info["framework"].append(f"{name} {deps[k]}")
    if (root / "pubspec.yaml").exists(): info["framework"].append("Flutter")
    tw = deps.get("tailwindcss")
    if tw: info["styling"].append(f"Tailwind {tw}" + (" (v4: CSS-first @theme)" if str(tw).lstrip("^~").startswith("4") else " (v3: tailwind.config.js)"))
    for k, name in (("styled-components", "styled-components"), ("@emotion/react", "Emotion"), ("sass", "Sass"), ("nativewind", "NativeWind"), ("@mui/material", "MUI"), ("@chakra-ui/react", "Chakra UI"), ("@mantine/core", "Mantine"), ("framer-motion", "Framer Motion"), ("motion", "Motion"), ("gsap", "GSAP"), ("lucide-react", "lucide icons"), ("react-icons", "react-icons"), ("@radix-ui/react-slot", "Radix"), ("class-variance-authority", "cva (shadcn pattern)"), ("next-themes", "next-themes")):
        if k in deps: info["uiLibs"].append(name)
    if (root / "components.json").exists(): info["uiLibs"].append("shadcn/ui (components.json)")
    for pat in ("tailwind.config.*", "postcss.config.*", "theme.*", "tokens.*", "**/theme/*.ts", "**/styles/theme*", "**/constants/Colors*", "**/constants/theme*", "**/lib/theme*"):
        for p in root.glob(pat):
            if not any(s in p.parts for s in SKIP): info["tokenFiles"].append(str(p.relative_to(root)))
    css = list(walk(root, {".css", ".scss"}, 400))
    for p in css:
        t = p.read_text(errors="ignore")
        if re.search(r":root\s*\{|@theme|@tailwind|@import\s+[\"']tailwindcss", t): info["globalCss"].append(str(p.relative_to(root)))
        if p.name.endswith((".module.css", ".module.scss")) and "CSS Modules" not in info["styling"]: info["styling"].append("CSS Modules")
    if css and not info["styling"]: info["styling"].append("plain CSS/SCSS")
    for d in ("components", "src/components", "app/components", "ui", "src/ui", "components/ui", "src/components/ui", "lib/components"):
        if (root / d).is_dir(): info["componentDirs"].append(d)
    for d in ("app", "src/app", "pages", "src/pages", "src/routes", "app/(tabs)", "src/screens", "screens", "lib/screens"):
        if (root / d).is_dir(): info["routes"].append(d)
    hard, files = 0, {}
    for p in walk(root, {".tsx", ".jsx", ".ts", ".js", ".vue", ".svelte", ".css", ".scss", ".dart"}, 1500):
        t = p.read_text(errors="ignore"); n = len(re.findall(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b|rgba?\(", t))
        if n: hard += n; files[str(p.relative_to(root))] = n
        if "StyleSheet.create" in t and "React Native StyleSheet" not in info["styling"]: info["styling"].append("React Native StyleSheet")
        for m in re.finditer(r"@font-face|next/font|expo-font|useFonts|fontFamily:\s*['\"]([\w -]+)", t):
            if len(info["fonts"]) < 8 and m.group(0) not in info["fonts"]: info["fonts"].append(m.group(0)[:50])
    info["hardcodedColors"] = hard; info["hardcodedColorFiles"] = [k for k, _ in sorted(files.items(), key=lambda kv: -kv[1])[:12]]
    plan = []
    if any("Tailwind" in s for s in info["styling"]):
        plan.append("Tailwind: import tokens.css globally, extend theme from tailwind.config.js (v3) or tailwind-v4.css (@theme, v4); use semantic classes (bg-background, text-foreground, bg-primary, rounded-lg, shadow-md).")
    if any("shadcn" in s for s in info["uiLibs"]): plan.append("shadcn/ui: paste semantic variables into :root/.dark in the global CSS (names already match); then restyle ui/* primitives (button, card, input, badge) with the extracted component specs.")
    if any("React Native" in f or "Expo" in f for f in info["framework"]): plan.append("React Native/Expo: generate a theme.ts from tokens.json (colors, spacing, radius, typography), load fonts with expo-font, replace hardcoded colors; CSS shadows -> platform shadow props/elevation; no backdrop-filter without extra libs.")
    if "Flutter" in info["framework"]: plan.append("Flutter: map tokens to ThemeData/ColorScheme + TextTheme; google_fonts for open fonts.")
    if any("CSS Modules" in s or "plain" in s for s in info["styling"]): plan.append("Plain/Modules CSS: import tokens.css once at the root and replace literals with var(--token) file by file.")
    if hard > 20: plan.append(f"{hard} hardcoded color literals across {len(files)} files: replace with tokens during the pass (see hardcodedColorFiles).")
    if not plan: plan.append("Unknown styling system: add tokens.css, import it at the app root, then migrate components incrementally.")
    info["plan"] = plan
    if a.out: Path(a.out).write_text(json.dumps(info, indent=1))
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
