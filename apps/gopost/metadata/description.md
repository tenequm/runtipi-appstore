# gopost

Publish and schedule posts to many targets through pluggable adapters, pull
what happens around them into one inbox, and collect their analytics over
time. One binary, one SQLite file, one media directory, driven over a REST
API with an OpenAPI document (`/api/v1/openapi.json`). Built for one
operator and their agents; there is no web UI.

## Adapters

- `zernio-x`, `zernio-linkedin`, `zernio-reddit`: publish, analytics and
  inbox through a Zernio API key.
- `hn`: Hacker News, read-only (discover stories, points and comments,
  replies in the inbox).

## Configuration

Every API call carries `Authorization: Bearer <API token>`. The credential
encryption key seals stored adapter credentials and signs media URLs; back
it up with `/data`. Backups: runtipi's app backup tars `/data` (SQLite +
media).
