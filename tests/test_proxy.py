import unittest
from unittest.mock import Mock, patch

import requests
from requests.adapters import HTTPAdapter
from urllib3.contrib.socks import SOCKSProxyManager

from ehentai import signin


class ProxyAndRetryTests(unittest.TestCase):
    def test_proxy_configuration_reaches_request(self):
        for proxy in ('http://127.0.0.1:7890', 'https://127.0.0.1:7890',
                      'socks4://127.0.0.1:1080', 'socks4a://127.0.0.1:1080',
                      'socks5://127.0.0.1:1080', 'socks5h://127.0.0.1:1080'):
            with self.subTest(proxy=proxy), patch.object(signin, 'read_env', return_value={
                'E_COOKIE': 'id=value', 'E_PROXY': proxy, 'Notify': ''
            }), patch.object(signin.requests, 'get') as get:
                signin.init_config()
                signin.do_request()
                self.assertEqual(get.call_args.kwargs['proxies'], {'http': proxy, 'https': proxy})
                self.assertNotIn('verify', get.call_args.kwargs)

    def test_requests_proxy_adapters_support_schemes_and_dns(self):
        adapter = HTTPAdapter()
        for scheme in ('http', 'https'):
            with self.subTest(scheme=scheme):
                manager = adapter.proxy_manager_for(f'{scheme}://127.0.0.1:7890')
                self.assertEqual(manager.proxy.scheme, scheme)
        for scheme, rdns in (('socks4', False), ('socks4a', True),
                             ('socks5', False), ('socks5h', True)):
            with self.subTest(scheme=scheme):
                manager = adapter.proxy_manager_for(f'{scheme}://127.0.0.1:1080')
                self.assertIsInstance(manager, SOCKSProxyManager)
                self.assertEqual(manager.connection_pool_kw['_socks_options']['rdns'], rdns)

    def test_retry_succeeds_or_raises_without_tls_fallback(self):
        result = object()
        with patch.object(signin, 'do_request', side_effect=[requests.ConnectionError('one'), result]) as request, \
             patch.object(signin.time, 'sleep') as sleep:
            self.assertIs(signin.request_page(), result)
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once_with(2)
        with patch.object(signin, 'do_request', side_effect=requests.ConnectionError('failed')) as request, \
             patch.object(signin.time, 'sleep') as sleep:
            with self.assertRaises(requests.ConnectionError):
                signin.request_page()
            self.assertEqual(request.call_count, 3)
            self.assertEqual(sleep.call_count, 2)


if __name__ == '__main__':
    unittest.main()
