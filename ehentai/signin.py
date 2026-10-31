"""访问 E-Hentai 新闻页，处理签到结果、Cookie 和通知。"""
import http.cookies
import json
import logging
import os
import time

import requests
from bs4 import BeautifulSoup

import notify
from .config import read_env, save_cookie

URL = 'https://e-hentai.org/news.php'
headers = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;q=0.9,'
        'image/avif,image/webp,image/apng,*/*;q=0.8,'
        'application/signed-exchange;v=b3;q=0.7'
    ),
    'Upgrade-Insecure-Requests': '1',
    'Cookie': '',
}
proxies = {}
notification_config = {}
NOTIFY_KEYS = frozenset(notify.push_config)
COOKIE_FIELDS = ('ipb_member_id', 'ipb_pass_hash', 'sk', 'hath_perks', 'nw', 'event')


def send_notify(title, content):
    """通知失败只记录错误，不中断签到。"""
    if not notification_config:
        return
    try:
        notify.send(f'Ehentai SignIn - {title}', content,
                    ignore_default_config=True, **notification_config)
    except Exception as e:
        logging.error(f'发送通知失败：{e}')


def mask_cookie(cookie):
    """隐藏日志中的 Cookie 值。"""
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



def parse_notify_config(raw_notify):
    """解析 Notify JSON，并校验字段是否来自通知模块。"""
    if not raw_notify:
        return {}
    try:
        config = json.loads(raw_notify)
    except json.JSONDecodeError as exc:
        raise ValueError('Notify 必须是有效的 JSON 对象。') from exc
    if not isinstance(config, dict):
        raise ValueError('Notify 必须是 JSON 对象。')
    unknown = set(config) - NOTIFY_KEYS
    if unknown:
        raise ValueError(f'Notify 包含未知字段: {", ".join(sorted(unknown))}')
    if any(not isinstance(value, (str, int, float, bool)) for value in config.values()):
        raise ValueError('Notify 字段的值必须是字符串、数字或布尔值。')
    if not config:
        return {}
    config = {'HITOKOTO': 'false', **config}
    if isinstance(config['HITOKOTO'], bool):
        config['HITOKOTO'] = str(config['HITOKOTO']).lower()
    return config


def init_config():
    """每次签到前重新读取配置，供请求和通知使用。"""
    global notification_config
    # .env 优先，确保上次持久化的 Cookie 在下次运行时生效。
    values = {key: os.getenv(key, '') for key in ('E_PROXY', 'E_COOKIE', 'E_USER_AGENT', 'Notify')}
    values.update(read_env())
    proxy = values.get('E_PROXY', '')
    cookie = values.get('E_COOKIE', '')
    user_agent = values.get('E_USER_AGENT', '')
    raw_notify = values.get('Notify', '')

    if not cookie:
        raise ValueError('请在 .env 或环境变量中设置 E_COOKIE。')
    proxies.clear()
    if proxy:
        proxies.update(http=proxy, https=proxy)
        logging.info('已配置代理。')
    headers['Cookie'] = cookie
    logging.info(f'使用 Cookie: {mask_cookie(cookie)}')
    if user_agent:
        headers['User-Agent'] = user_agent

    notification_config = {}
    notification_config = parse_notify_config(raw_notify)
    os.environ['E_COOKIE'] = cookie


def parse_set_cookie(raw_headers):
    """提取响应中的 Cookie 值与到期时间。"""
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
    """合并受支持的 Cookie 字段，并在变化时写回 .env。"""
    old_cookie = os.getenv('E_COOKIE', '')
    current = {}

    for item in old_cookie.split(';'):
        if '=' in item:
            key, value = item.strip().split('=', 1)
            current[key] = value

    updated = False

    for field in COOKIE_FIELDS:
        if field in new_cookies and current.get(field) != new_cookies[field]:
            current[field] = new_cookies[field]
            updated = True

    if not updated:
        logging.info('本地 Cookie 是最新的，无需更新。')
        return

    new_cookie = '; '.join(f'{k}={v}' for k, v in current.items())
    save_cookie(new_cookie)
    os.environ['E_COOKIE'] = new_cookie
    headers['Cookie'] = new_cookie

    logging.info(f'已更新 .env 中的 E_COOKIE：{mask_cookie(new_cookie)}')

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
    """使用默认 TLS 设置请求，失败后最多重试两次。"""
    last_error = None
    for attempt in range(1, 4):
        logging.info(f'请求页面，第 {attempt}/3 次')
        try:
            return do_request()
        except requests.exceptions.RequestException as exc:
            last_error = exc
        if attempt < 3:
            time.sleep(2)
    raise last_error


def scrape():
    """执行一次签到并发送结果通知。"""
    init_config()

    try:
        response = request_page()

        set_cookies = response.raw.headers.getlist('Set-Cookie')

        if set_cookies:
            new_cookies, expires = parse_set_cookie(set_cookies)
            update_cookie(new_cookies, expires)
        else:
            logging.info('未检测到 Set-Cookie，说明当前 Cookie 有效，无需更新。')

        # news.php 的 eventpane 包含奖励或 Random Encounter。
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
