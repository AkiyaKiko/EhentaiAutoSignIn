import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import requests

from ehentai import config, signin


def response(html, set_cookies=()):
    headers = SimpleNamespace(getlist=lambda name: list(set_cookies))
    return SimpleNamespace(text=html, raw=SimpleNamespace(headers=headers))


class SigninTests(unittest.TestCase):
    def test_cookie_update_persists_and_notifies(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            path.write_text(
                "# keep comment\nE_COOKIE='ipb_member_id=123; event=old; other=value'\n"
                "Notify='{\"GOTIFY_URL\":\"https://example.com\",\"GOTIFY_TOKEN\":\"token\"}'\n",
                encoding='utf-8',
            )
            cookies = [
                'event=new; Path=/',
                'sk=abc; expires=Wed, 21 Oct 2037 07:28:00 GMT; Path=/',
            ]
            with patch.dict(os.environ, {}, clear=True), \
                 patch.object(signin, 'read_env', side_effect=lambda: config.read_env(path)), \
                 patch.object(signin, 'save_cookie', side_effect=lambda value: config.save_cookie(value, path)), \
                 patch.object(signin, 'request_page', return_value=response('<div id="eventpane"><p>Reward</p></div>', cookies)), \
                 patch.object(signin.notify, 'send') as send:
                self.assertEqual(signin.scrape(), ['Reward'])
                saved = config.read_env(path)
                self.assertEqual(saved['E_COOKIE'], 'ipb_member_id=123; event=new; other=value; sk=abc')
                self.assertIn('# keep comment', path.read_text(encoding='utf-8'))
                self.assertEqual(send.call_count, 2)
                self.assertIn('sk 过期时间', send.call_args_list[0].args[1])
                self.assertEqual(send.call_args_list[1].args[1], '签到成功！\nReward')
                signin.init_config()
                self.assertEqual(signin.headers['Cookie'], saved['E_COOKIE'])

    def test_signin_results_and_request_errors(self):
        cases = (
            ('<html></html>', '没有事件，已经签到了！', '没有事件，已经签到了！'),
            ('<div id="eventpane">Random Encounter</div>', 'Random Encounter', 'Random Encounter'),
            ('<div id="eventpane"><p>Prize</p></div>', ['Prize'], '签到成功！'),
        )
        for html, expected, message in cases:
            with self.subTest(html=html), patch.object(signin, 'init_config'), \
                 patch.object(signin, 'request_page', return_value=response(html)), \
                 patch.object(signin, 'send_notify') as send:
                self.assertEqual(signin.scrape(), expected)
                self.assertIn(message, send.call_args.args[1])
        with patch.object(signin, 'init_config'), \
             patch.object(signin, 'request_page', side_effect=requests.ConnectionError('failed')), \
             patch.object(signin, 'send_notify') as send:
            with self.assertRaises(requests.ConnectionError):
                signin.scrape()
            self.assertEqual(send.call_args.args[0], '请求错误')

    def test_notification_configuration_validation(self):
        self.assertEqual(signin.parse_notify_config(''), {})
        self.assertEqual(signin.parse_notify_config('{}'), {})
        self.assertEqual(signin.parse_notify_config('{"HITOKOTO":false}'), {'HITOKOTO': 'false'})
        for value in ('bad-json', '[]', '{"unknown":1}', '{"HITOKOTO":null}'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                signin.parse_notify_config(value)


if __name__ == '__main__':
    unittest.main()
