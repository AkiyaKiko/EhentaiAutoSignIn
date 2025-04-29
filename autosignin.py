# 建议设置每天凌晨自动运行
'''
new Env('E-Hentai 自动签到')
1 */3 * * * autosignin.py
'''

import logging
import os
import requests
import http.cookies
from bs4 import BeautifulSoup
import urllib3
import notify # 来自青龙面板默认的通知模块，不需要安装依赖

# 禁用 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Upgrade-Insecure-Requests': '1',
    'Cookie': ''
}

proxies = {
    'http': None,
    'https': None
}

def send_notify(title, content):
    try:
        notify.send(f"Ehentai SignIn - {title}", content)
    except Exception as e:
        logging.error(f"发送通知失败：{e}")

def init_proxy():
    try:
        proxy = os.getenv('E_PROXY')
        if proxy:
            proxies['http'] = proxy
            proxies['https'] = proxy
            logging.info(f'使用代理: {proxy}')
        else:
            logging.info('未设置代理，将不使用代理。')
    except Exception as e:
        logging.error(f'初始化代理失败: {e}')
        send_notify('初始化失败', f'初始化代理失败: {e}')

def mask_cookie(cookie_str):
    masked_parts = []
    for item in cookie_str.split(';'):
        item = item.strip()
        if '=' in item:
            key, value = item.split('=', 1)
            if len(value) > 8:
                masked_value = value[:3] + '*' * (len(value) - 6) + value[-3:]
            elif len(value) > 0:
                masked_value = value[0] + '*' * (len(value) - 1)
            else:
                masked_value = ''
            masked_parts.append(f"{key}={masked_value}")
        else:
            masked_parts.append(item)
    return '; '.join(masked_parts)

def init_cookie():
    try:
        cookie = os.getenv('E_COOKIE')
        if cookie:
            headers['Cookie'] = cookie
            masked_cookie = mask_cookie(cookie)
            logging.info(f'使用Cookie: {masked_cookie}')
        else:
            logging.info('未设置Cookie，将不发送Cookie。')
    except Exception as e:
        logging.error(f'初始化Cookie失败: {e}')
        send_notify('初始化失败', f'初始化Cookie失败: {e}')

def init_UserAgent():
    try:
        user_agent = os.getenv('E_USER_AGENT')
        if user_agent:
            headers['User-Agent'] = user_agent
            logging.info(f'使用User-Agent: {user_agent}')
        else:
            logging.info('未设置User-Agent，将使用默认 User-Agent。')
    except Exception as e:
        logging.error(f'初始化User-Agent失败: {e}')
        send_notify('初始化失败', f'初始化User-Agent失败: {e}')

def parse_set_cookie(set_cookie_headers):
    cookies = {}
    expires_info = []

    if not isinstance(set_cookie_headers, list):
        set_cookie_headers = [set_cookie_headers]

    for raw_cookie in set_cookie_headers:
        morsel = http.cookies.SimpleCookie()
        morsel.load(raw_cookie)
        for key, value in morsel.items():
            cookies[key] = value.value
            if 'expires' in value:
                expires_info.append((key, value['expires']))

    return cookies, expires_info

def compare_and_update_cookie_env(new_cookies, expires_info):
    cookie_fields = ['ipb_member_id', 'ipb_pass_hash', 'sk', 'hath_perks', 'nw', 'event']
    old_cookie = os.getenv('E_COOKIE', '')

    # 解析旧cookie为字典
    old_cookie_dict = {}
    for item in old_cookie.split(';'):
        if '=' in item:
            k, v = item.strip().split('=', 1)
            old_cookie_dict[k] = v

    updated = False
    updated_cookie_dict = old_cookie_dict.copy()

    for field in cookie_fields:
        if field in new_cookies:
            if old_cookie_dict.get(field) != new_cookies[field]:
                updated_cookie_dict[field] = new_cookies[field]
                updated = True

    if updated:
        # 组装新cookie并写入 os.environ
        new_cookie_str = '; '.join([f'{k}={v}' for k, v in updated_cookie_dict.items()])
        os.environ['E_COOKIE'] = new_cookie_str
        logging.info(f'已更新 os.environ 中的 E_COOKIE：{new_cookie_str}')

        # 发送过期时间通知
        notify_lines = [f"{k} 过期时间: {v}" for k, v in expires_info if k in updated_cookie_dict]
        if notify_lines:
            send_notify("Cookie 更新提醒", '\n'.join(notify_lines))
    else:
        logging.info('本地 Cookie 是最新的，无需更新。')

def scrape():
    init_proxy()
    init_cookie()
    init_UserAgent()
    try:
        response = requests.get('https://e-hentai.org/news.php', headers=headers, proxies=proxies, verify=False)
        response.raise_for_status()

        # 检查 Set-Cookie 并处理
        set_cookie_headers = response.headers.get_all('Set-Cookie') if hasattr(response.headers, 'get_all') else response.headers.get('Set-Cookie')
        if set_cookie_headers:
            new_cookies, expires_info = parse_set_cookie(set_cookie_headers)
            compare_and_update_cookie_env(new_cookies, expires_info)
        else:
            logging.info("未检测到 Set-Cookie，说明当前 Cookie 有效，无需更新。")

        soup = BeautifulSoup(response.text, 'html.parser')
        event_pane = soup.find('div', id='eventpane')

        if event_pane:
            text_lines = [p.get_text() for p in event_pane.find_all('p')]
            for line in text_lines:
                if 'encounter' in line.lower():
                    logging.info('出现 Random Encounter！')
                    send_notify('签到结果', '出现 Random Encounter！')

            logging.info('签到成功！'.join(text_lines))
            send_notify('签到结果', '签到成功！'.join(text_lines))
            return text_lines
        else:
            logging.info('已经签到了！')
            send_notify('签到结果', '已经签到了！')
            return '没有找到目标信息'

    except requests.exceptions.RequestException as e:
        msg = f'发生请求错误: {e}'
        logging.error(msg)
        send_notify('请求错误', msg)
        return msg
    except Exception as e:
        msg = f'发生其他错误: {e}'
        logging.error(msg)
        send_notify('程序错误', msg)
        return msg

if __name__ == "__main__":
    scrape()
