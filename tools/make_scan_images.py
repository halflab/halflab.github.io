#!/usr/bin/env python3
"""
Build the home-page scan slider images from real NIfTI volumes.

Rigidly co-registers the low-field scan to the high-field scan, takes a stack
of matched axial slices from each, and writes them as sprite sheets — one
image per modality containing every slice in a grid — plus the metadata the
website needs to index into them.

    python3 tools/make_scan_images.py \
        --high FV_resources/scans/sub-HYPE17_ses-GE_acq-MPRAGE_T1w.nii.gz \
        --low  FV_resources/scans/sub-HYPE17_ses-HFC_acq-iso_T1w.nii.gz

Options:
    --slices 20     number of axial slices in the stack
    --size 280      pixel size of each slice in the sprite
    --superres F    a model output volume, registered and written the same way
    --no-register   skip registration and trust the header affines
                    (only sane if the volumes are already aligned)

Writes into assets/img/scans/ and rewrites the `sprite:` block of
_data/scans.yml. Remove the `placeholder:` line from that file once you are
happy with the result.

DEPENDENCIES
    numpy and pillow only. NIfTI parsing and registration are implemented
    here so the script runs anywhere without nibabel, scipy, FSL or ANTs.

    Registration is a coarse-to-fine rigid search (3 rotations, 3
    translations) maximising normalised cross-correlation, initialised by
    centre-of-mass alignment. It is intended to be good enough for a display
    figure. It is not a substitute for a proper pipeline if you need
    quantitative alignment.
"""

import argparse
import gzip
import os
import re
import struct
import sys

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(REPO, "assets", "img", "scans")
SCANS_YML = os.path.join(REPO, "_data", "scans.yml")

DTYPES = {2: 'u1', 4: '<i2', 8: '<i4', 16: '<f4', 64: '<f8',
          256: 'i1', 512: '<u2', 768: '<u4'}


# ------------------------------------------------------------------ NIfTI
def load_nii(path):
    """Return (data, affine) for a NIfTI-1 file. numpy only."""
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as fh:
        raw = fh.read()

    endian = "<"
    if struct.unpack("<i", raw[0:4])[0] != 348:
        endian = ">"
        if struct.unpack(">i", raw[0:4])[0] != 348:
            sys.exit("%s is not a NIfTI-1 file" % path)

    dim = struct.unpack(endian + "8h", raw[40:56])
    datatype = struct.unpack(endian + "h", raw[70:72])[0]
    pixdim = struct.unpack(endian + "8f", raw[76:108])
    vox_offset = struct.unpack(endian + "f", raw[108:112])[0]
    slope = struct.unpack(endian + "f", raw[112:116])[0]
    inter = struct.unpack(endian + "f", raw[116:120])[0]
    qform_code = struct.unpack(endian + "h", raw[252:254])[0]
    sform_code = struct.unpack(endian + "h", raw[254:256])[0]
    quat = struct.unpack(endian + "6f", raw[256:280])
    srow = struct.unpack(endian + "12f", raw[280:328])

    shape = tuple(int(d) for d in dim[1:1 + dim[0]])[:3]
    fmt = DTYPES[datatype]
    if endian == ">":
        fmt = fmt.replace("<", ">")
    data = np.frombuffer(raw, dtype=np.dtype(fmt), offset=int(vox_offset))
    data = data[:int(np.prod(shape))].reshape(shape, order="F").astype(np.float32)
    if slope not in (0.0, 1.0) or inter != 0.0:
        data = data * (slope or 1.0) + inter

    if sform_code > 0:
        affine = np.vstack([np.array(srow).reshape(3, 4), [0, 0, 0, 1]])
    elif qform_code > 0:
        b, c, d, qx, qy, qz = quat
        a = np.sqrt(max(0.0, 1.0 - (b * b + c * c + d * d)))
        R = np.array([
            [a*a+b*b-c*c-d*d, 2*(b*c-a*d),     2*(b*d+a*c)],
            [2*(b*c+a*d),     a*a+c*c-b*b-d*d, 2*(c*d-a*b)],
            [2*(b*d-a*c),     2*(c*d+a*b),     a*a+d*d-b*b-c*c]])
        qfac = pixdim[0] or 1.0
        affine = np.eye(4)
        affine[:3, :3] = R @ np.diag([pixdim[1], pixdim[2], pixdim[3] * qfac])
        affine[:3, 3] = [qx, qy, qz]
    else:
        affine = np.diag([pixdim[1], pixdim[2], pixdim[3], 1.0])

    return data, affine


