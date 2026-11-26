# Shorts support: first local increment

## Behavior

- Parse all supported Shorts cards in a reel shelf, direct Shorts cards and mixed regular-video renderers in response order. Prefer the reel endpoint video ID; preserve hyphens in IDs.
- Apply the existing 20-item cap across regular videos and Shorts, per parsed channel response. Skip repeated IDs within a response.
- Archive every newly visible ID in each channel snapshot, rather than only its first item. Insert a batch in response order. Existing regular-video extraction and recommendation behavior remain supported.
- Store explicit `video_type`: `short` or `video`. Recognize legacy `duration: "Shorts"`, Shorts URLs and the old Shorts placeholder channel in statistics. No migration rewrites old files.
- Include Shorts in `/api/history`, `/api/stats`, the daily list and calendar details. Browser ingestion accepts Shorts and still constructs trusted URLs/thumbnails from a validated video ID.
- MQTT discovery adds `youtube_monitoring_dev_observed_shorts` and `youtube_monitoring_dev_observed_videos` unique IDs, with retained count states at `youtube_monitoring_dev/observed_shorts/state` and `youtube_monitoring_dev/observed_videos/state`. These are totals of archived IDs, across all dates, refreshed at startup and on polling. The recent-watched sensor and its recent list include `video_type`.

## What counts mean

The archive remains **one record per video ID for its entire lifetime**, across channels and days. `has_video_id` still enforces this. `duplicate_minutes` is an additional browser-ingest debounce, not a repeat-watch counter. Rewatching an archived ID does not increase counts. Manually edited legacy archives can contain duplicates; counts reflect their stored rows.

`timestamp` is when the add-on first archives the item in the configured timezone. It is not the actual watch time. Enabling this version can import older items visible on the first page into today's observation bucket. Duration describes video metadata, not time spent watching. Shorts currently have no reliable duration or channel attribution beyond the placeholder when the renderer does not supply them.

Response order is preserved across renderer types. Shorts shelf order is presentation order; it does not establish exact interleaving with regular watches. Multiple account channels are merged round-robin upstream, so the merged recent sensor is not a globally chronological timeline.

## Polling and completeness

No history continuation/pagination is fetched in this increment. At most 20 supported distinct items are parsed from the first response for each channel; the merged live list is capped again at 20. Polling archives the per-channel snapshots, which can collectively exceed the merged live-list limit. Rapid scrolling through Shorts can exceed this window between polls, so complete history and repeat totals cannot be promised.

The add-on defaults to a 60-second scan interval (HA schema allows 30–300 seconds), plus request latency, two-second inter-request pauses and per-channel pauses. All-channel mode adds channel discovery and browse requests. Subscriptions are checked every 120 seconds; recommendations use their separate configured interval. Thumbnail checks are cached but add requests for new IDs. HTTP 429 is recognized; there is no adaptive backoff in this increment. No polling intervals were shortened.

## Access controls and cookie handling

The development add-on uses slug `youtube_monitoring_dev`, version `1.6.0-dev.1`, private `/data/youtube_cookies.txt` storage, an admin-only sidebar entry and no host port published by default. MQTT uses separate `youtube_monitoring_dev` device, entity IDs, topics and client ID to avoid collisions with the upstream add-on.

All HTTP routes require the actual HA Ingress proxy peer when a Supervisor token is present. Forged Ingress headers from other peers do not grant access. Standalone mode binds to 127.0.0.1 and accepts only loopback peers and localhost/loopback Host names. Cross-site browser requests and mismatched Origin/Host requests are rejected; wildcard CORS has been removed. This deliberately disables direct cross-origin userscript ingestion. Browser-ingest support needs a separately authenticated design before it can be enabled safely.

Cookie file loading now filters unrelated domains just like uploads and discards expired cookies. Cookie replacement is atomic and attempts mode 0600; it does not retain a `.bak` copy. Deleted authentication cookies stay deleted rather than being restored from memory. Existing `.bak` files from previous versions are not removed automatically: review and delete them through your own trusted file access. POSIX mode 0600 is not a complete Windows ACL guarantee. Exclude all credential files from source control.

No real account credentials were used during automated testing. Exported cookies still grant account access. Use only your own explicitly authorized test account and upload through Home Assistant Ingress. Review who has admin access to that Home Assistant. Remote broker access, Google cookie rotation and the real Ingress forwarded-header behavior still need live checks.

The example userscript is not an audited reliable collector: regular-watch ID parsing uses pathname rather than the query string, DOM selectors can miss Shorts metadata, and failures are swallowed. Its cross-origin requests are now rejected by design. This increment validates the local/Ingress ingestion API, not the userscript.

## Verification and next increment

Run offline synthetic tests from the repository root:

```powershell
python -X utf8 -m unittest discover -s youtube_monitoring/tests
```

Tests cover mixed renderer ordering, multiple Shorts per shelf, hyphenated IDs, shared limits, regular-video preservation, archive deduplication, API visibility, normalized ingestion, MQTT discovery/count/type payloads and unchanged-snapshot read cost. Existing cookie tests use synthetic credentials and mocked remote requests. HTTP integration tests bind only localhost and use temporary history files.

Before deployment: verify real current YouTube renderer samples using an explicitly authorized test account, test HA Ingress and MQTT discovery/reconnection against a broker, confirm timezone/observation-day behavior, inspect high-volume sessions and 429 recovery, and verify the cookie/access protections above against the actual HA proxy. Automated tests do not deploy the add-on or access real accounts. See `development-testing.md` for the isolated HA test procedure.
