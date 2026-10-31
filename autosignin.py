# 建议设置每天凌晨自动运行
'''
new Env('E-Hentai 自动签到')
1 */6 * * * autosignin.py
'''

# ================================================================
# 注意：此文件仅保留用于青龙面板兼容，后续不再维护。
# 请迁移到单机部署模式，并使用 main.py 和项目目录中的 .env。
# ================================================================

import os
import ssl
import time
import logging
import requests
import http.cookies

from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter

import notify  # 青龙面板默认通知模块


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

URL = 'https://e-hentai.org/news.php'

headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/135.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;q=0.9,'
        'image/avif,image/webp,image/apng,*/*;q=0.8,'
        'application/signed-exchange;v=b3;q=0.7'
    ),
    'Upgrade-Insecure-Requests': '1',
    'Cookie': ''
}

proxies = {}


class TLS12Adapter(HTTPAdapter):
    """强制 HTTPS 使用 TLS 1.2"""

    def __init__(self):
        self.context = ssl.create_default_context()
        self.context.minimum_version = ssl.TLSVersion.TLSv1_2
        self.context.maximum_version = ssl.TLSVersion.TLSv1_2
        super().__init__()

    def init_poolmanager(self, *args, **kwargs):
        kwargs['ssl_context'] = self.context
        return super().init_poolmanager(*args, **kwargs)

    def proxy_manager_for(self, proxy, **kwargs):
        kwargs['ssl_context'] = self.context
        return super().proxy_manager_for(proxy, **kwargs)


def send_notify(title, content):
    try:
        notify.send(f'Ehentai SignIn - {title}', content)
    except Exception as e:
        logging.error(f'发送通知失败：{e}')


def mask_cookie(cookie):
    result = []

    for item in cookie.split(';'):
        item = item.strip()

        if '=' not in item:
            result.append(item)
            continue

        key, value = item.split('=', 1)

        if len(value) > 8:
            value = value[:3] + '*' * (len(value) - 6) + value[-3:]
        elif value:
            value = value[0] + '*' * (len(value) - 1)

        result.append(f'{key}={value}')

    return '; '.join(result)


def init_config():
    proxy = os.getenv('E_PROXY')
    cookie = os.getenv('E_COOKIE')
    user_agent = os.getenv('E_USER_AGENT')

    if proxy:
        proxies.update(http=proxy, https=proxy)
        logging.info(f'使用代理: {proxy}')
    else:
        logging.info('未设置代理，将不使用代理。')

    if cookie:
        headers['Cookie'] = cookie
        logging.info(f'使用Cookie: {mask_cookie(cookie)}')
    else:
        logging.info('未设置Cookie，将不发送Cookie。')

    if user_agent:
        headers['User-Agent'] = user_agent
        logging.info(f'使用User-Agent: {user_agent}')
    else:
        logging.info('未设置User-Agent，将使用默认 User-Agent。')


def parse_set_cookie(raw_headers):
    cookies = {}
    expires = []

    for raw in raw_headers:
        parsed = http.cookies.SimpleCookie()
        parsed.load(raw)

        for key, value in parsed.items():
            cookies[key] = value.value

            if value['expires']:
                expires.append((key, value['expires']))

    return cookies, expires


def update_cookie(new_cookies, expires):
    fields = [
        'ipb_member_id',
        'ipb_pass_hash',
        'sk',
        'hath_perks',
        'nw',
        'event'
    ]

    old_cookie = os.getenv('E_COOKIE', '')
    current = {}

    for item in old_cookie.split(';'):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            current[key] = value

    updated = False

    for field in fields:
        if field in new_cookies and current.get(field) != new_cookies[field]:
            current[field] = new_cookies[field]
            updated = True

    if not updated:
        logging.info('本地 Cookie 是最新的，无需更新。')
        return

    new_cookie = '; '.join(f'{k}={v}' for k, v in current.items())
    os.environ['E_COOKIE'] = new_cookie

    logging.info(f'已更新 os.environ 中的 E_COOKIE：{mask_cookie(new_cookie)}')

    lines = [
        f'{key} 过期时间: {value}'
        for key, value in expires
        if key in current and key != 'event'
    ]

    if lines:
        send_notify('Cookie 更新提醒', '\n'.join(lines))


def do_request(session=None):
    client = session or requests

    response = client.get(
        URL,
        headers=headers,
        proxies=proxies,
        timeout=(10, 30)
    )

    response.raise_for_status()
    return response


def request_page():
    last_error = None

    # 默认 TLS，最多尝试 3 次
    for attempt in range(1, 4):
        logging.info(f'默认 TLS 请求，第 {attempt}/3 次')

        try:
            return do_request()
        except requests.exceptions.RequestException as e:
            last_error = e

        if attempt < 3:
            time.sleep(2)

    # 默认 TLS 三次全部失败，回退 TLS 1.2
    logging.warning('默认 TLS 连续失败，回退到 TLS 1.2')

    for attempt in range(1, 4):
        logging.info(f'TLS 1.2 请求，第 {attempt}/3 次')

        try:
            with requests.Session() as session:
                session.mount('https://', TLS12Adapter())
                return do_request(session)

        except requests.exceptions.RequestException as e:
            last_error = e

        if attempt < 3:
            time.sleep(2)

    raise last_error


def scrape():
    init_config()

    try:
        response = request_page()

        set_cookies = response.raw.headers.getlist('Set-Cookie')

        if set_cookies:
            new_cookies, expires = parse_set_cookie(set_cookies)
            update_cookie(new_cookies, expires)
        else:
            logging.info('未检测到 Set-Cookie，说明当前 Cookie 有效，无需更新。')

        soup = BeautifulSoup(response.text, 'html.parser')
        event_pane = soup.find('div', id='eventpane')

        if not event_pane:
            msg = '没有事件，已经签到了！'
            logging.info(msg)
            send_notify('签到结果', msg)
            return msg

        event_text = event_pane.get_text(
            separator=' ',
            strip=True
        ).lower()

        if 'encounter' in event_text:
            msg = (
                '出现 Random Encounter！'
                '请手动前往处理，或者等待这一随机事件结束！'
            )

            logging.info('出现 Random Encounter！')
            send_notify('签到结果', msg)
            return 'Random Encounter'

        text_lines = [
            p.get_text(strip=True)
            for p in event_pane.find_all('p')
        ]

        if text_lines:
            result = '签到成功！\n' + '\n'.join(text_lines)
            logging.info(result)
            send_notify('签到结果', result)
            return text_lines

    except requests.exceptions.RequestException as e:
        msg = f'请求最终失败: {e}'
        logging.error(msg)
        send_notify('请求错误', msg)
        raise

    except Exception as e:
        msg = f'程序错误: {e}'
        logging.error(msg)
        send_notify('程序错误', msg)
        raise


if __name__ == '__main__':
    scrape()