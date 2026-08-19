#!/usr/bin/env python3
"""
Square team photos for assets/img/team/.

Reads the originals from FV_resources/team/ and writes 600x600 JPEGs, which
is what the site's cards and dialogs use. Originals are left untouched, so
this can be re-run at any time — drop a new photo in FV_resources/team/,
run it again, and the site picks the new one up.

Cropping. The card shows a square, and a portrait almost never is, so a crop
has to be chosen. The default takes the largest square it can and centres it
horizontally, but sits it slightly above centre vertically: in a headshot the
face is nearly always in the upper half, and a true centre crop tends to cut
the top of the head. Where that guess is wrong, FOCUS below overrides it per
photo — the numbers are the fraction of the original the crop should centre
on, so 0.5 is the middle and smaller means further left or higher up.

Usage:
    python3 tools/make_team_photos.py            # write the photos
    python3 tools/make_team_photos.py --check    # report, write nothing
"""

import os
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is missing. Install it with:\n"
             "    pip3 install pillow --break-system-packages")

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(HERE, "FV_resources", "team")
DST = os.path.join(HERE, "assets", "img", "team")

SIZE = 600          # square edge, in pixels
QUALITY = 88        # JPEG quality; 88 is visually clean at this size

# source file -> output name. The output name is what goes in _data/people.yml.
PHOTOS = {
    "Frantisek.png": "frantisek.jpg",
    "Levi.jpg":      "levente.jpg",
    "Anita.jpg":     "anita.jpg",
    "Hajer.png":     "hajer.jpg",
    "Ula.jpeg":      "ula.jpg",
    "Poppy.jpeg":    "poppy.jpg",
    "Annika.jpeg":   "annika.jpg",
}

# Per-photo crop centre as (x, y) fractions of the original. Only listed
# where the default is wrong.
FOCUS = {
    # Landscape frame, face just left of centre and high in it.
    "Levi.jpg": (0.49, 0.46),
    # Already square; the default lift would cut her chin, so hold centre.
    "Anita.jpg": (0.50, 0.50),
    "Ula.jpeg": (0.50, 0.40),
    "Poppy.jpeg": (0.53, 0.42),
    "Annika.jpeg": (0.38, 0.40),
}

DEFAULT_FOCUS = (0.50, 0.44)

# How much of the largest possible square to take, as a fraction. 1.0 is the
# whole thing; less crops in. This exists because the photos are taken at very
# different distances: a full-width crop of a half-length portrait leaves the
# face a fifth of the frame, next to a headshot where it fills half, and the
# row of cards then looks like a mistake. Cropping in equalises them.
#
# The floor is SIZE pixels — crop tighter than that and the photo would have
# to be enlarged to fill the card, which looks worse than the mismatch does.
ZOOM = {
    "Poppy.jpeg": 0.70,
    "Ula.jpeg": 0.88,
}


def square(im, focus, zoom=1.0):
    """Square crop of `im`, centred on `focus`, kept inside the frame."""
    w, h = im.size
    edge = int(round(min(w, h) * zoom))
    fx, fy = focus
    left = int(round(w * fx - edge / 2))
    top = int(round(h * fy - edge / 2))
    # A focus point near an edge would push the crop outside the image;
    # slide it back in rather than padding.
    left = max(0, min(left, w - edge))
    top = max(0, min(top, h - edge))
    return im.crop((left, top, left + edge, top + edge))


def flatten(im):
    """Drop transparency onto white, so PNG cut-outs don't become black."""
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def main():
    check = "--check" in sys.argv
    if not os.path.isdir(SRC):
        sys.exit("No FV_resources/team/ folder found at %s" % SRC)
    if not check:
        os.makedirs(DST, exist_ok=True)

    done = 0
    for src_name, out_name in PHOTOS.items():
        src = os.path.join(SRC, src_name)
        if not os.path.exists(src):
            print("  skipped  %-16s (not in FV_resources/team/)" % src_name)
            continue

        im = flatten(Image.open(src))
        before = im.size
        zoom = ZOOM.get(src_name, 1.0)
        if min(before) * zoom < SIZE:
            # Back off towards the full frame, but never past it: a zoom above
            # 1.0 asks for a crop larger than the photo, and PIL fills what
            # isn't there with black rather than refusing.
            zoom = min(1.0, SIZE / float(min(before)))
        im = square(im, FOCUS.get(src_name, DEFAULT_FOCUS), zoom)
        # LANCZOS is the slowest resample and the only one worth using when
        # the reduction is this large — Levi's photo comes down 6x.
        im = im.resize((SIZE, SIZE), Image.LANCZOS)

        if check:
            print("  would write  %-14s  %sx%s -> %dx%d"
                  % (out_name, before[0], before[1], SIZE, SIZE))
        else:
            out = os.path.join(DST, out_name)
            im.save(out, "JPEG", quality=QUALITY, optimize=True,
                    progressive=True)
            print("  %-14s  %sx%s -> %dx%d  (%d KB)"
                  % (out_name, before[0], before[1], SIZE, SIZE,
                     os.path.getsize(out) // 1024))
        done += 1

    print("\n%d photo%s %s." % (done, "" if done == 1 else "s",
                                "checked" if check else "written"))
    if not check and done:
        print("Set `photo:` in _data/people.yml to the filenames above.")


if __name__ == "__main__":
    main()
