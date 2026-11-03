import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import Mock

import pytest

import main
from ehentai import config, log_setup, signin


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    env_path = tmp_path / '.env'
    read_env = config.read_env
    for module in (config, log_setup, signin):
        monkeypatch.setattr(module, 'read_env', lambda **kwargs: read_env(env_path, **kwargs))
    monkeypatch.setattr(log_setup, 'ENV_PATH', env_path)
    for key in ('E_COOKIE', 'E_SCHEDULE', 'LOG_ENABLED', 'LOG_DIR', 'LOG_MAX_MB', 'LOG_RETENTION_DAYS'):
        monkeypatch.delenv(key, raising=False)
    root = logging.getLogger()
    before = set(root.handlers)
    yield env_path
    for handler in set(root.handlers) - before:
        root.removeHandler(handler)
        handler.close()


@pytest.mark.parametrize(('content', 'message'), [
    ("E_SCHEDULE='12:30,6:30'\n", 'E_SCHEDULE 时间必须按从早到晚'),
    ("E_COOKIE='unterminated\n", '.env 第 2 行的单引号未闭合'),
    ("E_COOKIE=''\n", '请在 .env 或环境变量中设置 E_COOKIE'),
    ("LOG_MAX_MB='0'\n", 'LOG_MAX_MB 必须是正整数'),
    ("LOG_MAX_MB='unterminated\n", '.env 第 2 行的单引号未闭合'),
])
def test_startup_error_is_recorded_and_exits_cleanly(isolated_config, monkeypatch, caplog, content, message):
    isolated_config.write_text("LOG_ENABLED='true'\n" + content, encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['main.py'])
    with caplog.at_level(logging.INFO):
        assert main.main() == 1
    log = (isolated_config.parent / 'logs' / 'ehentai.log').read_text(encoding='utf-8')
    assert message in log
    assert message in caplog.text
    assert 'Traceback' not in caplog.text


@pytest.mark.parametrize('args', [[], ['--once']])
def test_signin_error_exits_cleanly_and_is_logged(isolated_config, monkeypatch, caplog, args):
    isolated_config.write_text("LOG_ENABLED='true'\nE_COOKIE='event=111'\n", encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['main.py', *args])
    monkeypatch.setattr(main, 'scrape', Mock(side_effect=RuntimeError('simulated sign-in failure')))
    with caplog.at_level(logging.INFO):
        assert main.main() == 1
    log = (isolated_config.parent / 'logs' / 'ehentai.log').read_text(encoding='utf-8')
    assert 'simulated sign-in failure' in log
    assert 'Traceback' not in caplog.text


def test_unavailable_log_directory_falls_back(isolated_config, monkeypatch, caplog):
    invalid_directory = isolated_config.parent / 'not-a-directory'
    invalid_directory.write_text('file', encoding='utf-8')
    isolated_config.write_text(
        "LOG_ENABLED='true'\nLOG_DIR='not-a-directory'\n", encoding='utf-8'
    )
    monkeypatch.setattr('sys.argv', ['main.py'])
    with caplog.at_level(logging.INFO):
        assert main.main() == 1
    log = isolated_config.parent / 'logs' / 'ehentai.log'
    assert '程序运行失败' in log.read_text(encoding='utf-8')


def test_invalid_command_line_is_logged(isolated_config, monkeypatch, caplog):
    isolated_config.write_text("LOG_ENABLED='true'\n", encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['main.py', '--invalid'])
    with caplog.at_level(logging.INFO):
        assert main.main() == 1
    log = (isolated_config.parent / 'logs' / 'ehentai.log').read_text(encoding='utf-8')
    assert '--invalid' in log
    assert 'Traceback' not in caplog.text


def test_scheduled_run_error_is_logged_and_exits(isolated_config, monkeypatch, caplog):
    isolated_config.write_text("LOG_ENABLED='true'\nE_COOKIE='event=111'\n", encoding='utf-8')
    monkeypatch.setattr('sys.argv', ['main.py'])
    monkeypatch.setattr(main, 'scrape', Mock())
    scheduler = Mock()
    scheduler.run_pending.side_effect = RuntimeError('scheduled sign-in failure')
    monkeypatch.setattr(main.schedule, 'Scheduler', lambda: scheduler)
    with caplog.at_level(logging.INFO):
        assert main.main() == 1
    assert 'scheduled sign-in failure' in (isolated_config.parent / 'logs' / 'ehentai.log').read_text(encoding='utf-8')
    assert 'Traceback' not in caplog.text


def test_startup_error_exits_with_nonzero_status_without_traceback(tmp_path):
    root = Path(__file__).resolve().parent.parent
    shutil.copy(root / 'main.py', tmp_path)
    shutil.copy(root / 'notify.py', tmp_path)
    shutil.copytree(root / 'ehentai', tmp_path / 'ehentai', ignore=shutil.ignore_patterns('__pycache__'))
    (tmp_path / '.env').write_text(
        "LOG_ENABLED='true'\nE_SCHEDULE='12:30,6:30'\n", encoding='utf-8'
    )
    env = os.environ.copy()
    env['PYTHONUTF8'] = '1'
    result = subprocess.run(
        [sys.executable, str(tmp_path / 'main.py')], cwd=tmp_path,
        env=env, capture_output=True, text=True, encoding='utf-8', timeout=30,
    )
    assert result.returncode == 1
    assert 'E_SCHEDULE' in result.stderr
    assert 'Traceback' not in result.stderr
    assert 'E_SCHEDULE' in (tmp_path / 'logs' / 'ehentai.log').read_text(encoding='utf-8')
