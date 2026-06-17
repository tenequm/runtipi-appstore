# memegen custom image

The `memegen` app store entry runs a **custom-built** image, because upstream
[`jacebrowning/memegen`](https://github.com/jacebrowning/memegen) publishes no
public image (only a private Docker Hub on release).

This directory holds everything needed to build and extend that image. The
GitHub Actions workflow [`.github/workflows/build-memegen.yml`](../../.github/workflows/build-memegen.yml)
builds it and pushes a linux/amd64 image to:

```
ghcr.io/tenequm/runtipi-appstore/memegen:<VERSION>
```

## How the build works

1. Check out our app store repo.
2. Check out `jacebrowning/memegen` at the pinned `MEMEGEN_REF` commit.
3. Copy `extra-templates/*` into memegen's own `templates/` directory.
4. Build with memegen's `Containerfile` (BuildKit) for linux/amd64.
5. Push `:<VERSION>` and `:latest` to GHCR.

So the final image contains **all ~200 upstream templates + every folder in
`extra-templates/`** as first-class built-in templates. Custom backgrounds
(`?background=<url>`) work out of the box with no template registration at all.

### Versioning

- `VERSION` and `MEMEGEN_REF` are set in the workflow `env:` block.
- The app's `apps/memegen/docker-compose.yml` pins the image to the same
  `VERSION`. Bump both together on a release (and bump `tipi_version` +
  `updated_at` in `apps/memegen/config.json`).

## Package visibility

The package is **public** (it inherited this repo's visibility), so any Runtipi
host can pull `ghcr.io/tenequm/runtipi-appstore/memegen` with no auth.

If a future package ever comes up **private** instead, flip it once:
GitHub -> your profile/org -> **Packages** -> `memegen` -> **Package settings**
-> **Change visibility** -> **Public**. (GHCR packages pushed by
`GITHUB_TOKEN` can't be flipped to public from the workflow itself.)

## Adding / editing templates

A memegen template is just a folder:

```
extra-templates/<id>/
    config.yml        # text-box geometry + metadata
    default.png       # blank background (png/jpg/gif/webp)
```

`config.yml` text-box fields (all coordinates are **fractions** of the image,
0.0-1.0):

```yaml
name: My Template
source: https://example.com/where-it-came-from
keywords:
  -
text:
  - style: upper        # upper | lower | none | mock (spongebob-case)
    color: white
    font: thick         # thick | thin | comic | impact | notosans | segoe | titilliumweb
    anchor_x: 0.0       # top-left corner of the text box (x)
    anchor_y: 0.0       # top-left corner of the text box (y)
    angle: 0.0
    scale_x: 1.0        # box width  as a fraction of image width
    scale_y: 0.2        # box height as a fraction of image height
    align: center       # left | center | right
    start: 0.0          # animation start (gif/webp), fraction of duration
    stop: 1.0
  - style: upper        # second caption (e.g. bottom)
    color: white
    font: thick
    anchor_x: 0.0
    anchor_y: 0.8
    scale_x: 1.0
    scale_y: 0.2
    align: center
example:
  - top text
  - bottom text
```

After adding a folder, run the appstore tests and rebuild the image
(push to `main` or trigger the workflow manually).

### Bulk-sync trending templates from Imgflip

[`scripts/sync-imgflip-templates.py`](scripts/sync-imgflip-templates.py) pulls
Imgflip's top-100 templates, **skips any already shipped by upstream memegen**,
downloads each blank background, and generates a `config.yml` whose geometry is
derived from the template's text-box count (captions stacked top -> bottom).

```bash
# needs a local checkout of jacebrowning/memegen for deduping
python3 scripts/sync-imgflip-templates.py --memegen-dir /path/to/jacebrowning/memegen

# preview without downloading
python3 scripts/sync-imgflip-templates.py --memegen-dir ... --dry-run

# (re)generate only specific slugs
python3 scripts/sync-imgflip-templates.py --memegen-dir ... --only bell-curve,gus-fring-we-are-not-the-same
```

The generated geometry is a **sane default, not pixel-perfect** - multi-panel
formats (Drake-style, bell curve, Gru's plan) often want hand-tuned `anchor_y` /
`scale_y`. Render the template once (`/images/<id>/preview.jpg`) and nudge the
fractions until the captions sit right. For better multi-panel geometry without
hand-tuning, use the VLM script below instead.

### VLM markup (better multi-panel geometry)

[`scripts/vlm-markup-templates.py`](scripts/vlm-markup-templates.py) does what
the box-count heuristic can't: it shows each blank image to a vision LLM
(Gemini Flash via OpenRouter) and gets back actual caption regions - so Drake's
two captions land on the right half, Two Buttons' labels land on the buttons,
Distracted Boyfriend's three labels land on the three people. It also picks
text color (black vs white) per region and writes good name/keywords/examples.

```bash
export OPENROUTER_API_KEY=...    # already in the maintainer's env

# top ~100 ranked templates from imgflip (each with a box_count hint):
python3 scripts/vlm-markup-templates.py --source imgflip --limit 500

# any folder of blank images (filename -> template name):
python3 scripts/vlm-markup-templates.py --source dir --input-dir /path/to/blanks

# an explicit 500-template catalog you sourced elsewhere (e.g. justmeme):
#   manifest.json = [{"name":"...","url":"https://.../x.jpg","box_count":2}, ...]
python3 scripts/vlm-markup-templates.py --source manifest --manifest manifest.json --limit 500

# preview a few to a scratch dir without touching extra-templates:
python3 scripts/vlm-markup-templates.py --source imgflip --limit 5 --output-dir /tmp/vlm-out
```

Notes:
- Default model `google/gemini-3.5-flash` - tops the 2026-05 Roboflow Vision
  Evals for spatial reasoning and was visibly tighter than the lite models on
  3+ panel layouts (Drake, Left Exit 12, UNO) in testing. Swap with `--model`
  (e.g. `google/gemini-3.1-flash-lite` to trade some multi-panel accuracy for
  ~10x lower cost, or `qwen/qwen3-vl-235b-a22b-instruct`). Don't confuse with
  Nano Banana / `gemini-3-pro-image` - those generate images, not coordinates.
  Coordinates use the `[ymin, xmin, ymax, xmax]` 0-1000 convention internally.
- `--reasoning-effort low` (default) caps the thinking budget. 3.5-flash thinks
  at `medium` by default; this task is simple, so `low` matched `medium` quality
  in testing while cutting ~36% of the cost (~$0.0068 vs $0.0107/template). Use
  `minimal` to push cheaper, `high` only for unusually tricky layouts.
- It's **one-shot** markup (no render-verify loop), good for ~90% of templates;
  a few oddball layouts (diagonal text, speech bubbles, >4 panels) still want a
  manual nudge. Re-run with `--overwrite` to redo a template.
- **`--source imgflip` caps at imgflip's ranked top-100.** To reach 500 you must
  feed a `--source dir` folder or a `--source manifest` catalog of blanks - no
  single API hands out a ranked "top 500".

## Template images, licensing, and takedown requests

The code, build scripts, and template `config.yml` markup in this repository are
MIT-licensed (see the repository root `LICENSE`). That MIT license does **not**
extend to the template background images.

The images under `extra-templates/` are well-known internet meme formats whose
underlying photos, film stills, and artwork are owned by their respective
copyright holders. They are included in good faith for the same
nominative/transformative use that meme-generation tools rely on (the same legal
posture as anyone running memegen.link or the upstream image), and **no claim of
ownership is made over them**. Shipping them in a public image is a deliberate
choice for this personal app store.

If you are a rights holder and want a template image removed, email
**misha@kolesnik.io** with the template name (its folder under
`extra-templates/`) and proof of rights. Removal requests are honored promptly -
typically within a few days.

For zero redistribution exposure, drop `extra-templates/` and rely on the
`?background=<url>` custom-background endpoint instead.
