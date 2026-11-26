"""Offline access-control and cookie-handling regression tests."""
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import main
from app.cookie_manager import CookieManager
from test_cookies import COOKIES_TXT


class AccessControlTest(unittest.TestCase):
    def handler(self, peer='127.0.0.1', headers=None):
        handler = object.__new__(main.YouTubeMonitoringHandler)
        handler.client_address = (peer, 12345)
        handler.headers = headers or {'Host': '127.0.0.1:8765'}
        handler.path = '/api/history'
        return handler

    def test_standalone_rejects_lan_and_rebinding_hosts(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.handler('192.168.1.4')._is_trusted_request())
            self.assertFalse(self.handler(headers={'Host': 'attacker.example:8765'})._is_trusted_request())
            self.assertTrue(self.handler()._is_trusted_request())

    def test_ingress_requires_real_proxy_peer(self):
        with patch.dict(os.environ, {'SUPERVISOR_TOKEN': 'synthetic'}):
            self.assertFalse(self.handler(headers={'X-Ingress-Path': '/fake', 'Host': 'localhost'})._is_trusted_request())
            self.assertTrue(self.handler(main.INGRESS_PROXY_IP)._is_trusted_request())

    def test_cross_origin_browser_requests_are_rejected(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(self.handler(headers={'Host': '127.0.0.1:8765', 'Origin': 'https://evil.example'})._is_trusted_request())
            self.assertFalse(self.handler(headers={'Host': '127.0.0.1:8765', 'Sec-Fetch-Site': 'cross-site'})._is_trusted_request())
            self.assertTrue(self.handler(headers={'Host': '127.0.0.1:8765', 'Origin': 'http://127.0.0.1:8765'})._is_trusted_request())

    def test_get_post_and_preflight_reject_before_handling(self):
        for method in ('do_GET', 'do_POST', 'do_OPTIONS'):
            with self.subTest(method=method), patch.dict(os.environ, {'SUPERVISOR_TOKEN': 'synthetic'}):
                handler = self.handler()
                handler.path = '/not-a-route'
                responses = []
                handler.send_json = lambda body, status=200: responses.append(status)
                handler.send_response = lambda status: responses.append(status)
                handler.end_headers = lambda: None
                handler.send_header = lambda *args: None
                getattr(handler, method)()
                self.assertEqual(responses, [403])


class CookieSecurityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, 'cookies.txt')
        with open(self.path, 'w', encoding='utf-8') as stream:
            stream.write(COOKIES_TXT)

    def test_disk_load_filters_unrelated_domains(self):
        manager = CookieManager(self.path)
        session = manager.session()
        self.assertFalse(any(c.domain == '.example.com' for c in session.cookies))

    def test_replacement_creates_no_credential_backup(self):
        manager = CookieManager(self.path)
        manager.replace_from_text(COOKIES_TXT)
        self.assertFalse(os.path.exists(self.path + '.bak'))

    def test_server_auth_cookie_deletion_stays_deleted_on_disk(self):
        manager = CookieManager(self.path)
        session = manager.session()
        session.cookies.clear('.youtube.com', '/', 'SID')
        self.assertTrue(manager.save_if_changed())
        reloaded = CookieManager(self.path).session()
        self.assertFalse(any(c.name == 'SID' for c in reloaded.cookies))

    def test_expired_auth_cookie_is_not_loaded(self):
        from test_cookies import FAR
        with open(self.path, 'w', encoding='utf-8') as stream:
            stream.write(COOKIES_TXT.replace(f'FALSE\t{FAR}\tSID', 'FALSE\t1\tSID'))
        session = CookieManager(self.path).session()
        self.assertFalse(any(c.name == 'SID' for c in session.cookies))


class MqttIsolationTest(unittest.TestCase):
    def test_dev_discovery_uses_distinct_device_and_entity_ids(self):
        from app.mqtt_publisher import MqttPublisher
        publisher = MqttPublisher('unused')
        messages = {}
        publisher._publish = lambda topic, payload, **kwargs: messages.update({topic: payload})
        publisher.publish_discovery()
        self.assertTrue(messages)
        for payload in messages.values():
            self.assertTrue(payload['unique_id'].startswith('youtube_monitoring_dev_'))
            self.assertEqual(payload['device']['identifiers'], ['youtube_monitoring_dev'])
