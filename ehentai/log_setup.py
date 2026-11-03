"""配置控制台日志和可选的本地轮转日志。"""
from datetime import datetime, time as datetime_time, timedelta
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import time

from .config import ENV_PATH, read_env

LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'


class RetainedRotatingFileHandler(RotatingFileHandler):
    """按大小和时间轮转，并删除过期的本程序日志备份。"""

    def __init__(self, filename, max_bytes, retention_days):
        super().__init__(filename, maxBytes=max_bytes, backupCount=30, encoding='utf-8')
        self.retention_seconds = retention_days * 86400
        self.next_rollover = self.next_midnight()
        if (os.path.exists(self.baseFilename) and
                datetime.fromtimestamp(os.path.getmtime(self.baseFilename)).date() < datetime.now().date()):
            self.next_rollover = 0
        self.next_cleanup = 0
        self.cleanup_expired()

    @staticmethod
    def next_midnight():
        tomorrow = datetime.now().date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime_time.min).timestamp()

    def cleanup_expired(self):
        """只清理本程序生成且已过期的轮转文件。"""
        cutoff = time.time() - self.retention_seconds
        base = Path(self.baseFilename)
        for index in range(1, self.backupCount + 1):
            backup = base.with_name(f'{base.name}.{index}')
            try:
                if not backup.is_symlink() and backup.is_file() and backup.stat().st_mtime < cutoff:
                    backup.unlink()
            except FileNotFoundError:
                pass
        self.next_cleanup = time.time() + 3600

    def shouldRollover(self, record):
        # 首次跨日写入时轮转；其余情况按文件大小判断。
        if time.time() >= self.next_rollover and os.path.exists(self.baseFilename):
            if os.path.getsize(self.baseFilename) > 0:
                return True
        return super().shouldRollover(record)

    def doRollover(self):
        super().doRollover()
        self.next_rollover = self.next_midnight()
        self.cleanup_expired()

    def emit(self, record):
        if time.time() >= self.next_cleanup:
            try:
                self.cleanup_expired()
            except OSError:
                self.handleError(record)
        super().emit(record)


def configure_file_logging():
    """按 .env 配置启用文件日志；默认只输出到控制台。"""
    keys = ('LOG_ENABLED', 'LOG_DIR', 'LOG_MAX_MB', 'LOG_RETENTION_DAYS')
    values = {key: os.getenv(key, '') for key in keys}
    errors = []
    # 只解析日志字段，使其他配置行出错时仍能记录启动错误。
    for key in keys:
        try:
            values.update(read_env(keys={key}))
        except ValueError as exc:
            errors.append(exc)
            values[key] = ''
    enabled = values['LOG_ENABLED'].strip().lower()
    if enabled in ('', 'false', '0', 'no', 'off'):
        if errors:
            raise errors[0]
        return
    if enabled not in ('true', '1', 'yes', 'on'):
        raise ValueError('LOG_ENABLED 必须为 true 或 false。')

    def positive_integer(key, default):
        value = values[key].strip() or str(default)
        if not re.fullmatch(r'[0-9]+', value) or int(value) <= 0:
            errors.append(ValueError(f'{key} 必须是正整数。'))
            return default
        return int(value)

    max_mb = positive_integer('LOG_MAX_MB', 5)
    retention_days = positive_integer('LOG_RETENTION_DAYS', 30)
    default_directory = ENV_PATH.parent / 'logs'
    try:
        directory = Path(values['LOG_DIR'].strip() or 'logs').expanduser()
        if not directory.is_absolute():
            directory = ENV_PATH.parent / directory
        directory.mkdir(parents=True, exist_ok=True)
        handler = RetainedRotatingFileHandler(directory / 'ehentai.log', max_mb * 1024 * 1024, retention_days)
    except (OSError, ValueError) as exc:
        # 配置目录不可用时，尽量在默认位置记录启动错误。
        errors.append(exc)
        directory = default_directory
        directory.mkdir(parents=True, exist_ok=True)
        handler = RetainedRotatingFileHandler(directory / 'ehentai.log', max_mb * 1024 * 1024, retention_days)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logging.getLogger().addHandler(handler)
    logging.info('本地文件日志已启用：%s', directory / 'ehentai.log')
    if errors:
        raise errors[0]
