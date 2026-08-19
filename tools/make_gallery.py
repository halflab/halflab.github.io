#!/usr/bin/env python3
"""
Build the team photo gallery from a folder of photos.

Converts HEIC/JPEG/PNG originals into web-sized JPEGs (a thumbnail for the
grid and a larger one for the lightbox), orders them newest first, and
rewrites _data/gallery.yml.

    python3 tools/make_gallery.py FV_resources/team_photo_gallery

Options:
    --thumb 600     long edge of the grid thumbnails
    --full 1500     long edge of the lightbox images
    --quality 82

REQUIREMENTS
    ImageMagick (`convert`). HEIC files need a build with the HEIC delegate,
    which is the default on macOS Homebrew and most Linux packages.

DATES
    Uses EXIF DateTimeOriginal where present, otherwise the file's
    modification time. Ordering is newest first. To caption a photo or fix a
    date, edit _data/gallery.yml afterwards — but note that re-running this
    script overwrites that file, so keep captions somewhere safe or add them
    once you are done importing.

PRIVACY
    These are photographs of identifiable people. Make sure everyone pictured
    is happy to appear on a public website before you publish.
"""

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, "assets", "img", "gallery")
GALLERY_YML = os.path.join(REPO, "_data", "gallery.yml")

EXTS = (".heic", ".heif", ".jpg", ".jpeg", ".png", ".tif", ".tiff")


def _exists(prog):
    try:
        subprocess.run([prog, "--version"], capture_output=True, timeout=20)
        return True
    except Exception:
        try:
            subprocess.run([prog, "-version"], capture_output=True, timeout=20)
            return True
        except Exception:
            return False


def backends():
    """Decoders to try, in order. macOS `sips` handles Apple HDR HEIC that
    many ImageMagick builds cannot."""
    found = []
    if _exists("sips"):
        found.append("sips")
    if _exists("heif-convert"):
        found.append("heif-convert")
    for im in ("magick", "convert"):
        if _exists(im):
            found.append(im)
            break
    return found


def capture_date(path):
    """Date for ordering, in decreasing order of reliability:

    1. A YYYYMMDD prefix in the filename. Re-exported files (PNG from HEIC,
       say) carry the export date as their mtime and often lose EXIF, so a
       dated filename is the most trustworthy signal we have.
    2. EXIF DateTimeOriginal.
    3. File modification time.
    """
    name = os.path.basename(path)
    m = re.match(r"(\d{4})(\d{2})(\d{2})(?:_(\d+))?", name)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1990 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31:
            # the _N suffix keeps same-day photos in a stable order
            seq = int(m.group(4) or 0)
            return dt.datetime(y, mo, d) + dt.timedelta(minutes=seq)
    try:
        out = subprocess.run(
            ["convert", path, "-format", "%[EXIF:DateTimeOriginal]", "info:"],
            capture_output=True, text=True, timeout=60).stdout.strip()
        m = re.match(r"(\d{4}):(\d{2}):(\d{2})[ T](\d{2}):(\d{2}):(\d{2})", out)
        if m:
            return dt.datetime(*[int(g) for g in m.groups()])
    except Exception:
        pass
    return dt.datetime.fromtimestamp(os.path.getmtime(path))


def _im(prog, src, dst, long_edge, quality):
    subprocess.run(
        [prog] + (["convert"] if prog == "magick" else []) +
        [src, "-auto-orient", "-resize", "%dx%d>" % (long_edge, long_edge),
         "-strip", "-interlace", "Plane", "-quality", str(quality), dst],
        check=True, capture_output=True, timeout=240)
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        raise RuntimeError("no output")


def render(src, dst, long_edge, quality, tools):
    """Try each decoder until one produces a usable file."""
    errors = []
    for prog in tools:
        try:
            if prog == "sips":
                subprocess.run(
                    ["sips", "-s", "format", "jpeg", "-s", "formatOptions", str(quality),
                     "-Z", str(long_edge), src, "--out", dst],
                    check=True, capture_output=True, timeout=240)
                if os.path.getsize(dst) == 0:
                    raise RuntimeError("empty")
            elif prog == "heif-convert":
                tmp = dst + ".tmp.png"
                subprocess.run(["heif-convert", src, tmp],
                               check=True, capture_output=True, timeout=240)
                _im("convert", tmp, dst, long_edge, quality)
                os.remove(tmp)
            else:
                _im(prog, src, dst, long_edge, quality)
            return True
        except Exception as exc:
            errors.append("%s: %s" % (prog, str(exc).split("\n")[0][:60]))
    if os.path.exists(dst):
        os.remove(dst)
    return errors


