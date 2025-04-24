# 建议设置每天凌晨自动运行
'''
new Env('E-Hentai 自动签到')
1 0 * * * autosignin.py
'''

import logging
import os
import requests
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

def init_cookie():
    try:
        cookie = os.getenv('E_COOKIE')
        if cookie:
            headers['Cookie'] = cookie
            logging.info(f'使用Cookie: {cookie}')
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

def scrape():
    init_proxy()
    init_cookie()
    init_UserAgent()
    try:
        response = requests.get('https://e-hentai.org/news.php', headers=headers, proxies=proxies, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        event_pane = soup.find('div', id='eventpane')

        if event_pane:
            text_lines = [p.get_text() for p in event_pane.find_all('p')]
            logging.info('签到成功！')
            for line in text_lines:
                logging.info(line)
            send_notify('签到结果', '签到成功！\n' + '\n'.join(text_lines))
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
