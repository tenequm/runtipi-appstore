# AGENTS.md - tenequm/runtipi-appstore

Custom Runtipi app store. Apps live in `apps/<id>/`. This repo is the source for the
`tenequm` app store. Pushing to GitHub validates via CI; it does NOT deploy - deploying to a
running Runtipi instance is a separate step done by the owner outside this repo.

Human contributor guide is `CONTRIBUTING.md` (categories list, file templates). This file
is the agent guide and the gotchas that aren't obvious.

## Before EVERY push: `bun test` (non-negotiable)

CI (`.github/workflows/test.yml`) runs `bun test` on every push to `main` and on PRs. It
validates every app against the official `@runtipi/common` schemas. Run it locally first:

    bun install && bun test        # or: bun run test

Pushing without running it is how you land red on `main`. No exceptions.

## Adding / updating an app - required files and rules

Each `apps/<id>/` MUST have: `config.json`, `docker-compose.yml`, `metadata/logo.jpg`
(square JPEG), `metadata/description.md`. No legacy `docker-compose.json`.

`config.json` (schema: `apps/app-info-schema.json`, validated by `appInfoSchema`):
- `id` == folder name. Semantic `version`. `categories` from the allowed set in CONTRIBUTING.md.
- `supported_architectures`: list what the IMAGE actually supports - do NOT blindly put
  `["arm64","amd64"]`. Many images are amd64-only.
- `created_at` / `updated_at`: epoch ms that MUST be in the PAST relative to the Runtipi
  host's clock. CI only checks `> 0`, but a live Runtipi rejects future values at index time
  (`created_at must be a timestamp before now`). Never hardcode a future ms; copy a
  known-past value from an existing app or use `scripts/update-config.ts`.
- `exposable`: `false` for anything holding live sessions/secrets (keeps it off the public
  domain - private network only). `true` only for things safe to publish.
- `form_fields`: one per env var; types `password`, `text`, `boolean` (booleans take `default`).

`docker-compose.yml` (schema: `apps/dynamic-compose-schema.json`, validated by
`dynamicComposeSchemaYaml`):
- Top-level `x-runtipi: { schema_version: 2 }`.
- EXACTLY ONE service with `x-runtipi.is_main: true`, and it MUST set `x-runtipi.internal_port`.
- Verified-allowed keys beyond the basics: `shm_size`, `mem_limit`, `command` (list; a
  multiline `|` literal as the last arg is fine), `network_mode`, `depends_on`, `cap_add`,
  `devices`, `group_add`, `volumes`, `environment`. Secondary services (no `is_main`) are fine.
- IMAGES: must match `name:tag`, never `:latest`, and **never digest-pin**. `@sha256:...`
  FAILS the CI image regex - this repo is TAG-ONLY. Do not reintroduce digests here.
- **NEVER use a one-shot / init sidecar container.** Runtipi's status reconciler counts
  running containers every 5 min and writes `status = stopped` on any partial count
  (`warn > App <urn> has mixed container states: 2/3 running`). A container that exits 0 by
  design trips this permanently. The app keeps serving, so it looks cosmetic - but a
  `stopped` app **does not auto-start after a reboot**, and patching the DB row back to
  `running` does not stick (the reconciler overwrites it on the next cycle). Every service
  in the compose must be long-running. Fold init work into the real service's `entrypoint`
  instead (`entrypoint` and `user` are schema-allowed):

      entrypoint: ["/bin/sh", "-c", "chmod 700 /data/db 2>/dev/null || true; exec /app/entrypoint.sh"]

  Both `dispatcharr` and `onecli` use this to fix data-dir perms (Runtipi creates app-data
  dirs 0777; postgres and others refuse to start on a world-readable dir).

Updating an existing app's version:

    bun ./scripts/update-config.ts apps/<id>/docker-compose.yml <newVersion>

bumps `tipi_version` (+1), `version`, and `updated_at`. Then bump the image tag in
`docker-compose.yml`, then `bun test`. Runtipi offers an update only when `tipi_version`
grows - an image-tag change alone shows no Update button.

## Releasing

`bun test` green -> commit + push `main` -> confirm CI green (`gh run watch <id>`). That is
the whole release from this repo's side.

## Pointers

- Schemas: `apps/app-info-schema.json`, `apps/dynamic-compose-schema.json`.
- Sanctioned commands (`config.js`): `bun ./scripts/update-config.ts`, `bun install && bun run test`.
