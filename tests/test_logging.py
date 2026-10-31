import logging
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from ehentai import log_setup


class FileLoggingTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {}, clear=True), \
             patch.object(log_setup, 'read_env', return_value={}), \
             patch.object(log_setup, 'ENV_PATH', Path(directory) / '.env'):
            log_setup.configure_file_logging()
            self.assertFalse((Path(directory) / 'logs').exists())

    def test_configuration_and_output(self):
        root = logging.getLogger()
        before = set(root.handlers)
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {}, clear=True), \
             patch.object(log_setup, 'read_env', return_value={
                 'LOG_ENABLED': 'true', 'LOG_DIR': 'custom',
                 'LOG_MAX_MB': '2', 'LOG_RETENTION_DAYS': '7',
             }), patch.object(log_setup, 'ENV_PATH', Path(directory) / '.env'):
            try:
                log_setup.configure_file_logging()
                handler = next(iter(set(root.handlers) - before))
                self.assertEqual(handler.maxBytes, 2 * 1024 * 1024)
                self.assertEqual(handler.retention_seconds, 7 * 86400)
                logging.info('test log message')
                self.assertIn('test log message', (Path(directory) / 'custom' / 'ehentai.log').read_text(encoding='utf-8'))
            finally:
                for handler in set(root.handlers) - before:
                    root.removeHandler(handler)
                    handler.close()

    def test_rotation_and_expiration_only_delete_owned_backups(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            path = folder / 'ehentai.log'
            old = folder / 'ehentai.log.1'
            other = folder / 'other.log.1'
            old.write_text('old', encoding='utf-8')
            other.write_text('keep', encoding='utf-8')
            timestamp = time.time() - 2 * 86400
            os.utime(old, (timestamp, timestamp))
            os.utime(other, (timestamp, timestamp))
            handler = log_setup.RetainedRotatingFileHandler(path, max_bytes=50, retention_days=1)
            logger = logging.getLogger('test.file.rotation')
            logger.setLevel(logging.INFO)
            logger.addHandler(handler)
            logger.propagate = False
            try:
                self.assertFalse(old.exists())
                self.assertTrue(other.exists())
                logger.info('first message %s', 'x' * 20)
                logger.info('second message %s', 'x' * 20)
                self.assertTrue(old.exists())
                handler.next_rollover = 0
                logger.info('daily rotation')
                self.assertTrue((folder / 'ehentai.log.2').exists())
            finally:
                logger.removeHandler(handler)
                handler.close()

    def test_invalid_enabled_configuration(self):
        for config in ({'LOG_ENABLED': 'maybe'}, {'LOG_ENABLED': 'true', 'LOG_MAX_MB': '0'},
                       {'LOG_ENABLED': 'true', 'LOG_RETENTION_DAYS': '-1'}):
            with self.subTest(config=config), patch.dict(os.environ, {}, clear=True), \
                 patch.object(log_setup, 'read_env', return_value=config):
                with self.assertRaises(ValueError):
                    log_setup.configure_file_logging()


if __name__ == '__main__':
    unittest.main()
