# Dispatcharr (VPN gateway)

Dispatcharr is the \*arr-family **IPTV / M3U / Xtream stream manager**. It sits between your IPTV provider(s) and Jellyfin/Plex/Emby: ingest playlists, filter and organise channels, auto-match EPG, and re-serve everything as a stable HDHomeRun / M3U / XMLTV source.

This deployment forces all provider traffic through a **WireGuard VPN gateway**. A `gluetun` container (custom WireGuard mode) holds the network namespace and Dispatcharr shares it, so:

- **Kill-switch**: if the tunnel drops, gluetun's firewall blocks all egress - the provider connection cannot leak.
- **ISP bypass**: the local ISP never sees the (often plain-HTTP) stream URLs and cannot block them. The provider sees the gateway IP.
- **No port forwarding**: IPTV is pull-only, so the tunnel needs no inbound port.

## Why Dispatcharr in the middle

- Absorbs provider churn (URL rotation, http/https) behind a stable local endpoint - configure channels/EPG once.
- Proxy engine multiplexes **one upstream connection** to many local viewers, respecting provider connection limits.
- Buffering + automatic failover between redundant streams for stability.
- Optional Intel QuickSync (VA-API via `/dev/dri`) hardware transcoding for output profiles and DVR.

## After install

1. Open the web UI on port 9191, create the admin account.
2. Settings -> M3U & EPG Manager -> add your provider as an **Xtream Codes** account.
3. Filter to the channels you want, let EPG auto-match.
4. In Jellyfin: Live TV -> add Dispatcharr's **M3U/HDHR tuner** + **XMLTV guide** URLs (leave Jellyfin's stream limit at 0).
5. Keep the channel **Stream Profile** on **Proxy** so traffic egresses through the VPN.
