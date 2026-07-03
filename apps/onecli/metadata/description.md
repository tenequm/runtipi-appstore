# OneCLI

[OneCLI](https://onecli.sh) is an open-source **credential gateway with a built-in vault** for AI agents. Store your real API credentials once; agents get placeholder keys and make normal HTTP calls through the gateway, which matches each request, decrypts the right secret at request time, and injects it into the outbound call. **Agents never see the real keys.**

This app runs the self-hosted **Community edition** (`ghcr.io/onecli/onecli`) with a bundled PostgreSQL, following the [official self-hosting docs](https://onecli.sh/docs/self-hosting/community).

## What's in the box

| Component | Port | What it does |
| --- | --- | --- |
| Dashboard | `10254` | Web UI for connecting apps and managing secrets, agents, and rules |
| REST API | `10254` (`/v1`) | Same API as OneCLI Cloud, served by your instance |
| Gateway | `10255` | The HTTPS proxy your agents route through for credential injection and policy enforcement |

- Secrets are **AES-256-GCM encrypted at rest** in the bundled PostgreSQL; request activity is logged to your database only.
- **Rules** let you block operations, rate-limit sensitive actions, and scope access per agent.

## Security notes

- By default the instance runs in **single-user mode**: no login screen - anyone who can reach port `10254` has admin access. Keep the app unexposed (LAN/VPN only), or set **NextAuth Secret** + Google OAuth credentials to switch to multi-user mode.
- Treat `10254` as an admin interface; expose `10255` wherever your agents run.
- The vault encryption key is auto-generated on first start and persisted in the app's data directory unless you set it explicitly.

## After install

1. Open the dashboard on port `10254` and create an agent.
2. Add your secrets (or connect apps with your own OAuth credentials - callback URL is `{APP_URL}/v1/apps/{provider}/callback`).
3. Point your agent's HTTP proxy at `<server>:10255`, or use the [CLI](https://onecli.sh/docs/cli/onecli-cli) / [SDKs](https://onecli.sh/docs/sdks/node) to wire agents up automatically.

## Migrating from a standalone docker-compose install

Restore a `pg_dump` of your old database into the bundled PostgreSQL and copy the contents of the old `app-data` volume (`secret-encryption-key`, `gateway/` CA, `runtime-config.json`) into this app's `data/` directory before first use - or set **Secret Encryption Key** to your existing key. Database migrations run automatically on start.
