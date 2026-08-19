#!/usr/bin/env python3
"""
Build the three "Our work" card icons from the source artwork in
FV_resources/images_for_graphics/.

Both source icons are a brain hemisphere on the left and a network on the
right, drawn as flat line art. This script:

  * splits each at the blank column between hemisphere and network;
  * mirrors the hemisphere to make a whole brain for "Data acquisition",
    with the left hemisphere red and the right blue;
  * recolours the two network icons into theme greys.

    python3 tools/make_icons.py

Writes transparent PNGs into assets/img/icons/. Re-run after replacing the
source artwork. numpy and pillow only.
"""

import os
import sys

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "FV_resources", "images_for_graphics")
OUT = os.path.join(REPO, "assets", "img", "icons")

RED = (207, 72, 50)        # --red
BLUE = (30, 115, 166)      # --blue
CHARCOAL = (77, 77, 77)    # --charcoal
GREY = (131, 134, 138)     # lighter step for the second network icon
FOOTER_MARK = CHARCOAL     # footer outline colour; swap to RED for the logo red

HEIGHT = 240               # output height in px; icons display at ~34-54px


def load_mask(name):
    """Alpha mask of the drawn strokes, ignoring white/transparent pixels."""
    a = np.array(Image.open(os.path.join(SRC, name)).convert("RGBA"))
    rgb, alpha = a[..., :3].astype(float), a[..., 3].astype(float) / 255
    # coverage: how far each pixel is from white, weighted by its alpha
    ink = (1 - rgb.min(axis=2) / 255) * alpha
    return np.clip(ink, 0, 1)


def split(ink):
    """Return (hemisphere, network) masks, cut at the blank column."""
    cols = (ink > 0.15).sum(axis=0)
    nz = np.nonzero(cols)[0]
    mid = nz[0] + int(np.argmax(cols[nz[0]:nz[-1] + 1]))   # the flat midline
    gap = mid
    while gap < len(cols) and cols[gap] > 0:
        gap += 1
    return ink[:, :gap], ink[:, gap:]


def crop(ink):
    ys, xs = np.nonzero(ink > 0.02)
    return ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def tint(ink, colour):
    """Mask -> RGBA image in a flat colour."""
    h, w = ink.shape
    out = np.zeros((h, w, 4), np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = colour
    out[..., 3] = (ink * 255).astype(np.uint8)
    return Image.fromarray(out)


def scaled(im, height=HEIGHT):
    w = max(1, round(im.width * height / im.height))
    return im.resize((w, height), Image.LANCZOS)


def main():
    if not os.path.isdir(SRC):
        sys.exit("Source artwork not found: %s" % SRC)
    os.makedirs(OUT, exist_ok=True)

    # ---- whole brain for Data acquisition -------------------------------
    # The hemisphere faces right in the source, with its flat edge on the
    # right. Mirroring gives the opposite hemisphere; butt them together at
    # the midline so the pair reads as one brain seen from above.
    hemi, _ = split(load_mask("brain_network.png"))
    hemi = crop(hemi)

    left = tint(hemi, RED)
    right = tint(np.fliplr(hemi), BLUE)

    gap = max(2, round(hemi.shape[1] * 0.012))
    brain = Image.new("RGBA", (left.width + right.width + gap, left.height), (0, 0, 0, 0))
    brain.paste(left, (0, 0), left)
    brain.paste(right, (left.width + gap, 0), right)
    scaled(brain).save(os.path.join(OUT, "brain-lr.png"))
    print("  brain-lr.png        %s  (red left, blue right)" % (scaled(brain).size,))

    # single-colour version of the same whole brain, for the footer
    mono_mask = np.zeros((hemi.shape[0], hemi.shape[1] * 2 + gap))
    mono_mask[:, :hemi.shape[1]] = hemi
    mono_mask[:, hemi.shape[1] + gap:] = np.fliplr(hemi)
    mono = scaled(tint(mono_mask, FOOTER_MARK))
    mono.save(os.path.join(OUT, "brain-mono.png"))
    print("  brain-mono.png      %s  (single colour, footer)" % (mono.size,))

    # ---- one-colour whole brains, for the publication strand markers ----
    # Same brain as Data acquisition, but each half the same colour: red for
    # high field, blue for low. They mark which strands a paper belongs to,
    # so they have to read at 20px.
    for colour, name in ((RED, "brain-hf.png"), (BLUE, "brain-lf.png")):
        one = scaled(tint(mono_mask, colour))
        one.save(os.path.join(OUT, name))
        print("  %-20s%s  (whole brain, one colour)" % (name, one.size))

    # ---- the two network icons, in theme greys --------------------------
    for src, colour, name in (("neural_network.png", CHARCOAL, "neural-network.png"),
                              ("brain_network.png", GREY, "brain-network.png")):
        im = scaled(tint(crop(load_mask(src)), colour))
        im.save(os.path.join(OUT, name))
        print("  %-20s%s" % (name, im.size))

    print("\nWrote %s" % os.path.relpath(OUT, REPO))


if __name__ == "__main__":
    main()