# ------------------------------------------------- resampling/registration
def _sample(vol, ijk):
    i, j, k = ijk[..., 0], ijk[..., 1], ijk[..., 2]
    ni, nj, nk = vol.shape
    i0 = np.floor(i).astype(np.int64)
    j0 = np.floor(j).astype(np.int64)
    k0 = np.floor(k).astype(np.int64)
    di, dj, dk = i - i0, j - j0, k - k0
    ok = ((i0 >= 0) & (i0 < ni - 1) & (j0 >= 0) &
          (j0 < nj - 1) & (k0 >= 0) & (k0 < nk - 1))
    a = np.clip(i0, 0, ni - 2)
    b = np.clip(j0, 0, nj - 2)
    c = np.clip(k0, 0, nk - 2)

    def g(u, v, w):
        return vol[a + u, b + v, c + w]

    out = (g(0,0,0)*(1-di)*(1-dj)*(1-dk) + g(1,0,0)*di*(1-dj)*(1-dk) +
           g(0,1,0)*(1-di)*dj*(1-dk)     + g(0,0,1)*(1-di)*(1-dj)*dk +
           g(1,1,0)*di*dj*(1-dk)         + g(1,0,1)*di*(1-dj)*dk +
           g(0,1,1)*(1-di)*dj*dk         + g(1,1,1)*di*dj*dk)
    return np.where(ok, out, 0.0)


def _matrix(p):
    """Parameters -> 4x4 world transform.

    6  params: rotations (deg), translations (mm)          — rigid
    9  params: + scales (relative to 1)                     — similarity
    12 params: + shears                                     — full affine

    Scale and shear are what fix the ends of the brain drifting apart:
    a rigid fit can match the middle or the vertex, but not both, if the
    two acquisitions disagree slightly about millimetres.
    """
    rx, ry, rz = np.radians(p[:3])
    cx, sx, cy, sy, cz, sz = (np.cos(rx), np.sin(rx), np.cos(ry),
                              np.sin(ry), np.cos(rz), np.sin(rz))
    R = (np.array([[cz,-sz,0],[sz,cz,0],[0,0,1]]) @
         np.array([[cy,0,sy],[0,1,0],[-sy,0,cy]]) @
         np.array([[1,0,0],[0,cx,-sx],[0,sx,cx]]))

    A = R
    if len(p) >= 9:
        A = A @ np.diag(1.0 + np.asarray(p[6:9]))
    if len(p) >= 12:
        sh = np.eye(3)
        sh[0, 1], sh[0, 2], sh[1, 2] = p[9], p[10], p[11]
        A = A @ sh

    M = np.eye(4)
    M[:3, :3] = A
    M[:3, 3] = p[3:6]
    return M


_rigid = _matrix          # kept for readability at call sites


def _grid(shape, affine, step=1):
    I, J, K = np.meshgrid(np.arange(0, shape[0], step),
                          np.arange(0, shape[1], step),
                          np.arange(0, shape[2], step), indexing="ij")
    return np.stack([I, J, K, np.ones_like(I)], -1).astype(np.float64) @ affine.T


def _resample(mov, mov_aff, world, xform):
    ijk = ((world @ xform.T) @ np.linalg.inv(mov_aff).T)[..., :3]
    return _sample(mov, ijk)


def _ncc(a, b):
    m = (a > 0) | (b > 0)
    if m.sum() < 100:
        return -1.0
    x, y = a[m] - a[m].mean(), b[m] - b[m].mean()
    d = np.sqrt((x * x).sum() * (y * y).sum())
    return float((x * y).sum() / d) if d > 0 else -1.0


def _com(vol, affine):
    t = np.percentile(vol[vol > 0], 60) if (vol > 0).any() else 0
    idx = np.argwhere(vol > t).astype(float)
    if not len(idx):
        idx = np.array([[s / 2 for s in vol.shape]])
    return (affine @ np.append(idx.mean(0), 1.0))[:3]


