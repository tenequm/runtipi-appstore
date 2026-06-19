# CloakBrowser Manager

Self-hosted **stealth-browser profile manager** - a free alternative to Multilogin / GoLogin / AdsPower, powered by [CloakBrowser](https://github.com/CloakHQ/CloakBrowser) (a real Chromium with C++ source-level fingerprint patches that pass Cloudflare Turnstile and bot-detection).

Each profile is an isolated browser with its own fingerprint, proxy, cookies, and session data that **persist across restarts**. You interact with a launched profile through an in-browser **noVNC** viewer, and every running profile also exposes a **CDP endpoint** so Playwright / Puppeteer / agent-browser can drive it programmatically while you watch live.

## Why it's deployed here

- **Keep browser sessions off the local machine.** Log into a site once; the warm session lives on this always-on box, not your laptop.
- **Home-IP egress.** The browser exits via this machine's residential IP, so banks/Google see a consistent home location - fewer 2FA challenges than a datacenter IP.
- **Tailnet-only.** This app holds live logged-in account sessions. It is `exposable: false` (never on the public domain) and requires an **Auth Token**. Reach it over the tailnet at this host's LAN IP and port.

## After install

1. Open the web UI on port **8080** over the tailnet and unlock with your Auth Token.
2. **Create a profile**, click **Launch**, and log into your site through the noVNC view.
3. Grab the profile's CDP URL (`/api/profiles/<id>/cdp`) from the toolbar to drive it with agent-browser:
   `agent-browser connect "http://<host>:8080/api/profiles/<id>/cdp"`.

## Notes

- amd64 only (the CloakBrowser Chromium binary). Early-alpha upstream - expect rough edges.
- `mem_limit: 3g` + `shm_size: 2gb` cap resource use; run one profile at a time on low-power hardware.
- Profiles have **no built-in idle stop** - stop them when done, or pair with an external idle reaper.
