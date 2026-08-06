# Cleanuparr

Advanced download manager for the Servarr ecosystem. Cleanuparr watches the Sonarr
and Radarr queues and removes downloads that would otherwise sit there forever and
silently block new grabs.

## What it does

- **Strike system** - downloads that are stalled, stuck downloading metadata, failing
  to import, or unreasonably slow accumulate strikes and are removed + blocked once
  they hit the limit.
- **Auto search** - triggers a replacement search in the *arr after removing a bad
  download, so the item does not just go missing.
- **Malware blocking** - removes known-malicious payloads (`.lnk`, `.zipx` and other
  community-sourced patterns) that get stuck pending import.
- **Seeding cleanup** - removes torrents that have seeded past a configured time or
  ratio.
- **Orphan detection** - finds files with no hardlinks and nothing referencing them
  in the *arrs, and can move or purge them.

## Setup

Everything is configured in the web UI after install: add your Sonarr, Radarr and
download-client connections, then enable the individual jobs. Nothing runs until you
enable it.

Supports Sonarr, Radarr, Lidarr, Readarr and Whisparr alongside qBittorrent,
Transmission, Deluge, rTorrent and uTorrent.
