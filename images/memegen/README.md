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
fractions until the captions sit right.

## Licensing note

memegen's code is MIT. The template **images** (Drake, film/TV stills, etc.) are
copyrighted by their owners - the same legal posture as anyone running
memegen.link or the upstream image. Shipping them in a public image is a
deliberate choice for this personal app store. For zero redistribution exposure,
drop `extra-templates/` and rely on the `?background=<url>` custom-background
endpoint instead.
