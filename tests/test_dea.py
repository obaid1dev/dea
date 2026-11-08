import json, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S = ROOT / "dea" / "scripts"
FIX = ROOT / "examples" / "lumen-demo" / "output" / "raw.json"
DEMO = ROOT / "examples" / "lumen-demo" / "index.html"
sys.path.insert(0, str(S))
import synthesize as syn  # noqa: E402


def run(*args, **kw):
    return subprocess.run([str(a) for a in args], capture_output=True, text=True, **kw)


class ColorTests(unittest.TestCase):
    def test_formats(self):
        self.assertEqual(syn.hx("#fff"), "#ffffff")
        self.assertEqual(syn.hx("rgb(79, 70, 229)"), "#4f46e5")
        self.assertEqual(syn.hx("hsl(0 0% 100%)"), "#ffffff")
        self.assertEqual(syn.hx("222.2 84% 4.9%"), "#020817")          # shadcn triplet
        self.assertEqual(syn.hx("rgba(0,0,0,0.5)"), "#00000080")
        self.assertIsNotNone(syn.parse_color("oklch(0.62 0.19 264)"))      # modern color syntax
        self.assertIsNone(syn.parse_color("not-a-color"))

    def test_contrast(self):
        self.assertEqual(syn.contrast((0, 0, 0, 1), (255, 255, 255, 1)), 21.0)

    def test_hue_names(self):
        self.assertEqual(syn.hue_name(250, 0.8), "indigo")
        self.assertEqual(syn.hue_name(10, 0.05), "neutral")

    def test_var_resolution(self):
        r = syn.resolve_vars({"--a": "#123456", "--b": "var(--a)", "--c": "var(--missing, #abcdef)"})
        self.assertEqual(r["--b"], "#123456"); self.assertEqual(r["--c"], "#abcdef")


class SynthesizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = json.loads(FIX.read_text())
        cls.t = syn.build(cls.raw, "Lumen")

    def test_palette_roles(self):
        p = self.t["color"]["light"]
        self.assertEqual(p["background"]["value"], "#fafaf9")
        self.assertEqual(p["primary"]["value"], "#4f46e5")
        self.assertEqual(p["border"]["value"], "#e7e5e0")
        self.assertEqual(p["destructive"]["value"], "#dc2626")

    def test_dark_theme(self):
        d = self.t["color"]["dark"]
        self.assertEqual(d["background"]["value"], "#0c0a09")
        self.assertIn("prefers-color-scheme", self.t["color"]["darkStrategy"])

    def test_typography_and_scale(self):
        ty = self.t["typography"]
        self.assertEqual(ty["families"]["sans"], "Inter")
        h1 = next(s for s in ty["styles"] if s["role"] in ("display", "h1"))
        self.assertEqual(h1["size"], 64); self.assertAlmostEqual(h1["letterSpacingEm"], -0.035, places=3)
        self.assertEqual(ty["baseSize"], 16)

    def test_spacing_radius_motion(self):
        self.assertIn(self.t["spacing"]["baseUnit"], (4, 8))
        self.assertIn("full", self.t["radius"]["scale"])
        self.assertTrue(self.t["motion"]["durations"])
        self.assertEqual(self.t["layout"]["containerMax"], "1120px")

    def test_components_and_states(self):
        variants = {b["variant"] for b in self.t["components"]["buttons"]}
        self.assertIn("primary", variants); self.assertTrue({"ghost", "secondary"} & variants)
        hov = [s for s in self.t["states"] if s["kind"] == "button" and s["hover"]]
        self.assertTrue(hov)

    def test_anatomy(self):
        kinds = [a["kind"] for a in self.t["anatomy"]]
        for k in ("nav", "hero", "pricing", "footer"):
            self.assertIn(k, kinds)

    def test_outputs_written_and_valid(self):
        with tempfile.TemporaryDirectory() as d:
            r = run(sys.executable, S / "synthesize.py", FIX, "--out", d, "--name", "Lumen")
            self.assertEqual(r.returncode, 0, r.stderr)
            for f in ("tokens.json", "tokens.css", "tailwind.config.js", "tailwind-v4.css", "DESIGN.md"):
                self.assertTrue((Path(d) / f).exists(), f)
            css = (Path(d) / "tokens.css").read_text()
            for v in ("--background:", "--primary:", "--radius-lg:", "--shadow-sm:", "--duration-base:", "--font-sans:", "--text-h1:"):
                self.assertIn(v, css)
            self.assertIn("prefers-color-scheme: dark", css)
            md = (Path(d) / "DESIGN.md").read_text()
            self.assertIn("<!-- AGENT:", md); self.assertIn("Page anatomy", md)
            json.loads((Path(d) / "tokens.json").read_text())
            if shutil.which("node"):
                n = run("node", "-e", f"const c=require('{Path(d) / 'tailwind.config.js'}');if(!c.theme.extend.colors.primary)process.exit(1)")
                self.assertEqual(n.returncode, 0, n.stderr)


