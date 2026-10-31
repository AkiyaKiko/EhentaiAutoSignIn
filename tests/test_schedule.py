import datetime
import os
import unittest
from unittest.mock import Mock, patch

import schedule

import main
from ehentai import config


class ScheduleTests(unittest.TestCase):
    def test_defaults_and_custom_times(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(config, 'read_env', return_value={}):
            self.assertEqual(config.scheduled_times(), ('00:30', '12:30'))
        with patch.dict(os.environ, {'E_SCHEDULE': '01:15'}, clear=True), patch.object(
            config, 'read_env', return_value={'E_SCHEDULE': ' 08:00, 20:30 '}
        ):
            self.assertEqual(config.scheduled_times(), ('08:00', '20:30'))
        with patch.dict(os.environ, {'E_SCHEDULE': '01:15'}, clear=True), patch.object(
            config, 'read_env', return_value={'E_SCHEDULE': ''}
        ):
            self.assertEqual(config.scheduled_times(), ('00:30', '12:30'))

    def test_invalid_times_are_rejected(self):
        for value in ('24:00', '1:30', '12:60', '08:00,', '08:00,08:00'):
            with self.subTest(value=value), patch.object(config, 'read_env', return_value={'E_SCHEDULE': value}):
                with self.assertRaisesRegex(ValueError, 'E_SCHEDULE'):
                    config.scheduled_times()

    def test_scheduler_runs_due_jobs_after_failure(self):
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
        with patch.object(main, 'scheduled_times', return_value=('00:30', '12:30')), \
             patch.object(main, 'init_config'), \
             patch.object(main.schedule, 'Scheduler', return_value=scheduler), \
             patch.object(main, 'scrape', scrape), \
             patch.object(main.time, 'sleep', side_effect=KeyboardInterrupt), \
             self.assertLogs(level='ERROR'):
            main.run_scheduler()
        self.assertEqual(scrape.call_count, 3)
        self.assertEqual(len(scheduler.jobs), 2)
        self.assertTrue(all(job.next_run > datetime.datetime.now() for job in scheduler.jobs))

    def test_startup_signin_precedes_scheduling(self):
        events = []
        scheduler = schedule.Scheduler()
        with patch.object(main, 'scheduled_times', return_value=('00:30',)), \
             patch.object(main, 'init_config'), \
             patch.object(main, 'scrape', side_effect=lambda: events.append('signin')), \
             patch.object(main.schedule, 'Scheduler', side_effect=lambda: (events.append('schedule'), scheduler)[1]), \
             patch.object(main.time, 'sleep', side_effect=KeyboardInterrupt):
            main.run_scheduler()
        self.assertEqual(events, ['signin', 'schedule'])
        self.assertEqual(len(scheduler.jobs), 1)

    def test_once_mode(self):
        with patch('sys.argv', ['main.py', '--once']), patch.object(main, 'scrape') as scrape, \
             patch.object(main, 'configure_file_logging'), patch.object(main, 'run_scheduler') as run_scheduler:
            main.main()
        scrape.assert_called_once_with()
        run_scheduler.assert_not_called()


if __name__ == '__main__':
    unittest.main()
