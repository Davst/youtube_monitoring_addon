import os
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import main
from app import history_store
from app.fetcher import YouTubeHistoryFetcher, MAX_HISTORY_ITEMS
from app.mqtt_publisher import MqttPublisher


def short(video_id):
    return {'shortsLockupViewModel': {
        'entityId': 'shorts-shelf-' + video_id,
        'onTap': {'innertubeCommand': {'reelWatchEndpoint': {'videoId': video_id}}},
        'overlayMetadata': {'primaryText': {'content': 'A Short'}}}}


def page(items):
    return {'contents': {'twoColumnBrowseResultsRenderer': {'tabs': [{'tabRenderer': {
        'content': {'sectionListRenderer': {'contents': [
            {'itemSectionRenderer': {'contents': items}}]}}}}]}}}


class ShortsPipelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path_patch = patch.object(history_store, '_get_history_path',
                                       return_value=os.path.join(self.tmp.name, 'history.json'))
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.fetcher = YouTubeHistoryFetcher(os.path.join(self.tmp.name, 'absent.txt'))
        self.thumb = patch.object(self.fetcher, '_get_best_thumbnail', return_value='thumbnail')
        self.thumb.start()
        self.addCleanup(self.thumb.stop)

    def test_parser_keeps_page_order_and_all_shorts_with_hyphenated_ids(self):
        data = page([{'reelShelfRenderer': {'items': [short('abc-def_123'), short('second12345')]}},
                     {'videoRenderer': {'videoId': 'regular1234', 'title': {'simpleText': 'Regular'}}}])
        videos = self.fetcher._parse_history_data(data)
        self.assertEqual([v['video_id'] for v in videos], ['abc-def_123', 'second12345', 'regular1234'])
        self.assertEqual([v['video_type'] for v in videos], ['short', 'short', 'video'])

    def test_short_presented_as_regular_renderer_is_verified_and_cached(self):
        from types import SimpleNamespace
        data = page([{'videoRenderer': {'videoId': 'short123456',
                     'title': {'simpleText': 'Synthetic short'},
                     'lengthText': {'simpleText': '0:50'}}}])
        response = SimpleNamespace(status_code=200, url='https://www.youtube.com/shorts/short123456?ucbcb=1')
        with patch('app.fetcher.requests.head', return_value=response) as head:
            first = self.fetcher._parse_history_data(data)
            second = self.fetcher._parse_history_data(data)
        self.assertEqual(first[0]['video_type'], 'short')
        self.assertEqual(second[0]['video_type'], 'short')
        self.assertEqual(first[0]['url'], 'https://www.youtube.com/shorts/short123456')
        self.assertEqual(head.call_count, 1)

    def test_short_duration_alone_does_not_make_a_short(self):
        from types import SimpleNamespace
        data = page([{'videoRenderer': {'videoId': 'regular1234',
                     'lengthText': {'simpleText': '0:14'}}}])
        response = SimpleNamespace(status_code=200, url='https://www.youtube.com/watch?v=regular1234')
        with patch('app.fetcher.requests.head', return_value=response):
            self.assertEqual(self.fetcher._parse_history_data(data)[0]['video_type'], 'video')

    def test_shorts_verification_is_bounded(self):
        from types import SimpleNamespace
        data = page([{'videoRenderer': {'videoId': f'{i:011d}',
                     'lengthText': {'simpleText': '0:50'}}} for i in range(20)])
        response = SimpleNamespace(status_code=429, url='https://www.youtube.com/')
        with patch('app.fetcher.requests.head', return_value=response) as head:
            self.fetcher._parse_history_data(data)
            self.fetcher._parse_history_data(data)
        self.assertEqual(head.call_count, 1)

    def test_explicit_short_endpoint_needs_no_verification_request(self):
        data = page([{'videoRenderer': {'videoId': 'short123456',
                     'navigationEndpoint': {'reelWatchEndpoint': {'videoId': 'short123456'}}}}])
        with patch('app.fetcher.requests.head') as head:
            self.assertEqual(self.fetcher._parse_history_data(data)[0]['video_type'], 'short')
        head.assert_not_called()

    def test_later_short_verification_repairs_archive_without_new_observation(self):
        main.on_video_change({'video_id': 'short123456', 'duration': '0:50'})
        before = next(iter(history_store.load_history().values()))[0]
        main.record_history_snapshot([{'video_id': 'short123456', 'video_type': 'short',
                                      'url': 'https://www.youtube.com/shorts/short123456'}])
        entries = next(iter(history_store.load_history().values()))
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['timestamp'], before['timestamp'])
        self.assertEqual(entries[0]['video_type'], 'short')

    def test_latest_type_correction_is_republished_to_mqtt(self):
        from types import SimpleNamespace
        from contextlib import ExitStack
        fetcher = SimpleNamespace(history_data=[], history_by_channel={}, cookies_valid=True)
        rounds = iter(['video', 'short'])
        def fetch_history():
            fetcher.history_data = [{'video_id': 'short123456', 'video_type': next(rounds)}]
            fetcher.history_by_channel = {'default': fetcher.history_data}
        fetcher.fetch_history = fetch_history
        publisher = MqttPublisher('unused')
        publisher._connected = True
        messages = {}
        publisher._publish = lambda topic, payload, **kwargs: messages.update({topic: payload})
        sleeps = []
        def sleep(seconds):
            if seconds == 60:
                sleeps.append(seconds)
                if len(sleeps) == 2:
                    raise KeyboardInterrupt()
        with ExitStack() as stack:
            for name, value in {'fetcher': fetcher, 'mqtt_pub': publisher,
                                '_last_seen_by_channel': {}, '_recent_added': {},
                                '_last_subscriptions_fetch': 10**20}.items():
                stack.enter_context(patch.object(main, name, value))
            stack.enter_context(patch.object(main, 'load_options', return_value={'scan_interval': 60, 'fetch_recommended': False}))
            stack.enter_context(patch.object(main, 'maintain_cookies'))
            stack.enter_context(patch.object(main.time, 'sleep', side_effect=sleep))
            with self.assertRaises(KeyboardInterrupt):
                main.fetch_loop()
        self.assertEqual(messages['youtube_monitoring_dev/recent_watched/attributes']['video_type'], 'short')

    def test_shorts_share_global_limit(self):
        videos = self.fetcher._parse_history_data(page([
            {'reelShelfRenderer': {'items': [short(f'{i:011d}') for i in range(40)]}}]))
        self.assertEqual(len(videos), MAX_HISTORY_ITEMS)

    def test_archive_short_and_regular_once_with_explicit_type(self):
        short_data = {'video_id': 'short123456', 'url': 'https://www.youtube.com/shorts/short123456'}
        self.assertTrue(main.on_video_change(short_data))
        self.assertFalse(main.on_video_change(short_data))
        self.assertTrue(main.on_video_change({'video_id': 'regular1234'}))
        entries = next(iter(history_store.load_history().values()))
        self.assertEqual([v['video_type'] for v in entries], ['video', 'short'])
        self.assertEqual(history_store.get_monthly_breakdown(history_store.load_history()),
                         {next(iter(history_store.load_history()))[:7]: {'videos': 1, 'shorts': 1}})

    def test_stats_understand_explicit_and_legacy_short_types(self):
        stats = history_store.get_monthly_breakdown({'2026-11-26': [
            {'video_type': 'short'}, {'url': 'https://www.youtube.com/shorts/abc'},
            {'duration': 'Shorts'}, {'duration': '10:00'}]})
        self.assertEqual(stats['2026-11'], {'shorts': 3, 'videos': 1})

    def test_history_and_stats_endpoints_include_shorts(self):
        main.on_video_change({'video_id': 'short123456', 'duration': 'Shorts'})
        handler = object.__new__(main.YouTubeMonitoringHandler)
        output = []
        handler.send_json = output.append
        with patch.object(main, 'fetcher', None), patch.object(main, 'get_monthly_subscription_changes', return_value={}):
            handler._serve_history({})
            handler._serve_stats()
        self.assertEqual(len(next(iter(output[0]['by_date'].values()))), 1)
        self.assertEqual(next(iter(output[1]['monthly_breakdown'].values()))['shorts'], 1)

    def test_snapshot_archives_all_visible_items_once_in_response_order(self):
        videos = [{'video_id': 'short123456', 'duration': 'Shorts'},
                  {'video_id': 'regular1234'}]
        self.assertEqual(main.record_history_snapshot(videos), 2)
        self.assertEqual(main.record_history_snapshot(videos), 0)
        entries = next(iter(history_store.load_history().values()))
        self.assertEqual([v['video_id'] for v in entries], ['short123456', 'regular1234'])

    def test_unchanged_snapshot_reads_archive_only_once(self):
        videos = [{'video_id': 'regular1234'}]
        main.record_history_snapshot(videos)
        with patch.object(main, 'load_history', wraps=main.load_history) as load:
            self.assertEqual(main.record_history_snapshot(videos * 20), 0)
        self.assertEqual(load.call_count, 1)

    def test_ingest_ignores_non_string_url(self):
        import io
        import json
        payload = json.dumps({'video_id': 'regular1234', 'url': 123}).encode()
        handler = object.__new__(main.YouTubeMonitoringHandler)
        handler.headers = {'Content-Length': str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        output = []
        handler.send_json = lambda data, **kwargs: output.append(data)
        with patch.object(main, '_recent_added', {}):
            handler._handle_ingest()
        self.assertEqual(output[0]['status'], 'ok')

    def test_browser_ingest_accepts_short_and_builds_safe_url(self):
        import io
        import json
        payload = json.dumps({'video_id': 'short123456', 'video_type': 'short',
                              'url': 'https://untrusted.invalid/'}).encode()
        handler = object.__new__(main.YouTubeMonitoringHandler)
        handler.headers = {'Content-Length': str(len(payload))}
        handler.rfile = io.BytesIO(payload)
        output = []
        handler.send_json = lambda data, **kwargs: output.append(data)
        with patch.object(main, '_recent_added', {}):
            handler._handle_ingest()
        self.assertEqual(output[0]['status'], 'ok')
        entry = next(iter(history_store.load_history().values()))[0]
        self.assertEqual(entry['url'], 'https://www.youtube.com/shorts/short123456')
        self.assertEqual(entry['video_type'], 'short')

    def test_mqtt_exposes_observed_counts_and_type(self):
        publisher = MqttPublisher('unused')
        messages = {}
        publisher._publish = lambda topic, payload, **kwargs: messages.update({topic: payload})
        publisher.publish_discovery()
        self.assertIn('homeassistant/sensor/youtube_monitoring_dev/observed_shorts/config', messages)
        publisher.publish_history_counts({'2026-11-26': [{'video_type': 'short'}, {'video_type': 'video'}]})
        self.assertEqual(messages['youtube_monitoring_dev/observed_shorts/state'], '1')
        self.assertEqual(messages['youtube_monitoring_dev/observed_videos/state'], '1')
        publisher.publish_recent_watched([{'duration': 'Shorts'}])
        self.assertEqual(messages['youtube_monitoring_dev/recent_watched/attributes']['video_type'], 'short')


if __name__ == '__main__':
    unittest.main()

