#!/usr/bin/env python3
"""
Degraded copies of the scan sprite sheets, for low-field mode.

The rest of the site is resampled by an SVG filter at display time. The scan
comparison cannot be: on iOS every filtered element on the home page went
blank, and the slider's subtree is the likely cause — it has the stylesheet's
only clip-path, two large sprite sheets as backgrounds, and a slider thumb
100vh tall. So the degradation is baked into a second pair of images instead,
and low-field mode swaps to them. No filter, nothing to composite, works
everywhere.

The degradation matches what the site does to photographs in script:
downsample, add per-pixel noise, scale back up with no smoothing.

Sprite sheets are a grid of slices, so the downsample factor has to divide
the tile exactly — otherwise a block of pixels straddles two slices and each
tile picks up a smear of its neighbour along the seams.

Usage:
    python3 tools/make_scans_lofi.py
    python3 tools/make_scans_lofi.py --factor 6 --noise 14
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is missing. Install it with:\n"
             "    pip3 install pillow --break-system-packages")

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is missing. Install it with:\n"
             "    pip3 install pyyaml --break-system-packages")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FACTOR = 4      # linear downsample; must divide the tile size
NOISE = 10      # peak per-pixel noise, in levels out of 255


def arg(flag, default):
    if flag in sys.argv:
        return type(default)(sys.argv[sys.argv.index(flag) + 1])
    return default


def degrade(path, out, tile, factor, noise):
    im = Image.open(path).convert("RGB")
    w, h = im.size

    if tile % factor:
        # Round down to a factor that does divide it, rather than produce
        # sheets with contaminated seams.
        while tile % factor and factor > 1:
            factor -= 1
        print("   factor adjusted to %d so it divides the %dpx tile"
              % (factor, tile))

    small = im.resize((w // factor, h // factor), Image.BOX)

    px = small.load()
    import random
    for y in range(small.size[1]):
        for x in range(small.size[0]):
            r, g, b = px[x, y]
            # Two uniform draws approximate a normal one closely enough.
            n = int((random.random() + random.random() - 1) * noise)
            px[x, y] = (max(0, min(255, r + n)),
                        max(0, min(255, g + n)),
                        max(0, min(255, b + n)))

    big = small.resize((w, h), Image.NEAREST)
    big.save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return factor


def main():
    factor = arg("--factor", FACTOR)
    noise = arg("--noise", NOISE)

    cfg = yaml.safe_load(open(os.path.join(HERE, "_data", "scans.yml")))
    tile = cfg["sprite"]["size"]

    for key in ("over", "under"):
        rel = cfg[key]["image"].lstrip("/")
        src = os.path.join(HERE, rel)
        if not os.path.exists(src):
            print("  missing %s" % rel)
            continue
        stem, ext = os.path.splitext(src)
        out = stem + "-lofi" + ext
        used = degrade(src, out, tile, factor, noise)
        print("  %-28s -> %-34s (1/%d, noise %d, %d KB)"
              % (os.path.basename(src), os.path.basename(out), used, noise,
                 os.path.getsize(out) // 1024))

    print("\nThe page picks these up automatically: scan_slider.html passes "
          "both\nfiles to the stylesheet, which swaps them in low-field mode.")


if __name__ == "__main__":
    main()
