"""命令行入口：配置日志，执行一次签到或启动定时任务。"""
import argparse
import logging
import time

import schedule

from ehentai.config import scheduled_times
from ehentai.log_setup import LOG_FORMAT, configure_file_logging
from ehentai.signin import init_config, scrape

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


class ArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        """将参数错误交给统一的日志和退出处理。"""
        raise ValueError(message)


def run_scheduler():
    """启动时签到一次，再按配置的时间运行。"""
    times = scheduled_times()
    init_config()  # 启动时检查配置；每次签到时也会重新读取。
    logging.info('定时签到已启动（系统本地时间）：%s', ', '.join(times))
    logging.info('启动后立即执行一次签到。')
    scrape()
    scheduler = schedule.Scheduler()
    for scheduled_time in times:
        scheduler.every().day.at(scheduled_time).do(scrape)
    logging.info('下次签到时间：%s', scheduler.next_run)
    while True:
        scheduler.run_pending()
        time.sleep(1)


def main():
    parser = ArgumentParser(description='E-Hentai 自动签到')
    parser.add_argument('--once', action='store_true', help='立即执行一次签到后退出')
    try:
        configure_file_logging()
        args = parser.parse_args()
        if args.once:
            scrape()
        else:
            run_scheduler()
    except KeyboardInterrupt:
        logging.info('程序已停止。')
        return 0
    except Exception as exc:
        logging.error('程序运行失败：%s: %s', type(exc).__name__, exc)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
