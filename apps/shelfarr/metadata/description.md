# Shelfarr

A self-hosted request and download manager for ebooks and audiobooks - the books
equivalent of Jellyseerr for the *arr stack.

## How it works

1. **Discover** - search a title via Open Library, Hardcover or Google Books.
2. **Request** - pick ebook or audiobook; admins can approve or auto-approve.
3. **Search** - Shelfarr queries Prowlarr (or Jackett / NZBHydra2) and any enabled
   direct sources, then scores results against your format, bitrate and language rules.
4. **Download** - the chosen release is routed to Transmission, qBittorrent, Deluge,
   Decypharr, SABnzbd or NZBGet, with per-indexer routing and client priorities.
5. **Import** - completed files are renamed and filed using path/filename templates,
   with copy, move or hardlink import modes.
6. **Library** - Audiobookshelf (or BookOrbit / Grimmory) is told to rescan.

## Why this and not Readarr

Readarr was retired in June 2025. Shelfarr covers the gap from a different angle to the
*arr-family forks: it also supports **direct sources that are not Torznab indexers**
(Anna's Archive, Z-Library, LibriVox), and it uses open metadata providers rather than
Audible only, so non-English catalogues resolve.

## This deployment

- Runs as UID/GID 1000 to match the media tree.
- Mounts the whole `media/` root at `/media`, exactly like Radarr and Sonarr, so
  downloads and the library share one filesystem and **hardlink imports work** -
  imported books keep seeding.
- Not exposable: it holds indexer API keys and direct-source credentials, so it stays
  on the LAN / tailnet.

Configuration lives in the app's own admin UI (indexer, download clients, output paths,
library integration, notifications, OIDC).
