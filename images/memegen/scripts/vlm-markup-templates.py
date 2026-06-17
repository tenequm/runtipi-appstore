#!/usr/bin/env python3
"""
VLM-author memegen templates: look at each blank template image with a
vision LLM (via OpenRouter) and generate config.yml caption geometry.

Why a VLM: memegen config.yml is mostly text-box positions (anchor_x/y,
scale_x/y as FRACTIONS of image size). The naive box_count heuristic
(sync-imgflip-templates.py) only nails simple top/bottom macros; multi-panel
formats (Drake, Two Buttons, bell curve, Gru's plan) need a model that can
actually look at the image and place boxes. Gemini Flash has a native
0-1000 bounding-box capability that's cheap and resize-robust - ideal for the
easy-mode grounding this task needs (a few big regions on a near-blank canvas).

Coordinate convention: boxes are [ymin, xmin, ymax, xmax] normalized 0-1000
(Y FIRST) - the format Gemini's object-detection training emits.

Model: default google/gemini-3.1-flash-lite. This task is simple (2-4 big
regions on a near-blank canvas), and flash-lite matches the pricier 3.5-flash on
both box position and text-color choice here, at ~15x lower cost (~$0.0007 per
template, ~$0.35 for 500). Swap with --model: google/gemini-3.5-flash for the
hardest layouts (it tops the 2026-05 Roboflow Vision Evals for spatial
reasoning), or qwen/qwen3-vl-235b-a22b-instruct. Not to be confused with Nano
Banana / gemini-3-pro-image, which GENERATE images rather than return coordinates.

Output: writes <output-dir>/<slug>/{config.yml, default.<ext>} - the same
folder shape the build copies into memegen's templates/. Defaults to
extra-templates/, skips existing folders unless --overwrite.

NOTE: this is ONE-SHOT markup (fast, good enough for ~90% of templates).
A handful of oddball layouts (diagonal text, speech bubbles, >4 panels) will
still want a manual nudge - render /images/<slug>/preview.jpg and tweak.

Usage:
    export OPENROUTER_API_KEY=...   # already in your env
    # top ~100 ranked templates from imgflip (includes box_count hints):
    python3 vlm-markup-templates.py --source imgflip --limit 500

    # any folder of blank images (filename -> template name):
    python3 vlm-markup-templates.py --source dir --input-dir /path/to/blanks

    # an explicit catalog (e.g. 500 scraped from justmeme):
    #   manifest.json = [{"name": "...", "url": "https://.../x.jpg", "box_count": 2}, ...]
    python3 vlm-markup-templates.py --source manifest --manifest manifest.json --limit 500

    # try a few first, write to a scratch dir, don't touch extra-templates:
    python3 vlm-markup-templates.py --source imgflip --limit 5 --output-dir /tmp/vlm-out
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

# Thread-safe running totals (OpenRouter reports per-call cost in-band).
_TOTALS = {"cost": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "cost_known": 0}
_TOTALS_LOCK = threading.Lock()

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
GET_MEMES = "https://api.imgflip.com/get_memes"
HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE.parent / "extra-templates"
UA = {"User-Agent": "runtipi-appstore/1.0"}

SYSTEM_PROMPT = (
    "You are a meme-template layout expert. Given a BLANK meme template image, "
    "you identify exactly where a meme creator's caption text should be placed, "
    "and you reply with strict JSON only."
)

USER_PROMPT = """This is a blank meme template named "{name}".{hint}

Identify the caption regions - the areas where a meme creator types text (the
blank/solid-color bands, the labelled panels, speech areas, or the conventional
top and bottom). Return one bounding box per caption region.

Reply with ONLY this JSON object (no prose, no markdown fences):
{{
  "name": "<clean human-readable title>",
  "keywords": ["<lowercase tag>", "..."],
  "boxes": [
    {{
      "box_2d": [ymin, xmin, ymax, xmax],
      "color": "white",
      "align": "center",
      "example": "<short example caption for this box>"
    }}
  ]
}}

Rules:
- box_2d are INTEGERS 0-1000 as fractions of image size, order [ymin, xmin, ymax, xmax] (Y FIRST).
- Order boxes top-to-bottom, then left-to-right.
- Only include regions where a caption truly goes - do NOT invent regions. Most macros have 1-4.
- Prefer wide boxes covering the natural text area; memegen auto-wraps and auto-scales text,
  so the region only needs to be correct, not pixel-tight.
