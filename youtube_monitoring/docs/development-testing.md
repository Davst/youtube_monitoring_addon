# Isolated Home Assistant development test

This branch is a development build, version `1.6.0-dev.1`, with a separate add-on slug and MQTT device. Keep the upstream installation untouched.

## Install

1. Add `https://github.com/Davst/youtube_monitoring_addon#codex/shorts-observation-support` as the app repository. Home Assistant supports selecting a repository branch with `#branch` ([official repository guide](https://contributors.home-assistant.io/apps/guides/repository/)). Alternatively, copy the `youtube_monitoring` directory to HA's `/addons/youtube_monitoring_dev` local add-on directory.
2. Refresh the add-on store, find **YouTube Monitoring Dev**, and build/install it. Leave host port 8765 disabled. Open it through **Open Web UI** / Ingress using an HA administrator account.
3. Set timezone to `Europe/Stockholm` and leave the cookie path as `/data/youtube_cookies.txt`. For an initial smoke test, disable recommendations and all-channel scanning to reduce requests.
4. Start without cookies first. Expect an empty history and a cookie-invalid status. Confirm the rest of HA and any upstream monitoring installation remain unaffected.
5. Upload only your own authorized test-account cookies using the Ingress UI. Do not paste cookies into chat, commits, issue reports or logs.

## Live checks

- Watch one regular video, several Shorts, then another regular video. Wait at least one full configured polling cycle plus network delays. Check type labels, video IDs, safe links and retained order in daily history and calendar details.
- Check `/api/history` through the same authenticated Ingress session. `monthly_breakdown` should split videos/Shorts; all new archive entries have explicit `video_type`.
- Repeat a poll, restart the add-on, and rewatch an archived ID. No duplicate archive row or count increase is expected. Counts are distinct observed IDs, not completed plays. Dates are first-observation dates, including older items imported from the first page.
- If HA provides MQTT, verify a separate **YouTube Monitoring Dev** device, distinct observed Shorts/video sensors and recent-watched type attributes. Test broker reconnection before relying on automation.
- A direct host-port request must not expose history or accept cookies. Cross-origin POST/preflight requests must be denied. Confirm normal cookie upload through the real proxy is accepted; Origin/forwarded-Host differences may need a narrowly scoped adjustment if your proxy changes those headers.
- Remove/revoke the test session afterward. Do not expect Google session cookies to remain valid indefinitely. The application now honors server-side deletion and expiration.

## Offline verification

```powershell
python -X utf8 -m unittest discover -s youtube_monitoring/tests
```

The tests use synthetic cookies and localhost HTTP only. No deployment or live-account state is needed.

## Rollback

Stop and uninstall **YouTube Monitoring Dev** only. Its data and MQTT IDs are separate. Remove its retained MQTT discovery records through HA/MQTT tools if removing its entities permanently. Do not remove upstream add-on data or entities.

## Build verification

The `1.6.0-dev.1` Docker image was built on Slottet and all 60 synthetic tests passed inside it with external networking disabled and the root filesystem read-only. This verifies the packaged Python/runtime behavior; it does not verify live Ingress, Google cookies or MQTT broker reconnection.

The development repository was added to the user's Home Assistant at `http://homeassistant.local/` (port 80). Its registered app slug is `cf954e00_youtube_monitoring_dev`. Installation and live-account verification are separate steps.
