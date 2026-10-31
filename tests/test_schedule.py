import datetime
import os
from unittest.mock import Mock, patch

import pytest
import schedule

import main
from ehentai import config


@pytest.mark.parametrize(('env_value', 'file_values', 'expected'), [
    (None, {}, ('00:30', '12:30')),
    ('01:15', {'E_SCHEDULE': ' 08:00, 20:30 '}, ('08:00', '20:30')),
    ('01:15', {'E_SCHEDULE': ''}, ('00:30', '12:30')),
    ('01:15', {}, ('01:15',)),
])
def test_defaults_and_custom_times(env_value, file_values, expected, monkeypatch):
    monkeypatch.setattr(config, 'read_env', lambda: file_values)
    env = {} if env_value is None else {'E_SCHEDULE': env_value}
    with patch.dict(os.environ, env, clear=True):
        assert config.scheduled_times() == expected


@pytest.mark.parametrize('value', ['24:00', '1:30', '12:60', '08:00,', '08:00,08:00'])
def test_invalid_times_are_rejected(value, monkeypatch):
    monkeypatch.setattr(config, 'read_env', lambda: {'E_SCHEDULE': value})
    with pytest.raises(ValueError, match='E_SCHEDULE'):
        config.scheduled_times()


def test_scheduler_runs_due_jobs_after_failure(monkeypatch, caplog):
    scheduler = schedule.Scheduler()
    real_every = scheduler.every

    def every(*args, **kwargs):
        job = real_every(*args, **kwargs)
        real_do = job.do

        def register(*do_args, **do_kwargs):
            registered = real_do(*do_args, **do_kwargs)
            registered.next_run = datetime.datetime.now() - datetime.timedelta(seconds=1)
            return registered

        job.do = register
        return job

    scheduler.every = every
    scrape = Mock(side_effect=[RuntimeError('simulated failure'), None, None])
    monkeypatch.setattr(main, 'scheduled_times', lambda: ('00:30', '12:30'))
    monkeypatch.setattr(main, 'init_config', Mock())
    monkeypatch.setattr(main.schedule, 'Scheduler', lambda: scheduler)
    monkeypatch.setattr(main, 'scrape', scrape)
    monkeypatch.setattr(main.time, 'sleep', Mock(side_effect=KeyboardInterrupt))
    with caplog.at_level('ERROR'):
        main.run_scheduler()
    assert '本次定时签到失败' in caplog.text
    assert scrape.call_count == 3
    assert len(scheduler.jobs) == 2
    assert all(job.next_run > datetime.datetime.now() for job in scheduler.jobs)


def test_startup_signin_precedes_scheduling(monkeypatch):
    events = []
    scheduler = schedule.Scheduler()
    monkeypatch.setattr(main, 'scheduled_times', lambda: ('00:30',))
    monkeypatch.setattr(main, 'init_config', Mock())
    monkeypatch.setattr(main, 'scrape', lambda: events.append('signin'))
    monkeypatch.setattr(main.schedule, 'Scheduler', lambda: (events.append('schedule'), scheduler)[1])
    monkeypatch.setattr(main.time, 'sleep', Mock(side_effect=KeyboardInterrupt))
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
