#!/usr/bin/env python3
"""
DEA vision helper: pull measured colors out of screenshots (for screenshot-only inputs).

  python image_palette.py shot.png [--colors 8] [--sample 120,340 --sample 800,60] [--grid 4x6]

Needs Pillow. Prints dominant colors (with % of pixels), exact colors at sampled points, and an
optional grid of average colors (to find background/section bands). Use it to confirm what you
SEE in a screenshot; never guess hex values by eye.
"""
import argparse, sys
try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow required: pip install pillow")


def hexc(c): return "#%02x%02x%02x" % c[:3]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("image"); ap.add_argument("--colors", type=int, default=8)
    ap.add_argument("--sample", action="append", default=[], help="x,y pixel to read (repeatable)"); ap.add_argument("--grid", help="RxC average-color grid, e.g. 6x4")
    a = ap.parse_args()
    im = Image.open(a.image).convert("RGB"); w, h = im.size
    print(f"{a.image}: {w}x{h}")
    small = im.copy(); small.thumbnail((400, 400))
    q = small.quantize(colors=a.colors * 2, method=Image.Quantize.MEDIANCUT).convert("RGB")
    cnt = sorted(q.getcolors(maxcolors=10000), reverse=True); tot = sum(n for n, _ in cnt)
    merged = []
    for n, c in cnt:
        for m in merged:
            if sum(abs(x - y) for x, y in zip(m[1], c)) < 24: m[0] += n; break
        else: merged.append([n, c])
    print("Dominant colors:")
    for n, c in sorted(merged, reverse=True)[:a.colors]: print(f"  {hexc(c)}  {100 * n / tot:5.1f}%")
    for s in a.sample:
        x, y = (int(v) for v in s.split(","));
        if 0 <= x < w and 0 <= y < h: print(f"pixel({x},{y}) = {hexc(im.getpixel((x, y)))}")
        else: print(f"pixel({x},{y}) out of bounds")
    if a.grid:
        r, c = (int(v) for v in a.grid.lower().split("x")); print(f"Average color grid ({r} rows x {c} cols):")
        for i in range(r):
            row = []
            for j in range(c):
                box = im.crop((j * w // c, i * h // r, (j + 1) * w // c, (i + 1) * h // r)).resize((1, 1), Image.Resampling.BOX).getpixel((0, 0)); row.append(hexc(box))
            print("  " + " ".join(row))


if __name__ == "__main__":
    main()
