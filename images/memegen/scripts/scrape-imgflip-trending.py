#!/usr/bin/env python3
"""
Scrape imgflip's ranked template browser for the top-N trending templates we
DON'T already have (not upstream memegen, not in extra-templates), download the
highest-resolution blank imgflip offers for each, and stage them + a manifest
for later markup (vlm-markup-templates.py --source dir/manifest).

Why imgflip's HTML listing (not the API): the get_memes API caps at 100. The
listing at imgflip.com/memetemplates?sort=... is server-rendered HTML, ranked by
real usage, and ~40 templates/page deep (~2,180 for top-30-days). We read the
native image (i.imgflip.com/<id>.jpg) - NOT the /4/<id>.jpg listing thumbnail,
which is only 250px.

Quality note: imgflip's native blank is the ceiling it offers; for legacy
classics that ceiling can be small (e.g. 300x300). Each staged image records its
real width/height and a `lowres` flag (long side < --lowres-threshold) so the
processing step can upscale or re-source those without re-checking every file.

Usage:
    python3 scrape-imgflip-trending.py --memegen-dir /path/to/jacebrowning/memegen
    python3 scrape-imgflip-trending.py --memegen-dir ... --target 500 --sort top-30-days
    python3 scrape-imgflip-trending.py --memegen-dir ... --sort top-all-time
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parent / "staging" / "trending"
DEFAULT_EXTRA = HERE.parent / "extra-templates"
LISTING = "https://imgflip.com/memetemplates?sort={sort}&page={page}"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# One template tile: <h3 class="mt-title">...<a ... href="/meme/SLUG">NAME</a> ...
# <img ... alt="NAME Meme Template" src="//i.imgflip.com/4/<id>.jpg">
TILE_RE = re.compile(
    r'<h3 class="mt-title">\s*<a title="[^"]*" href="(?P<href>/meme/[^"]+)">(?P<name>[^<]+)</a>.*?'
    r'src="//i\.imgflip\.com/4/(?P<id>[a-z0-9]+)\.(?P<ext>jpg|png)"',
    re.S,
)


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def slugify(name: str) -> str:
    s = name.lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s) or "template"


def http_get(url: str, *, binary=False, timeout=30, retries=3):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read() if binary else r.read().decode("utf-8", "replace")
        except Exception as e:  # noqa: BLE001
            last = e
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET {url} failed: {last}")


def dims(path: Path) -> tuple[int, int]:
    try:
        out = subprocess.check_output(["magick", "identify", "-format", "%w %h", str(path)],
                                      stderr=subprocess.DEVNULL).decode()
        w, h = out.split()[:2]
        return int(w), int(h)
    except Exception:  # noqa: BLE001
        return 0, 0


def load_dedupe(memegen_dir: Path, extra_dir: Path) -> tuple[set[str], set[str]]:
    names, slugs = set(), set()
    for base in (memegen_dir / "templates", extra_dir):
        if not base or not base.is_dir():
            continue
        for d in base.iterdir():
            if not d.is_dir():
                continue
            slugs.add(d.name)
            cfg = d / "config.yml"
            if cfg.exists():
                m = re.search(r"^name:\s*(.+)$", cfg.read_text(), re.MULTILINE)
                if m:
                    names.add(normalize(m.group(1).strip().strip('"')))
    return names, slugs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--memegen-dir", required=True, type=Path, help="jacebrowning/memegen checkout (dedupe)")
    ap.add_argument("--extra-dir", type=Path, default=DEFAULT_EXTRA, help="our extra-templates (dedupe)")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--sort", default="top-30-days", help="top-30-days | top-all-time | top-new | newest")
    ap.add_argument("--target", type=int, default=500, help="how many NEW templates to collect")
    ap.add_argument("--max-pages", type=int, default=80)
    ap.add_argument("--lowres-threshold", type=int, default=800, help="long side below this => lowres flag")
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    up_names, up_slugs = load_dedupe(args.memegen_dir, args.extra_dir)
    print(f"dedupe set: {len(up_slugs)} existing templates ({len(up_names)} names)")

    candidates: list[dict] = []
    seen_ids: set[str] = set()
    raw = dups = 0
    for page in range(1, args.max_pages + 1):
        doc = http_get(LISTING.format(sort=args.sort, page=page))
        tiles = list(TILE_RE.finditer(doc))
        if not tiles:
            print(f"page {page}: no tiles, stopping")
            break
        for m in tiles:
            raw += 1
            name = html.unescape(m.group("name").strip())
            tid = m.group("id")
            if tid in seen_ids:
                continue
            seen_ids.add(tid)
            slug = slugify(name)
            if slug in up_slugs or normalize(name) in up_names:
                dups += 1
                continue
            candidates.append({
                "name": name,
                "id": tid,
                "slug": slug,
                "source": "https://imgflip.com" + m.group("href"),
            })
        print(f"page {page}: {len(tiles)} tiles, {len(candidates)} new so far ({dups} dups skipped)")
        if len(candidates) >= args.target:
            break
        time.sleep(0.5)

    candidates = candidates[: args.target]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    def fetch(c: dict) -> dict | None:
        # The listing only exposes the /4/<id>.jpg thumbnail; the native blank
        # may be png, jpg, or gif. Probe in quality order (png is usually the
        # lossless original and highest-res) and keep the first that exists.
        data = ext = None
        for e in ("png", "jpg", "gif"):
            try:
                data = http_get(f"https://i.imgflip.com/{c['id']}.{e}", binary=True, retries=1)
                ext = e
                break
            except Exception:  # noqa: BLE001 - 404 for the wrong extension
                continue
        if data is None:
            print(f"  FAIL {c['slug']}: no native image found")
            return None
        folder = args.out_dir / c["slug"]
        folder.mkdir(parents=True, exist_ok=True)
        img = folder / f"default.{ext}"
        img.write_bytes(data)
        w, h = dims(img)
        c.update(url=f"https://i.imgflip.com/{c['id']}.{ext}", ext=ext,
                 width=w, height=h, lowres=(max(w, h) < args.lowres_threshold), file=img.name)
        return c

    done = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for r in pool.map(fetch, candidates):
            if r:
                done.append(r)

    (args.out_dir / "manifest.json").write_text(json.dumps(done, indent=2))

    lowres = [c for c in done if c["lowres"]]
    tiny = [c for c in done if max(c["width"], c["height"]) < 600]
    print(f"\ncollected {len(done)} new templates -> {args.out_dir}")
    print(f"  raw seen {raw}, dups skipped {dups}")
    print(f"  resolution: {len(lowres)} lowres (<{args.lowres_threshold}px), {len(tiny)} tiny (<600px), "
          f"{len(done) - len(lowres)} ok")
    print(f"  manifest: {args.out_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
