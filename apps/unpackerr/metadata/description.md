# Unpackerr

Unpackerr watches the Sonarr and Radarr download queues and extracts RAR, ZIP, 7z and other
archives when a download completes, then removes the extracted copy after import.

## Features

- **Automatic extraction** of completed *arr downloads, with retries
- **Web UI and HTTP API** on port 5656: live queue, history, logs and settings
- **Cleanup after import**
- **Folder watching** for archives outside the *arr apps (configured in the UI)

## Runtipi integration

Sonarr and Radarr are set from this app's form (`http://sonarr:8989`, `http://radarr:7878`
on Runtipi's shared network). Those values come from the environment, so the web UI shows
them as locked. Add Lidarr, Readarr or watch folders in the web UI; they are saved to
`/config/unpackerr.conf`.

## First start

With no UI password set, the first start prints a temporary `admin` password in the
container log. Sign in and change it under Settings; `unpackerr --reset` issues a new one.

## Links

- [Website](https://unpackerr.zip)
- [GitHub](https://github.com/Unpackerr/unpackerr)
