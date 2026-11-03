import os
from unittest.mock import Mock, patch

import pytest
import schedule

import main
from ehentai import config


@pytest.mark.parametrize(('env_value', 'file_values', 'expected'), [
    (None, {}, ('00:30', '06:30', '12:30', '18:30')),
    ('01:15', {'E_SCHEDULE': ' 08:00, 20:30 '}, ('08:00', '20:30')),
    ('01:15', {'E_SCHEDULE': ''}, ('00:30', '06:30', '12:30', '18:30')),
    ('01:15', {}, ('01:15',)),
    (None, {'E_SCHEDULE': '00:30,6:30,12:30,18:30'}, ('00:30', '06:30', '12:30', '18:30')),
    (None, {'E_SCHEDULE': '00:30,6:30,11:11,12:30,18:30'}, ('00:30', '06:30', '11:11', '12:30', '18:30')),
    (None, {'E_SCHEDULE': '6:30,06:30,12:30,6:30'}, ('06:30', '12:30')),
])
def test_defaults_and_custom_times(env_value, file_values, expected, monkeypatch):
    monkeypatch.setattr(config, 'read_env', lambda: file_values)
    env = {} if env_value is None else {'E_SCHEDULE': env_value}
    with patch.dict(os.environ, env, clear=True):
        assert config.scheduled_times() == expected


@pytest.mark.parametrize('value', ['24:00', '12:60', '08:00,', '12:30,6:30', '6:30,12:30,11:11'])
def test_invalid_times_are_rejected(value, monkeypatch):
    monkeypatch.setattr(config, 'read_env', lambda: {'E_SCHEDULE': value})
    with pytest.raises(ValueError, match='E_SCHEDULE'):
        config.scheduled_times()


def test_startup_signin_precedes_scheduling(monkeypatch):
    events = []
    scheduler = schedule.Scheduler()
    monkeypatch.setattr(main, 'scheduled_times', lambda: ('00:30',))
    monkeypatch.setattr(main, 'init_config', Mock())
    monkeypatch.setattr(main, 'scrape', lambda: events.append('signin'))
    monkeypatch.setattr(main.schedule, 'Scheduler', lambda: (events.append('schedule'), scheduler)[1])
    monkeypatch.setattr(main.time, 'sleep', Mock(side_effect=KeyboardInterrupt))
    with pytest.raises(KeyboardInterrupt):
        main.run_scheduler()
    assert events == ['signin', 'schedule']
    assert len(scheduler.jobs) == 1


def test_once_mode(monkeypatch):
    scrape = Mock()
    run_scheduler = Mock()
    monkeypatch.setattr('sys.argv', ['main.py', '--once'])
    monkeypatch.setattr(main, 'scrape', scrape)
    monkeypatch.setattr(main, 'configure_file_logging', Mock())
    monkeypatch.setattr(main, 'run_scheduler', run_scheduler)
    main.main()
    scrape.assert_called_once_with()
    run_scheduler.assert_not_called()
