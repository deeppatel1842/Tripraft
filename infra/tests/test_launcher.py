# Purpose: Regression tests for launcher, including success and failure behavior.
"""Launcher regressions for data/configuration preservation and process ownership."""
import json
import socket
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import start


class LauncherTests(unittest.TestCase):
    def setUp(self):
        scratch = start.ROOT / '.tripraft/test-temp'
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.root = Path(self.temp.name)
        self.api = self.root / 'services/api'
        self.api.mkdir(parents=True)
        self.patcher = mock.patch.multiple(start, ROOT=self.root, API=self.api,
                                          LOCAL=self.root / '.tripraft', VENV=self.root / '.venv',
                                          PNPM_SCRIPT=self.root / '.tripraft/pnpm.cjs')
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.temp.cleanup()

    def test_first_setup_preserves_legacy_data_and_uses_random_secrets(self):
        (self.api / '.env.example').write_text('SECRET_KEY=placeholder\nJWT_SECRET_KEY=placeholder\nREDIS_URL=redis://localhost\nFLASK_HOST=0.0.0.0\n')
        legacy = self.root / 'data/runtime/tripraft.db'
        legacy.parent.mkdir(parents=True)
        legacy.write_bytes(b'legacy data must remain unchanged')
        start.configure_native()
        values = dict(line.split('=', 1) for line in (self.api / '.env').read_text().splitlines() if '=' in line and not line.startswith('#'))
        self.assertEqual(legacy.read_bytes(), b'legacy data must remain unchanged')
        self.assertIn('/data/runtime/dev/tripraft.db', values['DATABASE_URL'])
        self.assertNotEqual(values['SECRET_KEY'], values['JWT_SECRET_KEY'])
        self.assertGreaterEqual(len(values['SECRET_KEY']), 48)
        self.assertEqual(values['REDIS_URL'], '')
        self.assertEqual(values['FLASK_HOST'], '127.0.0.1')

    def test_existing_configuration_is_never_overwritten(self):
        target = self.api / '.env'
        target.write_bytes(b'DATABASE_URL=existing-account-data\nSECRET_KEY=keep-me\n')
        before = target.read_bytes()
        start.configure_native()
        self.assertEqual(target.read_bytes(), before)

    def test_occupied_port_is_rejected_without_stopping_its_owner(self):
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            port = listener.getsockname()[1]
            listener.listen()
            with self.assertRaisesRegex(RuntimeError, 'already in use'):
                start.require_free_ports([port])
            self.assertEqual(listener.getsockname()[1], port)

    def test_exited_child_is_not_killed_by_a_reused_pid(self):
        process = mock.Mock()
        process.poll.return_value = 0
        with mock.patch.object(start.subprocess, 'run') as run:
            start.stop_child(process)
        run.assert_not_called()
        process.kill.assert_not_called()

    def test_startup_failure_cleans_only_the_created_child(self):
        child = mock.Mock()
        with mock.patch.object(start, 'require_free_ports'), mock.patch.object(start, 'run'), \
                mock.patch.object(start, 'wait_ready', side_effect=RuntimeError('startup failed')), \
                mock.patch.object(start.subprocess, 'Popen', return_value=child), \
                mock.patch.object(start, 'stop_child') as stop:
            with self.assertRaisesRegex(RuntimeError, 'startup failed'):
                start.start('node', docker=False, smoke=True, no_browser=True)
        stop.assert_called_once_with(child)

    def test_saved_setup_is_invalid_when_dependencies_are_removed(self):
        for name in ['pnpm-lock.yaml', 'services/api/requirements.txt', 'services/api/requirements-dev.txt']:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('dependency manifest')
        saved = {'native': start.fingerprint(False)}
        self.assertFalse(start.setup_ready(saved, False))


if __name__ == '__main__':
    unittest.main()
