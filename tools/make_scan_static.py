#!/usr/bin/env python3
"""
A single static image of the scan comparison, for touch devices.

The interactive figure is three things WebKit will not composite under an
SVG filter: a clip-path, two large sprite sheets as backgrounds, and a slider
thumb 100vh tall. On a phone that combination blanked the whole home page in
low-field mode. Rather than fight it, phones get this picture instead — the
same comparison, the same diagonal, no moving parts.

Two files are written: the normal one, and a resampled copy for low-field
mode, since a picture cannot be degraded by a filter that will not run.

Usage:
    python3 tools/make_scan_static.py
"""

import os
import random
import sys

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Pillow is missing. Install it with:\n"
             "    pip3 install pillow --break-system-packages")

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is missing. Install it with:\n"
             "    pip3 install pyyaml --break-system-packages")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "assets", "img", "scans")

FACTOR = 4      # low-field copy: linear downsample, must divide the tile
NOISE = 10


def slice_from(sheet, cols, size, index):
    """One tile out of a sprite sheet."""
    x = (index % cols) * size
    y = (index // cols) * size
    return sheet.crop((x, y, x + size, y + size))


def compose(high, low, size):
    """High field above the diagonal, low field below — as the slider does at
    its midpoint, which is the position the figure rests at."""
    out = Image.new("RGB", (size, size), "black")
    out.paste(low, (0, 0))

    mask = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.polygon([(0, 0), (size, 0), (0, size)], fill=255)
    out.paste(high, (0, 0), mask)

    # the divider itself, so the join reads as deliberate
    d = ImageDraw.Draw(out)
    d.line([(size, 0), (0, size)], fill=(236, 236, 238), width=2)
    return out


def degrade(im, factor, noise):
    w, h = im.size
    small = im.resize((w // factor, h // factor), Image.BOX)
    px = small.load()
    for y in range(small.size[1]):
        for x in range(small.size[0]):
            r, g, b = px[x, y]
            n = int((random.random() + random.random() - 1) * noise)
            px[x, y] = (max(0, min(255, r + n)),
                        max(0, min(255, g + n)),
                        max(0, min(255, b + n)))
    return small.resize((w, h), Image.NEAREST)


def main():
    cfg = yaml.safe_load(open(os.path.join(HERE, "_data", "scans.yml")))
    sp = cfg["sprite"]
    mid = (sp["slices"] - 1) // 2

    sheets = {}
    for key in ("over", "under"):
        path = os.path.join(HERE, cfg[key]["image"].lstrip("/"))
        if not os.path.exists(path):
            sys.exit("missing %s" % cfg[key]["image"])
        sheets[key] = slice_from(Image.open(path).convert("RGB"),
                                 sp["cols"], sp["size"], mid)

    full = compose(sheets["over"], sheets["under"], sp["size"])
    a = os.path.join(OUT, "scan-static.jpg")
    full.save(a, "JPEG", quality=88, optimize=True, progressive=True)

    b = os.path.join(OUT, "scan-static-lofi.jpg")
    degrade(full, FACTOR, NOISE).save(b, "JPEG", quality=82, optimize=True,
                                      progressive=True)

    for p in (a, b):
        print("  %-24s %dx%d  %d KB"
              % (os.path.basename(p), sp["size"], sp["size"],
                 os.path.getsize(p) // 1024))
    print("\nUsed on touch devices in place of the interactive figure.")


if __name__ == "__main__":
    main()