def read_manual(path):
    """Pull `caption` and `focus` out of an existing gallery.yml.

    Keyed by the `source` filename rather than by position: the generated
    names carry a sequence number, so inserting one photo shifts every name
    after it and matching on those would move captions onto the wrong shots.
    Entries written before `source` existed are simply not carried across.
    """
    if not os.path.exists(path):
        return {}
    kept, cur = {}, None
    for line in open(path, encoding="utf-8"):
        m = re.match(r"\s*source:\s*(\S.*)$", line)
        if m:
            cur = m.group(1).strip()
            kept.setdefault(cur, {})
            continue
        if cur:
            for field in ("caption", "focus"):
                m = re.match(r"\s*%s:\s*(\S.*)$" % field, line)
                if m:
                    kept[cur][field] = m.group(1).strip()
        if line.startswith("  - thumb:"):
            cur = None
    return {k: v for k, v in kept.items() if v}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("srcdir")
    ap.add_argument("--thumb", type=int, default=600)
    ap.add_argument("--full", type=int, default=1500)
    ap.add_argument("--quality", type=int, default=82)
    args = ap.parse_args()

    tools = backends()
    if not tools:
        sys.exit("No image decoder found. Install ImageMagick, or run this on "
                 "macOS where `sips` is built in.")
    print("decoders: %s" % ", ".join(tools))
    if not os.path.isdir(args.srcdir):
        sys.exit("No such folder: %s" % args.srcdir)

    files = [os.path.join(args.srcdir, f) for f in sorted(os.listdir(args.srcdir))
             if f.lower().endswith(EXTS)]
    if not files:
        sys.exit("No images found in %s" % args.srcdir)

    dated = sorted(((capture_date(f), f) for f in files), reverse=True)
    os.makedirs(OUTDIR, exist_ok=True)

    # clear previously generated files so removed originals do not linger
    for old in os.listdir(OUTDIR):
        if old.startswith("photo-"):
            os.remove(os.path.join(OUTDIR, old))

    # Anything hand-written in the existing file, keyed by source filename so
    # it survives a re-import even though the generated names change. Without
    # this, adding one photo silently wiped every caption and crop you had
    # set — the file said as much, but a warning is not a safeguard.
    keep = read_manual(GALLERY_YML)
    if keep:
        print("keeping %d hand-edited entr%s (caption / focus)"
              % (len(keep), "y" if len(keep) == 1 else "ies"))

    entries, skipped = [], []
    for when, src in dated:
        n = len(entries) + 1
        stem = "photo-%02d-%s" % (n, when.strftime("%Y%m%d"))
        thumb, full = stem + "-t.jpg", stem + ".jpg"
        r1 = render(src, os.path.join(OUTDIR, thumb), args.thumb, args.quality, tools)
        if r1 is not True:
            skipped.append((os.path.basename(src), r1))
            print("  %-28s SKIPPED (no decoder could read it)" % os.path.basename(src))
            continue
        render(src, os.path.join(OUTDIR, full), args.full, args.quality, tools)
        print("  %-28s %s" % (os.path.basename(src), when.date()))
        entries.append((thumb, full, when, os.path.basename(src)))

    with open(GALLERY_YML, "w", encoding="utf-8") as fh:
        fh.write("""# ============================================================
#  TEAM PHOTO GALLERY
#
#  Generated by tools/make_gallery.py. Re-running it is safe:
#  `caption` and `focus` are carried across, matched on the
#  original filename recorded in `source`.
#
#  Newest first.
#
#    caption  optional, shown on hover and in the lightbox
#    focus    where to crop the thumbnail, as a percentage down
#             the image — the strip is 4:3, so a tall photo shows
#             about half its height. 50% is the middle; lower
#             numbers move the crop up, towards a face.
#    source   the original file, used only to match on re-import
# ============================================================

photos:
""")
        for thumb, full, when, src_name in entries:
            manual = keep.get(src_name, {})
            fh.write("\n  - thumb: /assets/img/gallery/%s\n" % thumb)
            fh.write("    full: /assets/img/gallery/%s\n" % full)
            fh.write("    date: %s\n" % when.strftime("%Y-%m-%d"))
            fh.write("    source: %s\n" % src_name)
            fh.write("    caption:%s\n" % (" " + manual["caption"] if manual.get("caption") else ""))
            fh.write("    focus:%s\n" % (" " + manual["focus"] if manual.get("focus") else ""))

    kb = sum(os.path.getsize(os.path.join(OUTDIR, f))
             for f in os.listdir(OUTDIR)) / 1024
    print("\n%d photos -> assets/img/gallery/ (%.1f MB total)" % (len(entries), kb / 1024))
    print("Wrote _data/gallery.yml")
    if skipped:
        print("\n  %d file(s) could not be decoded here:" % len(skipped))
        for name, errs in skipped:
            print("    %s" % name)
        print("  These are most likely Apple HDR/10-bit HEIC. Re-run this script")
        print("  on macOS, where `sips` reads them natively, and they will be")
        print("  picked up automatically.")


if __name__ == "__main__":
    main()
