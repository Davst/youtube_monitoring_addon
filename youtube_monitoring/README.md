> Development branch: install **YouTube Monitoring Dev** through Home Assistant Ingress. Direct LAN/API and cross-origin userscript access are disabled. See [test instructions](docs/development-testing.md).

# YouTube Monitoring Add-on

A standalone Home Assistant Add-on that tracks your YouTube watch history (daily/monthly), subscriptions, and recommended videos using only YouTube cookies.

> Full documentation: [English README](../README.md) | [한국어 README](../README.ko.md)

## Key Features

- Cookie-based watch history polling (default interval: 60s)
- Automatic cookie refresh (saves response cookies + rotates Google cookies every 10 minutes, with HA notification on failure)
- Multi-channel collection (`scan_all_channels`: merges main channel and Brand Accounts)
- Daily history & Monthly calendar view (including Shorts)
- Subscriptions list with thumbnails, subscriber counts, `@handles`, and sorting (Alphabetical / By Subscribers)
- Monthly subscription changes (added / removed)
- Recommended videos with manual refresh (10-minute cooldown)
- Bilingual Web UI (**English / 한국어** toggle button) & Ingress sidebar panel (**YouTube Watch History**)
- Optional MQTT Discovery sensors & real-time push (`POST /api/ingest`)

## Quick Start

1. Install **YouTube Monitoring** from **Settings** → **Add-ons**
2. Open the **YouTube Watch History** panel → click **Update Cookies** (top right) and upload `youtube_cookies.txt` (export from an Incognito window, then close the window immediately)
3. The add-on will automatically refresh your cookies going forward

## Configuration

| Option | Description | Default |
|--------|-------------|---------|
| `cookies_path` | Path to cookies file | `/data/youtube_cookies.txt` |
| `scan_interval` | History/subscription polling interval (sec) | `60` |
| `port` | API server port | `8765` |
| `duplicate_minutes` | Duplicate video ignore window (min) | `5` |
| `fetch_recommended` | Fetch recommended videos | `true` |
| `scan_interval_recommended` | Recommended videos interval (sec) | `1800` |
| `timezone` | Timezone for logs and daily grouping | `Europe/Stockholm` |
| `notify_cookie_invalid` | HA notification on cookie expiration | `true` |
| `scan_all_channels` | Collect history & subscriptions across all channels | `true` |

## Documentation

- [English README](../README.md) / [한국어 README](../README.ko.md)
- [DOCS.md](DOCS.md) - API & detailed reference
- [CHANGELOG.md](CHANGELOG.md) - Version history

## License

[MIT License](../LICENSE)

## Shorts development increment

Shorts are archived with `video_type: "short"`, shown in daily and calendar views, and included in monthly breakdowns. MQTT exposes distinct archived Shorts/video counts. These are observations, not play totals or watch time. See [scope and live-use review](docs/shorts-support.md).
