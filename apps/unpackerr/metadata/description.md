# Unpackerr

Unpackerr monitors your Sonarr, Radarr, Lidarr, and Readarr download queues and automatically extracts RAR, ZIP, and other compressed archives when downloads complete. It seamlessly integrates with the *arr suite to ensure your media files are ready for import without manual intervention.

## Features

- **Automatic Extraction**: Monitors download queues and extracts archives automatically
- **Multi-App Support**: Works with Sonarr, Radarr, Lidarr, Readarr, and Whisparr
- **Archive Format Support**: Handles RAR, ZIP, 7z, and other common archive formats
- **Cleanup After Import**: Automatically removes extracted files after successful import
- **Prometheus Metrics**: Built-in web server for monitoring and Grafana integration
- **Folder Watching**: Can also monitor standalone folders for extraction

## Runtipi Integration

This app is pre-configured to work with other *arr apps in Runtipi:

- **Sonarr**: Default URL `http://sonarr:8989`
- **Radarr**: Default URL `http://radarr:7878`
- **Lidarr**: Default URL `http://lidarr:8686`
- **Readarr**: Default URL `http://readarr:8787`

All apps share the same Docker network, so they can communicate using their service names.

## Setup

1. Install and configure your *arr apps (Sonarr, Radarr, etc.) first
2. Get the API key from each app (Settings > General > Security)
3. Enter the API keys in the Unpackerr configuration
4. The default URLs are pre-configured for Runtipi's internal networking

## How It Works

1. Unpackerr polls the *arr apps' download queues every 2 minutes (configurable)
2. When a download completes that contains compressed archives, Unpackerr extracts them
3. The *arr app imports the extracted media files
4. Unpackerr cleans up the extracted files after successful import

## Metrics

Access Prometheus metrics at port 5656 for monitoring extraction activity. A Grafana dashboard is available at [grafana.com/dashboards/18817](https://grafana.com/grafana/dashboards/18817-unpackerr/).

## Storage

- Configuration is stored in `/config`
- Logs are stored in `/data/unpackerr.log`
- The `/data` volume should match your media/downloads directory
