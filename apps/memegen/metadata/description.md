# Memegen

A self-hosted instance of [memegen](https://github.com/jacebrowning/memegen): a fast, stateless meme generator where **the URL is the meme**. No database, no Redis, no accounts - everything is encoded in the request, and rendered images are cached to a local volume.

## Features

- **200+ built-in templates** baked into the image (Drake, Distracted Boyfriend, Two Buttons, Gru's Plan, Bernie, Expanding Brain, and more).
- **Extra trending formats** added on top of the upstream set.
- **Custom backgrounds** - caption *any* image on the web without registering a template:
  ```
  /images/custom/top_line/bottom_line.png?background=https://example.com/any-image.png
  ```
- **URL-driven API** - generate memes programmatically. Browse the interactive API at `/docs` and list every template at `/templates`.
- **Animated output** - GIF and WebP supported for animated templates.
- Built from source (linux/amd64).

## Usage

Open the app and visit `/docs` for the full interactive API. Basic patterns:

- Built-in template: `/images/drake/left_on_unread/left_on_read.png`
- Custom background: `/images/custom/_/it_works.png?background=https://example.com/pic.png`
- List templates: `/templates`

Use `_` for an empty line and `~q`/`~p` style escapes for special characters (see `/docs`).

## Exposing on a public domain

By default this app runs in local mode, so meme image bytes are served correctly through Runtipi's reverse proxy, but the **absolute URLs returned in JSON API responses** point at `localhost:5000`. If you expose Memegen on a public domain and want the API responses to return correct external URLs, set the `DOMAIN` environment variable to your exposed hostname.

Do this with a Runtipi user-config override (do **not** edit the app folder directly, it is overwritten on update):

```
runtipi/user-config/<your-app-store>/memegen/docker-compose.yml
```

```yaml
services:
  memegen:
    environment:
      - DOMAIN=memes.yourdomain.com
```

Note: setting `DOMAIN` enables "deployed" mode, which also stamps a `Memegen.link` watermark on full-size images (upstream attribution behavior). Leave `DOMAIN` unset for watermark-free local rendering.

## Adding your own templates

Templates are baked into the image at build time (each is a folder with a `config.yml` + a background image). To add more without rebuilding, you can also just use the **custom background** endpoint above - it gives you effectively unlimited templates by pointing at any image URL.

## Credits

memegen is created and maintained by [Jace Browning](https://github.com/jacebrowning/memegen) (MIT licensed).

> Bundled meme template images are third-party works included under fair/nominative use; the project claims no ownership. Rights holders: email misha@kolesnik.io for removal.