def register(fix, fix_aff, mov, mov_aff, dof=12):
    def norm(v):
        hi = np.percentile(v[v > 0], 99) if (v > 0).any() else 1
        return np.clip(v / (hi or 1), 0, 1)

    fixn, movn = norm(fix), norm(mov)
    dc = _com(fixn, fix_aff) - _com(movn, mov_aff)
    best = np.array([0., 0., 0., -dc[0], -dc[1], -dc[2]])

    #      step  rot   trans  scale  shear  active dof
    plan = [(8,  8.0,  12.0,  0.0,   0.0,   6),
            (4,  4.0,   6.0,  0.04,  0.0,   min(dof, 9)),
            (3,  1.5,   2.5,  0.02,  0.02,  dof),
            (3,  0.6,   1.0,  0.008, 0.008, dof)]

    for step, rot, tr, sc, sh, ndof in plan:
        if len(best) < ndof:
            best = np.concatenate([best, np.zeros(ndof - len(best))])

        world = _grid(fix.shape, fix_aff, step)
        target = fixn[::step, ::step, ::step]

        def score(p):
            return _ncc(target, _resample(movn, mov_aff, world, _matrix(p)))

        cur = score(best)
        for _ in range(4):
            improved = False
            for axis in range(ndof):
                span = (rot if axis < 3 else tr if axis < 6
                        else sc if axis < 9 else sh)
                if span == 0:
                    continue
                for delta in (span, -span, span / 2, -span / 2):
                    trial = best.copy()
                    trial[axis] += delta
                    s = score(trial)
                    if s > cur + 1e-5:
                        cur, best, improved = s, trial, True
            if not improved:
                break
        print("   %dmm (%d dof)  NCC=%.4f" % (step, ndof, cur), flush=True)

    print("   rot %s deg, trans %s mm" %
          (np.round(best[:3], 2).tolist(), np.round(best[3:6], 1).tolist()))
    if len(best) >= 9:
        print("   scale %s" % np.round(1 + best[6:9], 4).tolist())
    if len(best) >= 12:
        print("   shear %s" % np.round(best[9:12], 4).tolist())
    return _matrix(best), cur


# ------------------------------------------------------------------ output
def coverage(vol):
    """Per-slice count of above-background voxels, along axis 2."""
    if not (vol > 0).any():
        return np.zeros(vol.shape[2])
    return (vol > np.percentile(vol[vol > 0], 55)).sum(axis=(0, 1))


def shared_z_range(hf, lf, drop_low=0.30, drop_high=0.02):
    """Axial slices both volumes actually cover.

    The low-field FOV is smaller, so its coverage bounds the range. The neck
    is trimmed from the bottom by `drop_low` — brains are the subject here,
    shoulders are not.
    """
    ch, cl = coverage(hf), coverage(lf)
    ok = np.where((ch > ch.max() * 0.12) & (cl > cl.max() * 0.12))[0]
    if not len(ok):
        ok = np.where(ch > ch.max() * 0.12)[0]
    lo, hi = int(ok[0]), int(ok[-1])
    span = hi - lo
    return int(lo + span * drop_low), int(hi - span * drop_high)


def head_bbox(vol, ks, margin=0.06):
    """Square in-plane bounding box of the head over the chosen slices."""
    sub = vol[:, :, ks]
    thr = np.percentile(sub[sub > 0], 40) if (sub > 0).any() else 0
    m = (sub > thr).any(axis=2)
    idx = np.argwhere(m)
    if not len(idx):
        return 0, vol.shape[0], 0, vol.shape[1]
    i0, j0 = idx.min(0)
    i1, j1 = idx.max(0) + 1
    n = int(max(i1 - i0, j1 - j0) * (1 + margin))
    ci, cj = (i0 + i1) // 2, (j0 + j1) // 2
    return ci - n // 2, ci + n // 2, cj - n // 2, cj + n // 2


def slice_to_array(vol, k, size, box):
    i0, i1, j0, j1 = box
    n = max(i1 - i0, j1 - j0)
    sq = np.zeros((n, n), dtype=np.float32)
    si0, si1 = max(i0, 0), min(i1, vol.shape[0])
    sj0, sj1 = max(j0, 0), min(j1, vol.shape[1])
    sq[si0 - i0:si0 - i0 + (si1 - si0), sj0 - j0:sj0 - j0 + (sj1 - sj0)] = \
        vol[si0:si1, sj0:sj1, k]

    lo, hi = (np.percentile(sq[sq > 0], [1, 99.5])
              if (sq > 0).any() else (0.0, 1.0))
    if hi <= lo:
        hi = lo + 1
    x = np.clip((sq - lo) / (hi - lo), 0, 1)
    x = np.rot90(x)
    return np.asarray(Image.fromarray((x * 255).astype(np.uint8))
                      .resize((size, size), Image.LANCZOS))


