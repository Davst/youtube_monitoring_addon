# YouTube Monitoring Add-on

**English** | [한국어](README.ko.md)

[![Add Repository to Home Assistant](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2Fredchupa%2Fyoutube_monitoring_addon)

A **standalone** Home Assistant Add-on that tracks your YouTube watch history (daily/monthly), subscriptions, and recommended videos using only YouTube cookies.

This add-on was created for parents who want to check whether their children are watching appropriate content on a shared YouTube account. Because exporting cookies requires signing in to the YouTube account, you need access to the account's credentials.

**Happy Smart Home!**

---

## Screenshots

Taken with made-up demo data (no real watch history).

| Daily history | Subscriptions |
|:---:|:---:|
| <img src="https://raw.githubusercontent.com/redchupa/youtube_monitoring_addon/main/images/screenshots/daily-en.png" alt="Daily history" width="100%"> | <img src="https://raw.githubusercontent.com/redchupa/youtube_monitoring_addon/main/images/screenshots/subscriptions-en.png" alt="Subscriptions" width="100%"> |

## Key Features

- **Cookie-based Polling**: Directly fetches the YouTube watch history page (default interval: 60 seconds)
- **Automatic Cookie Refresh**: Saves updated cookies from responses and rotates Google cookies every 10 minutes to keep the session alive; sends a Home Assistant notification if manual re-upload is needed
- **Multi-Channel Support**: Collects watch history and subscriptions across the main channel and all Brand Accounts under the same Google account (`scan_all_channels`, enabled by default)
- **Persistent History**: Saves watch history to `/data/yt_history.json` (with 5-minute deduplication). **YouTube Shorts are excluded**
- **Daily History**: Grouped by date with collapsible sections
- **Monthly Calendar View**: Select a month to see daily watch counts; click any date to view that day's videos (Shorts excluded)
- **Subscriptions**: Displays channel thumbnails, subscriber counts, and `@handles` with **Alphabetical / By Subscribers** sorting
- **Monthly Subscription Changes**: Tracks newly subscribed and unsubscribed channels by month
- **Recommended Videos**: Shows up to 3 recommended videos from the YouTube home feed (configurable interval + manual refresh with 10-minute cooldown)
- **Bilingual Web UI (EN / KO)**: Built-in English/Korean toggle button with automatic browser language detection, plus an in-app **Update Cookies** button
- **Home Assistant Ingress**: Accessible directly from the Home Assistant sidebar as **YouTube Watch History**
- **MQTT Discovery Sensors** (Optional): Automatically registers recent watched video, recommended videos, and cookie status sensors in Home Assistant when MQTT is configured
- **Real-time Push** (Optional): Instantly record videos via `POST /api/ingest` using a browser extension or userscript (Shorts URLs are skipped)

### Why Cookies?

The official YouTube Data API v3 **does not provide access to a user's watch history**.

Advantages of the cookie-based approach:
- Direct access to the YouTube watch history page
- Accurate tracking of the most recently watched videos
- No API quota limits

> **Note**: Because the add-on polls the YouTube history page using cookies, there may be a delay of a few minutes from YouTube's servers. If you need **instant recording**, use `POST /api/ingest` with the included userscript.

---

## Requirements

- Home Assistant **Supervisor** (Add-on supported installation)
- YouTube account cookies file (`youtube_cookies.txt`)

---

## Quick Start Guide

### Step 1: Add Repository and Install Add-on

Click the **Add Repository** button at the top of this page, or add it manually:

1. Go to **Settings** → **Add-ons** → **Add-on Store** → **⋮** (top right) → **Repositories**
2. Add the repository URL:
   ```text
   https://github.com/redchupa/youtube_monitoring_addon
   ```
3. Search for **YouTube Monitoring** in the Add-on Store and install it
4. Click **Start**

---

### Step 2: Export YouTube Cookies

#### Chrome / Chromium (Recommended)

1. **Install the extension**
   - Install [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) from the Chrome Web Store
   - In extension settings, enable **"Allow in Incognito"**

2. **Sign in to YouTube in Incognito Mode**
   - Open an **Incognito / Private window** and go to [YouTube.com](https://youtube.com)
   - Sign in with your YouTube account

3. **Export cookies & close the window**
   - Click the extension icon and click **Export** to download `youtube.com_cookies.txt`
   - **Close the Incognito window immediately** (continuing to use the same session in a browser can invalidate the exported cookies quickly)

#### Firefox

Use a compatible "cookies.txt" extension in a Private Window following the same steps.

---

### Step 3: Upload Cookies

#### Option A: Web UI (Recommended)

1. Open **Settings** → **Add-ons** → **YouTube Monitoring** → **Open Web UI** (or click **YouTube Watch History** in the sidebar)
2. Click **Update Cookies** in the top right
3. Select your exported `.txt` file (or paste its contents) and click **Save & Verify**

#### Option B: Upload to `/config`

Rename the file to `youtube_cookies.txt` and place it in your Home Assistant `/config` folder via **File Editor**, **Samba/SMB** (`\\homeassistant\config`), or **SSH**:

```bash
scp youtube_cookies.txt root@homeassistant:/config/
```

---

### Step 4: Configuration

| Option | Description | Default |
|---|---|---|
| `cookies_path` | Path to the Netscape cookies file | `/config/youtube_cookies.txt` |
| `scan_interval` | History/subscription polling interval in seconds (30 to 300) | `60` |
| `port` | HTTP API server port | `8765` |
| `duplicate_minutes` | Ignore duplicate detections of the same video within N minutes (1 to 60) | `5` |
| `fetch_recommended` | Fetch recommended videos from YouTube Home | `true` |
| `scan_interval_recommended` | Recommended videos refresh interval in seconds (60 to 3600) | `1800` |
| `timezone` | Timezone for logs and daily history grouping (e.g., `America/New_York`, `Europe/London`, `Asia/Seoul`) | `Asia/Seoul` |
| `notify_cookie_invalid` | Show a Home Assistant persistent notification if cookies expire and auto-recovery fails | `true` |
| `scan_all_channels` | Collect watch history and subscriptions across the main channel and all Brand Accounts | `true` |

---

## Sidebar Panel

This add-on supports Home Assistant Ingress and appears in the sidebar as **YouTube Watch History** (visible to non-admin users as well). You can switch between **English** and **한국어** anytime using the language toggle button in the top-right corner of the Web UI.

---

## API Reference

### `GET /api/history`
Returns daily watch history, monthly stats, subscriptions, monthly subscription changes, recommended videos, and cookie maintenance status.

### `GET /api/stats`
Returns monthly statistics only (Shorts excluded).

### `GET /api/health`
Health check endpoint including `cookies_valid`, `cookie_problem`, and `cookie_maintenance`.

### `POST /api/cookies`
Replaces the active cookies with uploaded Netscape `cookies.txt` text and immediately verifies login status. Restricted to Home Assistant Ingress requests.

### `POST /api/refresh/recommended`
Manually refreshes recommended videos (10-minute cooldown).

### `POST /api/ingest` (Real-time Push)
Immediately records the currently playing video from a browser extension or userscript (faster than cookie polling).

```json
POST /api/ingest
Content-Type: application/json

{"video_id": "dQw4w9WgXcQ", "title": "Video Title", "channel": "Channel Name", "duration": "3:45"}
```

- `video_id` is required; all other fields are optional
- Duplicate `video_id` entries within `duplicate_minutes` are skipped
- Shorts URLs (`/shorts/`) are skipped

**Userscript setup**: Install `youtube_monitoring/docs/userscript.example.js` in Tampermonkey and update `INGEST_URL` to your add-on's Ingress URL.

---

## REST Sensor Integration (Optional)

```yaml
rest:
  - resource: http://localhost:8765/api/history
    scan_interval: 60
    sensor:
      - name: "YouTube Monitoring Monthly Count"
        unique_id: "youtube_monitoring_accumulated"
        value_template: "{{ value_json.monthly_stats | default({}) | length }}"
```

---

## Local Testing

```powershell
cd youtube_monitoring
$env:COOKIES_PATH = "C:\path\to\youtube_cookies.txt"
python main.py
```

Open `http://localhost:8765` in your browser.

---

## Cookie Security

Cookies contain **sensitive authentication credentials**. Please follow these best practices:

```bash
# Restrict file permissions via SSH
chmod 600 /config/youtube_cookies.txt
```

- Never commit or upload `youtube_cookies.txt` to public repositories (GitHub, etc.)
- Keep `youtube_cookies.txt` in `.gitignore`
- Change your Google/YouTube password immediately if you notice suspicious activity

---

## Troubleshooting

### "Cookies Invalid" is displayed

**Possible causes**:
- Missing or unreadable cookie file
- Expired session (e.g., password changed or signed out of all devices)
- Cookies were exported from a regular browser window still in active use

**Fix**:
1. Sign in to YouTube in a fresh **Incognito / Private window**
2. Export cookies with **Get cookies.txt LOCALLY** and close the Incognito window immediately
3. Click **Update Cookies** in the Web UI and upload the new file

### Watch history does not update immediately

Cookie polling relies on YouTube updating its history feed, which can take a few minutes. For instant updates, use `POST /api/ingest` with the userscript.

### HTTP 429 (Rate Limit) errors

Increase `scan_interval` to `120` seconds or higher. If you also browse YouTube on a phone simultaneously, try setting `fetch_recommended` to `false`.

### Will my history be lost when cookies expire?

**No.** Watch history and subscription changes are persisted on disk under `/data/` independently of cookies. Once you upload new cookies, tracking resumes right where it left off.

---

## Disclaimer

- This add-on is an **unofficial** project and is not affiliated with or endorsed by Google/YouTube.
- You are responsible for complying with YouTube's Terms of Service and handling your cookies safely.
- This software is provided "as is", without warranty of any kind.

---

## FAQ

**Q: Why aren't YouTube Shorts recorded?**  
A: Since v1.4.8, Shorts are intentionally excluded from both history storage and monthly statistics.

**Q: How long do cookies last?**  
A: Since v1.5.4, the add-on automatically rotates and saves cookies every 10 minutes, keeping sessions alive for months as long as the Incognito window was closed right after export.

**Q: Is this an official Home Assistant add-on?**  
A: No, it is a community-maintained standalone add-on.

**Q: What if multiple family members share the same YouTube account?**  
A: All watched videos under the account (including Brand Accounts when `scan_all_channels` is enabled) are accumulated into the watch history.

---

## Contributing & Bug Reports

Bug reports, feature requests, and Pull Requests are welcome!  
Please open an issue at [GitHub Issues](https://github.com/redchupa/youtube_monitoring_addon/issues) with:
- Home Assistant version
- Add-on version
- Error logs
- Steps to reproduce

---

## Technical Details

- **Platform**: Home Assistant Supervisor
- **Architectures**: `armhf`, `armv7`, `aarch64`, `amd64`, `i386`
- **Dependencies**: `requests`, `paho-mqtt`

---

## License

[MIT License](LICENSE)

---

## Support

If you find this add-on useful, feel free to buy me a coffee!

<table>
  <tr>
    <td align="center">
      <b>Toss (Korea)</b><br>
      <img src="https://raw.githubusercontent.com/redchupa/youtube_monitoring_addon/main/images/toss-donation.png" width="200" alt="Donate via Toss">
    </td>
    <td align="center">
      <b>PayPal</b><br>
      <img src="https://raw.githubusercontent.com/redchupa/youtube_monitoring_addon/main/images/paypal-donation.png" width="200" alt="Donate via PayPal">
    </td>
  </tr>
</table>

---

**Enjoy your Smart Home!**
