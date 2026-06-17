#!/usr/bin/env python3
"""
Sync trending meme templates from Imgflip into memegen-compatible template folders.

For each of Imgflip's top-100 templates (https://api.imgflip.com/get_memes) that is
NOT already shipped by upstream memegen, this writes a folder under extra-templates/:

    extra-templates/<id>/
        config.yml      generated text-box geometry (from box_count)
        default.<ext>   the blank background image downloaded from Imgflip

These folders are copied into memegen's own templates/ directory at image-build
time (see ../../.github/workflows/build-memegen.yml), so they become first-class
built-in templates alongside the ~200 upstream ones.

Geometry is GENERATED from box_count using the classic stacked-caption convention
(see band_layout). It is a sane default, not pixel-perfect - fine-tune any template
by editing its config.yml (anchor_x/anchor_y/scale_x/scale_y are fractions of the
image size). See ../README.md.

Usage:
    python3 sync-imgflip-templates.py --memegen-dir /path/to/jacebrowning/memegen
    python3 sync-imgflip-templates.py --memegen-dir ... --only drake,two-buttons
    python3 sync-imgflip-templates.py --memegen-dir ... --dry-run

--memegen-dir must point at a checkout of jacebrowning/memegen; its templates/
directory is read only to dedupe (we never want to re-ship an upstream template).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

GET_MEMES = "https://api.imgflip.com/get_memes"
HERE = Path(__file__).resolve().parent
EXTRA_DIR = HERE.parent / "extra-templates"


def normalize(name: str) -> str:
    """Lowercase, alphanumeric-only - used for fuzzy dedupe against upstream names."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def slugify(name: str) -> str:
    """memegen-style id: lowercase, hyphen-separated, alphanumeric."""
    # Drop apostrophes first so "I'm"/"that's" -> "im"/"thats", not "-m-"/"-s-".
    s = name.lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s)


def band_layout(box_count: int) -> list[dict]:
    """Generate `box_count` caption boxes stacked top->bottom across the image.

    box_count==1 -> single bottom caption (classic single-line macro).
    box_count>=2 -> boxes evenly distributed from the top (y=0.0) to the
    bottom band (y=0.8), each occupying a 20%-tall band.
    """
    n = max(1, box_count)
    if n == 1:
        anchors = [0.8]
    else:
        anchors = [round(i * (0.8 / (n - 1)), 3) for i in range(n)]
    return [
        {
            "style": "upper",
            "color": "white",
            "font": "thick",
            "anchor_x": 0.0,
            "anchor_y": y,
            "angle": 0.0,
            "scale_x": 1.0,
            "scale_y": 0.2,
            "align": "center",
            "start": 0.0,
            "stop": 1.0,
        }
        for y in anchors
    ]


def to_yaml(template: dict) -> str:
    """Render a memegen config.yml. Hand-rolled to avoid a PyYAML dependency."""
    lines: list[str] = []
    lines.append(f"name: {yaml_scalar(template['name'])}")
    lines.append(f"source: {template['source']}")
    lines.append("keywords:")
    lines.append("  -")
    lines.append("text:")
    for box in template["text"]:
        first = True
        for key, val in box.items():
            prefix = "  - " if first else "    "
            lines.append(f"{prefix}{key}: {yaml_scalar(val)}")
            first = False
    lines.append("example:")
    for ex in template["example"]:
        lines.append(f"  - {yaml_scalar(ex)}")
    return "\n".join(lines) + "\n"


def yaml_scalar(val) -> str:
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val)
    if s == "":
        return '""'
    if re.search(r'[:#\[\]{}&*!|>"%@`,]|^\s|\s$', s):
        return json.dumps(s)
    return s


def load_upstream(memegen_dir: Path) -> tuple[set[str], set[str]]:
    tdir = memegen_dir / "templates"
    if not tdir.is_dir():
        sys.exit(f"error: {tdir} not found (pass a valid --memegen-dir)")
    ids: set[str] = set()
    names: set[str] = set()
    for d in sorted(tdir.iterdir()):
        if not d.is_dir():
            continue
        ids.add(d.name)
        cfg = d / "config.yml"
        if cfg.exists():
            m = re.search(r"^name:\s*(.+)$", cfg.read_text(), re.MULTILINE)
            if m:
                names.add(normalize(m.group(1).strip().strip('"')))
    return ids, names


def fetch_memes() -> list[dict]:
    req = urllib.request.Request(GET_MEMES, headers={"User-Agent": "runtipi-appstore/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if not data.get("success"):
        sys.exit(f"imgflip error: {data}")
    return data["data"]["memes"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--memegen-dir", required=True, type=Path, help="Path to a jacebrowning/memegen checkout (for dedupe)")
    ap.add_argument("--only", help="Comma-separated slugs to (re)generate; others skipped")
    ap.add_argument("--dry-run", action="store_true", help="List what would be written, fetch nothing")
    args = ap.parse_args()

    only = {s.strip() for s in args.only.split(",")} if args.only else None
    up_ids, up_names = load_upstream(args.memegen_dir)
    memes = fetch_memes()

    EXTRA_DIR.mkdir(parents=True, exist_ok=True)
    written, skipped_dupe, skipped_only = 0, 0, 0

    for meme in memes:
        name = meme["name"]
        slug = slugify(name)
        if only is not None and slug not in only:
            skipped_only += 1
            continue
        if slug in up_ids or normalize(name) in up_names:
            skipped_dupe += 1
            print(f"  dup  {slug:40s} (already upstream)")
            continue

        url = meme["url"]
        ext = Path(urllib.parse.urlparse(url).path).suffix.lstrip(".") or "jpg"
        if ext not in {"jpg", "jpeg", "png", "gif", "webp"}:
            ext = "jpg"

        folder = EXTRA_DIR / slug
        cfg = {
            "name": name,
            "source": f"https://imgflip.com/memetemplate/{meme['id']}",
            "text": band_layout(int(meme.get("box_count", 2))),
            "example": example_lines(int(meme.get("box_count", 2))),
        }

        if args.dry_run:
            print(f"  new  {slug:40s} boxes={meme.get('box_count')} ext={ext}")
            written += 1
            continue

        folder.mkdir(parents=True, exist_ok=True)
        (folder / "config.yml").write_text(to_yaml(cfg))
        img = folder / f"default.{ext}"
        req = urllib.request.Request(url, headers={"User-Agent": "runtipi-appstore/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            img.write_bytes(resp.read())
        print(f"  new  {slug:40s} boxes={meme.get('box_count')} -> {img.name}")
        written += 1

    print(f"\n{written} written, {skipped_dupe} skipped (upstream dup)"
          + (f", {skipped_only} skipped (--only filter)" if only else ""))


def example_lines(box_count: int) -> list[str]:
    pool = ["top text", "bottom text", "third line", "fourth line", "fifth line"]
    return pool[: max(1, box_count)]


if __name__ == "__main__":
    main()
