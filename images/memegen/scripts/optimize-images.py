#!/usr/bin/env python3
"""
Optimize meme template background images for repo storage + social rendering.

Meme templates don't need 4000px / multi-MB source blanks: memegen caps output
at 1920x1080 and social platforms re-compress anyway. This caps the long side
and re-compresses every `default.*` under the given template dirs, in place.

Format policy (memegen-safe - it treats .webp as animated, so we never emit
webp for static blanks):
  - GIF (animated)      -> gifsicle, resized + lossy
  - PNG with alpha      -> pngquant (lossy palette) + oxipng  (stays PNG)
  - everything else     -> JPEG q88 (jpegoptim)               (old default.png removed)

Never upscales. Strips metadata. Idempotent (re-running shrinks little further).

Usage:
    python3 optimize-images.py images/memegen/staging/trending images/memegen/extra-templates
    python3 optimize-images.py <dir> --max-side 1500 --jpeg-quality 88
"""
from __future__ import annotations

import argparse
import concurrent.futures
import subprocess
import sys
from pathlib import Path

def run(cmd):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode

def identify(f):
    try:
        out = subprocess.check_output(["magick", "identify", "-format", "%m|%w|%h|%[opaque]|%n", str(f) + "[0]"],
                                      stderr=subprocess.DEVNULL).decode()
        fmt, w, h, opaque, n = out.split("|")[:5]
        return fmt.upper(), int(w), int(h), opaque, int(n or 1)
    except Exception:
        return None

def optimize(f: Path, cap: int, q: int) -> tuple[int, int]:
    before = f.stat().st_size
    info = identify(f)
    if not info:
        return before, before
    fmt, w, h, opaque, _ = info
    long = max(w, h)
    resize = f"{cap}x{cap}>"  # '>' = shrink only
    ext = f.suffix.lower().lstrip(".")
    # Keep PNG only when there's REAL transparency; an opaque alpha channel
    # (common in screenshots) would otherwise get palette-banded by pngquant.
    has_alpha = opaque == "False"

    if ext == "gif":
        out = f.with_suffix(".gif")
        if long > cap:
            run(["gifsicle", "--resize-fit", f"{cap}x{cap}", "-O3", "--lossy=80", str(f), "-o", str(out) + ".tmp"])
        else:
            run(["gifsicle", "-O3", "--lossy=80", str(f), "-o", str(out) + ".tmp"])
        tmp = Path(str(out) + ".tmp")
        if tmp.exists() and tmp.stat().st_size > 0:
            tmp.replace(out)
        return before, f.stat().st_size

    if has_alpha and fmt == "PNG":
        tmp = f.with_name("opt_tmp.png")
        run(["magick", str(f), "-resize", resize, "-strip", str(tmp)])
        if run(["pngquant", "--quality=65-92", "--strip", "--force", "--output", str(f), str(tmp)]) != 0:
            tmp.replace(f)  # pngquant declined (quality floor) -> keep resized
        else:
            tmp.unlink(missing_ok=True)
        run(["oxipng", "-o", "2", "--strip", "safe", "-q", str(f)])
        return before, f.stat().st_size

    # static, no alpha -> JPEG
    jpg = f.with_suffix(".jpg")
    run(["magick", str(f), "-resize", resize, "-background", "white", "-flatten", "-strip", "-quality", str(q), str(jpg)])
    run(["jpegoptim", f"-m{q}", "--strip-all", "--all-progressive", str(jpg)])
    for old in f.parent.glob("default.*"):
        if old != jpg:
            old.unlink()
    return before, jpg.stat().st_size

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dirs", nargs="+", type=Path)
    ap.add_argument("--max-side", type=int, default=1500)
    ap.add_argument("--jpeg-quality", type=int, default=88)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    files = []
    for d in args.dirs:
        files += [p for p in d.glob("*/default.*")]
    if not files:
        sys.exit("no default.* template images found")
    print(f"optimizing {len(files)} images (cap {args.max_side}px, jpeg q{args.jpeg_quality})...")

    tb = ta = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for b, a in pool.map(lambda f: optimize(f, args.max_side, args.jpeg_quality), files):
            tb += b; ta += a
    print(f"before {tb/1e6:.1f} MB -> after {ta/1e6:.1f} MB  ({100*(1-ta/tb):.0f}% smaller)")

if __name__ == "__main__":
    main()