class StaticTests(unittest.TestCase):
    def test_static_pipeline_recovers_palette(self):
        with tempfile.TemporaryDirectory() as d:
            raw = Path(d) / "raw.json"
            r = run(sys.executable, S / "analyze_css.py", DEMO, "--out", raw); self.assertEqual(r.returncode, 0, r.stderr)
            t = syn.build(json.loads(raw.read_text()), "static")
            p = t["color"]["light"]
            self.assertEqual(p["background"]["value"], "#fafaf9"); self.assertEqual(p["primary"]["value"], "#4f46e5")
            self.assertTrue(t["color"]["dark"])


class ImageToolTests(unittest.TestCase):
    def setUp(self):
        try:
            from PIL import Image  # noqa: F401
        except ImportError:
            self.skipTest("Pillow not installed")

    def test_palette_and_compare(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d) / "a.png", Path(d) / "b.png"
            Image.new("RGB", (400, 600), (250, 250, 249)).save(a)
            im = Image.new("RGB", (400, 600), (250, 250, 249)); im.paste((79, 70, 229), (50, 50, 150, 100)); im.save(b)
            p = run(sys.executable, S / "image_palette.py", b, "--sample", "60,60"); self.assertIn("#4f46e5", p.stdout)
            c = run(sys.executable, S / "compare.py", a, b, "--out", Path(d) / "out"); self.assertEqual(c.returncode, 0, c.stderr)
            self.assertIn("similarity", c.stdout); self.assertTrue((Path(d) / "out" / "side-by-side.png").exists())


class ProjectScanTests(unittest.TestCase):
    def test_detects_stack(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "src/app").mkdir(parents=True)
            (Path(d) / "package.json").write_text(json.dumps({"dependencies": {"next": "15", "react": "19", "tailwindcss": "^4.0.0"}}))
            (Path(d) / "components.json").write_text("{}")
            (Path(d) / "src/app/globals.css").write_text('@import "tailwindcss";\n:root{--background:#fff}\n')
            r = run(sys.executable, S / "scan_project.py", d); self.assertEqual(r.returncode, 0, r.stderr)
            j = json.loads(r.stdout)
            self.assertTrue(any("Next.js" in f for f in j["framework"])); self.assertTrue(any("Tailwind" in s for s in j["styling"]))
            self.assertTrue(any("shadcn" in u for u in j["uiLibs"]))


class SkillFileTests(unittest.TestCase):
    def test_frontmatter(self):
        import re
        t = (ROOT / "dea" / "SKILL.md").read_text()
        m = re.match(r"---\nname: (.+)\ndescription: (.+)\n---", t)
        self.assertTrue(m); self.assertEqual(m.group(1), "dea"); self.assertLessEqual(len(m.group(2)), 1024)
        self.assertLess(len(t.splitlines()), 500)

    def test_references_exist(self):
        t = (ROOT / "dea" / "SKILL.md").read_text()
        import re
        for ref in set(re.findall(r"references/[\w-]+\.md", t)):
            self.assertTrue((ROOT / "dea" / ref).exists(), ref)
        for sc in set(re.findall(r"scripts/[\w]+\.(?:py|mjs|js)", t)):
            self.assertTrue((ROOT / "dea" / sc).exists(), sc)


@unittest.skipUnless(shutil.which("node") and os.environ.get("DEA_E2E", "1") == "1", "node/e2e disabled")
class EndToEndTests(unittest.TestCase):
    def test_browser_extraction(self):
        with tempfile.TemporaryDirectory() as d:
            r = run("node", S / "extract.mjs", DEMO, "--out", d, "--crawl", "0")
            if r.returncode in (2, 3):
                self.skipTest("Playwright/Chromium not available: " + r.stderr[-120:])
            self.assertEqual(r.returncode, 0, r.stderr)
            raw = json.loads((Path(d) / "raw.json").read_text()); L = raw["light"]
            self.assertTrue((Path(d) / "screenshots" / "desktop-fold.png").exists())
            self.assertTrue((Path(d) / "screenshots" / "mobile-fold.png").exists())
            self.assertEqual(L["layout"]["bodyBackground"], "#fafaf9")
            self.assertTrue(raw["dark"]["differs"])
            self.assertTrue(any(s.get("hover") for s in raw["states"]))
            self.assertIn("hero", [s["kind"] for s in L["sections"]])
            t = syn.build(raw, "Lumen"); self.assertEqual(t["color"]["light"]["primary"]["value"], "#4f46e5")


if __name__ == "__main__":
    unittest.main()
