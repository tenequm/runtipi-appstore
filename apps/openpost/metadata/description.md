# OpenPost

An open-source social publishing workspace. Write a post once, shape a variant per
channel, schedule it, and see in Activity what actually shipped and what failed.

## Supported channels

X, LinkedIn, Threads, Instagram, Facebook Pages, TikTok, YouTube, Bluesky and
Mastodon - all through their official APIs, no browser automation.

## What you get

- **Composer** with per-channel variants, character and media limits enforced per
  platform, and a live preview of how each post will render.
- **Scheduling** with a calendar view and a queue; failures surface in Activity
  with the provider error instead of failing silently.
- **Media library** with local storage, an optional image editor, and optional
  stock-photo sources (Pexels, Unsplash, Pixabay).
- **Workspaces** with member roles, so client or team accounts stay separated.
- **Analytics** per post and per account, pulled from the provider APIs.

## This app

Runs the `selfhost` edition: a single Go binary with an embedded frontend, SQLite
on disk, and local media storage. No external database or object store.

The published image is **amd64 only** - it will not run on ARM hardware.

## Setup

1. Set **App URL** to the exact public HTTPS URL you will serve OpenPost from,
   before the first start. OAuth callback URLs, the WebAuthn passkey RPID, CORS
   origins and the public media URL are all derived from it. Changing it later
   breaks every provider callback you have already registered.
2. Open the app and create an account - **the first account becomes the instance
   admin**.
3. Turn on **Disable self-service registrations** afterwards if the instance is
   reachable from the public internet.
4. Add your provider OAuth apps under **Settings > Instance > Configuration**.
   Client IDs and secrets live in the UI, not in this app's environment.

Providers need HTTPS and an exact callback URL match, and Meta fetches media for
Threads and Instagram from your public media URL server-side - so a publicly
reachable HTTPS origin is required for those two to work at all.

## Notes

- The JWT secret and token encryption key are generated once at install and
  persisted. **Back up the encryption key**: if it changes, every connected
  account has to be reconnected.
- Telemetry is off by default. The update check is on and contacts the OpenPost
  release endpoint; set `OPENPOST_UPDATE_CHECK_ENABLED=false` in user-config to
  turn it off.