def write_sprite(vol, ks, size, cols, path, box):
    rows = int(np.ceil(len(ks) / cols))
    sheet = Image.new("L", (cols * size, rows * size), 0)
    for n, k in enumerate(ks):
        tile = Image.fromarray(slice_to_array(vol, k, size, box))
        sheet.paste(tile, ((n % cols) * size, (n // cols) * size))
    sheet.save(path, quality=88, optimize=True)
    kb = os.path.getsize(path) / 1024
    print("   %s  %dx%d tiles, %.0f KB" %
          (os.path.relpath(path, REPO), cols, rows, kb))
    return cols, rows


def update_yaml(n, cols, rows, size):
    """Rewrite the sprite: block in _data/scans.yml."""
    if not os.path.exists(SCANS_YML):
        return
    block = ("sprite:\n"
             "  slices: %d\n"
             "  cols: %d\n"
             "  rows: %d\n"
             "  size: %d\n" % (n, cols, rows, size))
    text = open(SCANS_YML, encoding="utf-8").read()
    if re.search(r"^sprite:\n(?:  .*\n)+", text, re.M):
        text = re.sub(r"^sprite:\n(?:  .*\n)+", block, text, flags=re.M)
    else:
        text = text.replace("\npairs:", "\n" + block + "\npairs:")
    open(SCANS_YML, "w", encoding="utf-8").write(text)
    print("   updated _data/scans.yml (%d slices, %dx%d grid)" % (n, cols, rows))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--high", required=True)
    ap.add_argument("--low", required=True)
    ap.add_argument("--superres")
    ap.add_argument("--slices", type=int, default=20)
    ap.add_argument("--size", type=int, default=280)
    ap.add_argument("--cols", type=int, default=5)
    ap.add_argument("--drop-top", type=int, default=0,
                    help="discard N slices from the superior end, keeping the\n                          spacing of the others unchanged")
    ap.add_argument("--no-register", action="store_true")
    ap.add_argument("--dof", type=int, default=12, choices=(6, 9, 12),
                    help="6 rigid, 9 +scale, 12 +shear (default)")
    args = ap.parse_args()

    os.makedirs(OUTDIR, exist_ok=True)

    print("high field:", args.high)
    hf, hf_aff = load_nii(args.high)
    print("low field: ", args.low)
    lf, lf_aff = load_nii(args.low)

    world = _grid(hf.shape, hf_aff, 1)
    if args.no_register:
        print("  skipping registration (header affines only)")
        lf_r = _resample(lf, lf_aff, world, np.eye(4))
    else:
        print("  registering low field to high field:")
        M, _ = register(hf, hf_aff, lf, lf_aff, dof=args.dof)
        lf_r = _resample(lf, lf_aff, world, M)

    lo, hi = shared_z_range(hf, lf_r)
    ks = np.linspace(lo, hi, args.slices).round().astype(int)
    if args.drop_top:
        # Trim from the top without re-spacing, so slice indices below the
        # cut keep pointing at the same anatomy as before.
        ks = ks[:-args.drop_top]
    box = head_bbox(hf, ks)
    print("  slices %d-%d of %d, cropped to %dx%d voxels"
          % (ks[0], ks[-1], hf.shape[2], box[1] - box[0], box[3] - box[2]))

    cols, rows = write_sprite(hf, ks, args.size, args.cols,
                              os.path.join(OUTDIR, "highfield_slices.jpg"), box)
    write_sprite(lf_r, ks, args.size, args.cols,
                 os.path.join(OUTDIR, "lowfield_slices.jpg"), box)

    if args.superres:
        print("super-resolved:", args.superres)
        sr, sr_aff = load_nii(args.superres)
        Ms, _ = register(hf, hf_aff, sr, sr_aff, dof=args.dof)
        write_sprite(_resample(sr, sr_aff, world, Ms), ks, args.size, args.cols,
                     os.path.join(OUTDIR, "superres_slices.jpg"), box)

    update_yaml(len(ks), cols, rows, args.size)
    print("\nDone. Remove the `placeholder:` line from _data/scans.yml when happy.")


if __name__ == "__main__":
    main()
