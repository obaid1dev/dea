#!/usr/bin/env python3
"""
DEA fidelity check: compare a reference screenshot with a screenshot of your rebuild.

  python compare.py reference.png rebuild.png --out compare-out [--bands 12]

Resizes both to the same width, writes side-by-side.png and diff.png, and prints a similarity score
plus the WORST horizontal bands (where to fix first). Exact pixel match is not the goal (content
differs); watch for large layout/color/spacing differences in the same band. Needs Pillow.
"""
import argparse, sys
from pathlib import Path
try:
    from PIL import Image, ImageChops, ImageDraw
except ImportError:
    sys.exit("Pillow required: pip install pillow")


def load(p, w):
    im = Image.open(p).convert("RGB"); return im.resize((w, max(1, round(im.height * w / im.width))), Image.Resampling.LANCZOS)


def mean_abs(im):
    px = im.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)); return sum(px) / 3 / 255


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("ref"); ap.add_argument("new"); ap.add_argument("--out", default="compare-out"); ap.add_argument("--width", type=int, default=800); ap.add_argument("--bands", type=int, default=12)
    a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    r, n = load(a.ref, a.width), load(a.new, a.width); H = max(r.height, n.height)
    def pad(im):
        c = Image.new("RGB", (a.width, H), (255, 0, 255)); c.paste(im, (0, 0)); return c
    rp, np_ = pad(r), pad(n); diff = ImageChops.difference(rp, np_)
    side = Image.new("RGB", (a.width * 2 + 20, H), (30, 30, 30)); side.paste(rp, (0, 0)); side.paste(np_, (a.width + 20, 0)); side.save(out / "side-by-side.png"); diff.save(out / "diff.png")
    score = 1 - mean_abs(diff); print(f"height ref={r.height}px new={n.height}px (ratio {n.height / r.height:.2f}) | similarity {score * 100:.1f}%")
    if abs(n.height / r.height - 1) > 0.15: print("  -> page height differs >15%: check section padding, line-heights, image heights")
    bh = max(1, H // a.bands); rows = []
    for i in range(a.bands):
        box = (0, i * bh, a.width, min(H, (i + 1) * bh)); rows.append((mean_abs(diff.crop(box)), i, box))
    print("Worst bands (fix first):")
    for d, i, box in sorted(rows, reverse=True)[:4]: print(f"  band {i + 1}/{a.bands} y={box[1]}-{box[3]} difference {d * 100:.1f}%")
    ca, cb = r.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)), n.resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    print(f"average color ref #{ca[0]:02x}{ca[1]:02x}{ca[2]:02x} vs new #{cb[0]:02x}{cb[1]:02x}{cb[2]:02x}")
    print(f"Wrote {out}/side-by-side.png and {out}/diff.png (open them and look)")


if __name__ == "__main__":
    main()
