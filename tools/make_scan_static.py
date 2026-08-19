#!/usr/bin/env python3
"""
A single static image of the scan comparison, for touch devices.

The interactive figure is three things WebKit will not composite under an
SVG filter: a clip-path, two large sprite sheets as backgrounds, and a slider
thumb 100vh tall. On a phone that combination blanked the whole home page in
low-field mode. So in that one state — low field, WebKit — the figure steps
aside for this picture: the same comparison, the same diagonal, no moving
parts. At high field, and in every other browser, the slider is what shows.

One file is written, already resampled: the still only ever appears in
low-field mode, where the filter that would have degraded it is the one
that cannot run.

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

    # Only the degraded one is ever served: the still stands in for the
    # figure exclusively in low-field mode, where a crisp copy would be wrong.
    out = os.path.join(OUT, "scan-static-lofi.jpg")
    degrade(full, FACTOR, NOISE).save(out, "JPEG", quality=82, optimize=True,
                                      progressive=True)
    print("  %-24s %dx%d  %d KB"
          % (os.path.basename(out), sp["size"], sp["size"],
             os.path.getsize(out) // 1024))
    print("\nShown in place of the interactive figure in low-field mode,\n"
          "in WebKit only. Everywhere else the slider is what renders.")


if __name__ == "__main__":
    main()
