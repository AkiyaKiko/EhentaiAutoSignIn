import logging
import os
import time
from unittest.mock import patch

import pytest

from ehentai import log_setup


def test_disabled_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(log_setup, 'read_env', lambda **kwargs: {})
    monkeypatch.setattr(log_setup, 'ENV_PATH', tmp_path / '.env')
    with patch.dict(os.environ, {}, clear=True):
        log_setup.configure_file_logging()
    assert not (tmp_path / 'logs').exists()


def test_configuration_and_output(tmp_path, monkeypatch, caplog):
    root = logging.getLogger()
    before = set(root.handlers)
    monkeypatch.setattr(log_setup, 'read_env', lambda **kwargs: {
        'LOG_ENABLED': 'true', 'LOG_DIR': 'custom',
        'LOG_MAX_MB': '2', 'LOG_RETENTION_DAYS': '7',
    })
    monkeypatch.setattr(log_setup, 'ENV_PATH', tmp_path / '.env')
    caplog.set_level(logging.INFO)
    try:
        with patch.dict(os.environ, {}, clear=True):
            log_setup.configure_file_logging()
        handler = next(iter(set(root.handlers) - before))
        assert handler.maxBytes == 2 * 1024 * 1024
        assert handler.retention_seconds == 7 * 86400
        logging.info('test log message')
        assert 'test log message' in (tmp_path / 'custom' / 'ehentai.log').read_text(encoding='utf-8')
    finally:
        for handler in set(root.handlers) - before:
            root.removeHandler(handler)
            handler.close()


def test_rotation_and_expiration_only_delete_owned_backups(tmp_path):
    old = tmp_path / 'ehentai.log.1'
    other = tmp_path / 'other.log.1'
    old.write_text('old', encoding='utf-8')
    other.write_text('keep', encoding='utf-8')
    timestamp = time.time() - 2 * 86400
    os.utime(old, (timestamp, timestamp))
    os.utime(other, (timestamp, timestamp))
    handler = log_setup.RetainedRotatingFileHandler(tmp_path / 'ehentai.log', max_bytes=50, retention_days=1)
    logger = logging.getLogger('test.file.rotation')
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
    try:
        assert not old.exists()
        assert other.exists()
        logger.info('first message %s', 'x' * 20)
        logger.info('second message %s', 'x' * 20)
        assert old.exists()
        handler.next_rollover = 0
        logger.info('daily rotation')
        assert (tmp_path / 'ehentai.log.2').exists()
    finally:
        logger.removeHandler(handler)
        handler.close()


@pytest.mark.parametrize('config', [
    {'LOG_ENABLED': 'maybe'},
    {'LOG_ENABLED': 'true', 'LOG_MAX_MB': '0'},
    {'LOG_ENABLED': 'true', 'LOG_RETENTION_DAYS': '-1'},
])
def test_invalid_enabled_configuration(config, monkeypatch, tmp_path):
    root = logging.getLogger()
    before = set(root.handlers)
    monkeypatch.setattr(log_setup, 'ENV_PATH', tmp_path / '.env')
    monkeypatch.setattr(log_setup, 'read_env', lambda **kwargs: config)
    try:
        with patch.dict(os.environ, {}, clear=True), pytest.raises(ValueError):
            log_setup.configure_file_logging()
    finally:
        for handler in set(root.handlers) - before:
            root.removeHandler(handler)
            handler.close()
