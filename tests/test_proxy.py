from unittest.mock import Mock

import pytest
import requests
from requests.adapters import HTTPAdapter
from urllib3.contrib.socks import SOCKSProxyManager

from ehentai import signin


@pytest.mark.parametrize('proxy', [
    'http://127.0.0.1:7890', 'https://127.0.0.1:7890',
    'socks4://127.0.0.1:1080', 'socks4a://127.0.0.1:1080',
    'socks5://127.0.0.1:1080', 'socks5h://127.0.0.1:1080',
])
def test_proxy_configuration_reaches_request(proxy, monkeypatch):
    monkeypatch.setattr(signin, 'read_env', lambda: {
        'E_COOKIE': 'id=value', 'E_PROXY': proxy, 'Notify': '',
    })
    get = Mock()
    monkeypatch.setattr(signin.requests, 'get', get)
    signin.init_config()
    signin.do_request()
    assert get.call_args.kwargs['proxies'] == {'http': proxy, 'https': proxy}
    assert 'verify' not in get.call_args.kwargs


@pytest.mark.parametrize('scheme', ['http', 'https'])
def test_http_proxy_adapters_support_schemes(scheme):
    manager = HTTPAdapter().proxy_manager_for(f'{scheme}://127.0.0.1:7890')
    assert manager.proxy.scheme == scheme


@pytest.mark.parametrize(('scheme', 'rdns'), [
    ('socks4', False), ('socks4a', True), ('socks5', False), ('socks5h', True),
])
def test_socks_proxy_adapters_support_dns(scheme, rdns):
    manager = HTTPAdapter().proxy_manager_for(f'{scheme}://127.0.0.1:1080')
    assert isinstance(manager, SOCKSProxyManager)
    assert manager.connection_pool_kw['_socks_options']['rdns'] is rdns


def test_retry_succeeds_or_raises_without_tls_fallback(monkeypatch):
    result = object()
    request = Mock(side_effect=[requests.ConnectionError('one'), result])
    sleep = Mock()
    monkeypatch.setattr(signin, 'do_request', request)
    monkeypatch.setattr(signin.time, 'sleep', sleep)
    assert signin.request_page() is result
    assert request.call_count == 2
    sleep.assert_called_once_with(2)

    request.reset_mock(side_effect=True)
    request.side_effect = requests.ConnectionError('failed')
    sleep.reset_mock()
    with pytest.raises(requests.ConnectionError):
        signin.request_page()
    assert request.call_count == 3
    assert sleep.call_count == 2
