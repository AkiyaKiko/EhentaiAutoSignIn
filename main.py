"""命令行入口：配置日志，执行一次签到或启动定时任务。"""
import argparse
import logging
import time

import schedule

from ehentai.config import scheduled_times
from ehentai.log_setup import LOG_FORMAT, configure_file_logging
from ehentai.signin import init_config, scrape

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def run_scheduled_signin():
    """单次签到失败时继续等待下一次任务。"""
    try:
        scrape()
    except Exception:
        logging.exception('本次定时签到失败，将继续等待下一次任务。')


def run_scheduler():
    """启动时签到一次，再按配置的时间运行。"""
    times = scheduled_times()
    init_config()  # 启动时检查配置；每次签到时也会重新读取。
    logging.info('定时签到已启动（系统本地时间）：%s', ', '.join(times))
    try:
        logging.info('启动后立即执行一次签到。')
        run_scheduled_signin()
        scheduler = schedule.Scheduler()
        for scheduled_time in times:
            scheduler.every().day.at(scheduled_time).do(run_scheduled_signin)
        logging.info('下次签到时间：%s', scheduler.next_run)
        while True:
            scheduler.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info('定时签到已停止。')


def main():
    parser = argparse.ArgumentParser(description='E-Hentai 自动签到')
    parser.add_argument('--once', action='store_true', help='立即执行一次签到后退出')
    args = parser.parse_args()
    configure_file_logging()
    if args.once:
        scrape()
    else:
        run_scheduler()


if __name__ == '__main__':
    main()