- "color": choose "black" for light/white backgrounds, "white" for dark or photographic backgrounds.
- "align": "left" | "center" | "right".
"""


# ----- helpers ------------------------------------------------------------

def slugify(name: str) -> str:
    # Drop apostrophes first so "I'm"/"that's" -> "im"/"thats", not "-m-"/"-s-".
    s = name.lower().replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s) or "template"


def normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


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


def to_yaml(name: str, source: str, keywords: list[str], boxes: list[dict], examples: list[str]) -> str:
    lines = [f"name: {yaml_scalar(name)}", f"source: {source}", "keywords:"]
    if keywords:
        lines += [f"  - {yaml_scalar(k)}" for k in keywords]
    else:
        lines.append("  -")
    lines.append("text:")
    for box in boxes:
        first = True
        for key, val in box.items():
            prefix = "  - " if first else "    "
            lines.append(f"{prefix}{key}: {yaml_scalar(val)}")
            first = False
    lines.append("example:")
    for ex in (examples or ["top text", "bottom text"]):
        lines.append(f"  - {yaml_scalar(ex)}")
    return "\n".join(lines) + "\n"


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def box_to_text(box: dict) -> tuple[dict, str]:
    """Convert a VLM box_2d (0-1000, [ymin,xmin,ymax,xmax]) to a memegen text box."""
    ymin, xmin, ymax, xmax = (float(v) for v in box["box_2d"])
    ax, ay = clamp01(xmin / 1000), clamp01(ymin / 1000)
    sx = clamp01((xmax - xmin) / 1000) or 1.0
    sy = clamp01((ymax - ymin) / 1000) or 0.2
    color = box.get("color", "white")
    if color not in ("white", "black"):
        color = "white"
    align = box.get("align", "center")
    if align not in ("left", "center", "right"):
        align = "center"
    text = {
        "style": "upper",
        "color": color,
        "font": "thick",
        "anchor_x": round(ax, 3),
        "anchor_y": round(ay, 3),
        "angle": 0.0,
        "scale_x": round(sx, 3),
        "scale_y": round(sy, 3),
        "align": align,
        "start": 0.0,
        "stop": 1.0,
    }
    return text, str(box.get("example", "")).strip()


def http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def extract_video_frame(path: Path) -> bytes:
    """Grab a representative (~midpoint) frame from an MP4 as JPEG bytes, to show
    the VLM (it marks up caption geometry, which is the same across the clip).
    Needs ffmpeg/ffprobe on PATH."""
    dur = 0.0
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            stderr=subprocess.DEVNULL).decode().strip()
        dur = float(out)
    except Exception:  # noqa: BLE001
        dur = 0.0
    ts = max(0.0, dur * 0.5)
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{ts:.3f}", "-i", str(path),
         "-frames:v", "1", "-f", "image2", "-c:v", "mjpeg", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if proc.returncode != 0 or not proc.stdout:  # seek past end on tiny clips -> first frame
        proc = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(path), "-frames:v", "1",
             "-f", "image2", "-c:v", "mjpeg", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if not proc.stdout:
        raise RuntimeError(f"ffmpeg could not extract a frame from {path}")
    return proc.stdout


def call_openrouter(model: str, api_key: str, image_b64: str, mime: str, name: str,
                    box_count: int | None, effort: str, retries: int = 3) -> dict:
    hint = f" It conventionally has {box_count} caption area(s)." if box_count else ""
    payload = {
        "model": model,
        "temperature": 0,
        "usage": {"include": True},
        # Cap thinking: this is simple spatial work, so we don't pay for the
        # model's default (medium) reasoning budget. OpenRouter maps effort ->
        # Gemini thinkingLevel (minimal|low|medium|high).
        "reasoning": {"effort": effort},
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": USER_PROMPT.format(name=name, hint=hint)},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            },
        ],
    }
    body = json.dumps(payload).encode()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/tenequm/runtipi-appstore",
        "X-Title": "runtipi-appstore memegen markup",
    }
    last_err = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(OPENROUTER_URL, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.load(resp)
            usage = data.get("usage") or {}
            with _TOTALS_LOCK:
                _TOTALS["calls"] += 1
                _TOTALS["prompt_tokens"] += usage.get("prompt_tokens", 0)
                _TOTALS["completion_tokens"] += usage.get("completion_tokens", 0)
                if usage.get("cost") is not None:
                    _TOTALS["cost"] += usage["cost"]
                    _TOTALS["cost_known"] += 1
            content = data["choices"][0]["message"]["content"]
            content = re.sub(r"^```(?:json)?|```$", "", content.strip(), flags=re.MULTILINE).strip()
            return json.loads(content)
        except Exception as e:  # noqa: BLE001 - retry any transient/parse error
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"openrouter failed after {retries} tries: {last_err}")


# ----- sources ------------------------------------------------------------

def source_imgflip(limit: int) -> list[dict]:
    data = json.loads(http_get(GET_MEMES))
    if not data.get("success"):
        sys.exit(f"imgflip error: {data}")
    out = []
    for m in data["data"]["memes"][:limit]:
        out.append({
            "name": m["name"],
            "url": m["url"],
            "box_count": int(m.get("box_count", 0)) or None,
            "source": f"https://imgflip.com/memetemplate/{m['id']}",
        })
    return out


def source_manifest(path: Path, limit: int) -> list[dict]:
    items = json.loads(path.read_text())
    out = []
    for m in items[:limit]:
        out.append({
            "name": m["name"],
            "url": m["url"],
            "box_count": (int(m["box_count"]) if m.get("box_count") else None),
            "source": m.get("source", m["url"]),
        })
    return out


def source_staging(staging_dir: Path, limit: int) -> list[dict]:
    """A scrape-imgflip-trending.py staging dir: <slug>/default.* + manifest.json.

    Uses the LOCAL (already optimized / HD-swapped) image bytes and the real
    template name + source URL from the manifest - never re-downloads."""
    manifest = json.loads((staging_dir / "manifest.json").read_text())
    out = []
    for m in manifest[:limit]:
        files = sorted((staging_dir / m["slug"]).glob("default.*"))
        if not files:  # dir pruned or never downloaded
            continue
        out.append({
            "name": m["name"],
            "path": files[0],          # actual on-disk ext (optimize may have png->jpg)
            "box_count": None,
            "source": m.get("source", m.get("url", "")),
        })
    return out


def source_dir(input_dir: Path, limit: int) -> list[dict]:
    exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4"}
    files = sorted(p for p in input_dir.iterdir() if p.suffix.lower() in exts)
    out = []
    for p in files[:limit]:
        out.append({
            "name": p.stem.replace("-", " ").replace("_", " ").title(),
            "path": p,
            "box_count": None,
            "source": f"file://{p.name}",
        })
    return out


# ----- worker -------------------------------------------------------------

def process(item: dict, args, api_key: str, up_ids: set[str], up_names: set[str]) -> str:
    name = item["name"]
    slug = slugify(name)
    if slug in up_ids or normalize(name) in up_names:
        return f"  dup   {slug:40s} (already upstream)"
    folder = args.output_dir / slug
    if folder.exists() and not args.overwrite and (folder / "config.yml").exists():
        return f"  skip  {slug:40s} (exists; --overwrite to redo)"

    # load image bytes (+ ext / mime)
    if "path" in item:
        raw = item["path"].read_bytes()
        ext = item["path"].suffix.lstrip(".").lower()
    else:
        raw = http_get(item["url"])
        ext = (Path(urllib.parse.urlparse(item["url"]).path).suffix.lstrip(".").lower() or "jpg")
    if ext == "jpeg":
        ext = "jpg"

    # MP4 is an animated source memegen reads via PyAV: the VLM can't see video,
    # so we mark up a representative still frame but persist the .mp4 itself.
    is_video = ext == "mp4"
    if is_video:
        frame_jpeg = extract_video_frame(item["path"])
        vlm_b64, vlm_mime = base64.b64encode(frame_jpeg).decode(), "image/jpeg"
    else:
        vlm_b64 = base64.b64encode(raw).decode()
        vlm_mime = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif",
                    "webp": "image/webp"}.get(ext, "image/jpeg")

    result = call_openrouter(args.model, api_key, vlm_b64, vlm_mime, name, item.get("box_count"), args.reasoning_effort)
    raw_boxes = result.get("boxes") or []
    if not raw_boxes:
        raise RuntimeError("model returned no boxes")
    text_boxes, examples = [], []
    for b in raw_boxes:
        if "box_2d" not in b or len(b["box_2d"]) != 4:
            continue
        tb, ex = box_to_text(b)
        text_boxes.append(tb)
        examples.append(ex or "text")
    if not text_boxes:
        raise RuntimeError("no usable boxes after parse")

    if args.dry_run:
        return f"  new   {slug:40s} boxes={len(text_boxes)} (dry-run, not written)"

    folder.mkdir(parents=True, exist_ok=True)
    yml = to_yaml(
        name=result.get("name", name),
        source=item["source"],
        keywords=[str(k).lower() for k in (result.get("keywords") or [])][:8],
        boxes=text_boxes,
        examples=examples,
    )
    (folder / "config.yml").write_text(yml)
    (folder / f"default.{ext}").write_bytes(raw)
    extra = ""
    # keep-both templates: also emit a static still so /<id>/a/b.png works
    if is_video and (args.static_all or slug in args.static_slugs):
        (folder / "default.jpg").write_bytes(frame_jpeg)
        extra = " (+static default.jpg)"
    return f"  new   {slug:40s} boxes={len(text_boxes)} -> default.{ext}{extra}"


def load_upstream(memegen_dir: Path | None) -> tuple[set[str], set[str]]:
    if not memegen_dir:
        return set(), set()
    tdir = memegen_dir / "templates"
    if not tdir.is_dir():
        sys.exit(f"error: {tdir} not found")
    ids, names = set(), set()
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


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["imgflip", "manifest", "dir", "staging"], default="imgflip")
    ap.add_argument("--input-dir", type=Path, help="blank images dir (--source dir) "
                    "or a scrape staging dir with manifest.json (--source staging)")
    ap.add_argument("--manifest", type=Path, help="catalog JSON (--source manifest)")
    ap.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--model", default="google/gemini-3.5-flash")
    ap.add_argument("--reasoning-effort", default="low", choices=["minimal", "low", "medium", "high"],
                    help="thinking level (OpenRouter effort -> Gemini thinkingLevel); low is plenty "
                         "for this simple task and avoids the 'medium' default's thinking-token cost")
    ap.add_argument("--limit", type=int, default=500)
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--memegen-dir", type=Path, help="dedupe against an upstream memegen checkout")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="call the model but don't write files")
    ap.add_argument("--static-slugs", default="",
                    help="comma-separated slugs (or 'all') that also get a static default.jpg "
                         "still extracted from the mp4 (keep-both templates)")
    args = ap.parse_args()
    args.static_all = args.static_slugs.strip().lower() == "all"
    args.static_slugs = set() if args.static_all else {
        s.strip() for s in args.static_slugs.split(",") if s.strip()}

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        sys.exit("error: OPENROUTER_API_KEY not set")

    if args.source == "imgflip":
        items = source_imgflip(args.limit)
    elif args.source == "manifest":
        if not args.manifest:
            sys.exit("--source manifest needs --manifest")
        items = source_manifest(args.manifest, args.limit)
    elif args.source == "staging":
        if not args.input_dir:
            sys.exit("--source staging needs --input-dir (the scrape staging dir)")
        items = source_staging(args.input_dir, args.limit)
    else:
        if not args.input_dir:
            sys.exit("--source dir needs --input-dir")
        items = source_dir(args.input_dir, args.limit)

    up_ids, up_names = load_upstream(args.memegen_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"model={args.model}  source={args.source}  items={len(items)}  concurrency={args.concurrency}")

    ok = fail = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futs = {pool.submit(process, it, args, api_key, up_ids, up_names): it for it in items}
        for fut in concurrent.futures.as_completed(futs):
            it = futs[fut]
            try:
                print(fut.result())
                ok += 1
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"  FAIL  {slugify(it['name']):40s} {e}")

    print(f"\ndone: {ok} ok, {fail} failed -> {args.output_dir}")
    t = _TOTALS
    print(f"cost: ${t['cost']:.4f} over {t['calls']} api call(s) "
          f"({t['prompt_tokens']:,} in + {t['completion_tokens']:,} out tokens)"
          + ("" if t["cost_known"] == t["calls"] else f"; cost reported for {t['cost_known']}/{t['calls']}"))


if __name__ == "__main__":
    main()
