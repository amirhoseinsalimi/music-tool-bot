"""Core control authorization, immutable history and handler-gating regressions."""
# pylint: disable=duplicate-code
import asyncio
import io
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from wsgiref.util import setup_testing_defaults

import psycopg2
from pg_support import PostgresFixture

from runtime_controls import ControlsStore, ControlError, bot_settings, feature_gate
from admin_bridge.app import create_app


class ControlsTests(unittest.TestCase):
    """Use temporary control storage and mocked current core membership."""

    def setUp(self):
        translation = patch('runtime_controls.disabled_message',
                            return_value=('This tool is temporarily unavailable. '
                                          'Please try again later.'))
        translation.start()
        self.addCleanup(translation.stop)
        self.directory = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.directory.cleanup)
        fixture = PostgresFixture()
        self.addCleanup(fixture.close)
        self.path = fixture.dsn
        self.store = ControlsStore(self.path)
        self.repo = Mock()
        self.repo.dispatch.return_value = {'telegramId': '42', 'isOwner': True}
        self.app = create_app('s'*32, self.repo, self.store, control_token='w'*32)
        self.command = {'feature': 'cutter', 'enabled': False, 'reason': 'Provider maintenance',
                        'expectedRevision': 0, 'operationId': 'operation-controls-test'}

    def request(self, method='GET', data=None, path='/v1/controls', actor='42', token=None):
        # pylint: disable=too-many-arguments,too-many-positional-arguments
        """Exercise the WSGI boundary with a selectable actor, token and payload."""
        environ = {}
        setup_testing_defaults(environ)
        body = json.dumps(data).encode() if data is not None else b''
        write_token = method == 'POST' and path == '/v1/controls'
        selected_token = token or ('w' * 32 if write_token else 's' * 32)
        environ.update(
            REQUEST_METHOD=method, PATH_INFO=path, HTTP_AUTHORIZATION='Bearer ' + selected_token,
            HTTP_X_ADMIN_TELEGRAM_ID=actor, CONTENT_LENGTH=str(len(body)),
            CONTENT_TYPE='application/json',
        )
        environ['wsgi.input'] = io.BytesIO(body)
        result = []
        content = b''.join(self.app(environ, lambda status, headers: result.append(status)))
        return int(result[0].split()[0]), json.loads(content)

    def test_control_audit_paginates_past_twenty_records(self):
        """Reach the full immutable history with bounded pages."""
        for index in range(27):
            self.store.change('42', {**self.command, 'operationId': 'pagination-control-' +
                              str(index), 'expectedRevision': index, 'enabled': bool(index % 2)})
        self.assertEqual(self.store.audit()['total'], 27)
        self.assertEqual([row['revision']
                         for row in self.store.audit()['items']], list(range(27, 17, -1)))
        last = self.store.audit('999')
        self.assertEqual(last['page'], 3)
        self.assertEqual([row['revision'] for row in last['items']], list(range(7, 0, -1)))
        for value in ('0', '-1', '100001', 'x', None):
            with self.assertRaises(ControlError):
                self.store.audit(value)
        status, body = self.request(path='/v1/controls/audit')
        self.assertEqual(status, 200)
        self.assertEqual(body['pageSize'], 10)
        self.assertEqual(self.request(path='/v1/controls/audit', token='wrong')[0], 401)
        self.assertEqual(self.request('POST', {}, path='/v1/controls/audit')[0], 405)

    def test_health_observation_requires_current_membership(self):
        """Keep observations behind the same current-membership authorization."""
        self.assertEqual(self.request(path='/v1/health', token='wrong')[0], 401)
        status, value = self.request(path='/v1/health')
        self.assertEqual(status, 200)
        self.assertEqual(value['database'], 'reachable')
        self.assertEqual(value['botProcess'], 'not_monitored')
        self.repo.dispatch.assert_called_with('42', '/v1/session', {})
        self.assertNotIn('hostname', value)
        self.assertEqual(self.request('POST', {}, path='/v1/health')[0], 405)

    def test_owner_scope_revision_and_idempotency(self):
        """Reject invalid writes and replay matching commands only once."""
        self.assertEqual(self.request(token='wrong')[0], 401)
        self.assertEqual(self.request('POST', self.command, path='/v1/users')[0], 405)
        self.assertEqual(self.request('POST', self.command, token='s'*32)[0], 401)
        self.assertEqual(self.request('POST', self.command)[0], 200)
        replay = self.request('POST', self.command)
        self.assertFalse(replay[1]['created'])
        self.assertEqual(len(self.store.read()['audit']), 1)
        self.assertEqual(self.request(
            'POST', {**self.command, 'operationId': 'another-operation-control'})[0], 409)
        self.assertEqual(self.request('POST', {**self.command, 'reason': 'different'})[0], 409)
        self.repo.dispatch.return_value['isOwner'] = False
        self.assertFalse(self.request()[1]['canChange'])
        self.assertEqual(self.request('POST', {
            **self.command, 'enabled': True, 'expectedRevision': 1,
            'operationId': 'owner-denied-operation'})[0], 403)
        self.assertEqual(self.store.read()['revision'], 1)

    def test_invalid_payloads_and_audit_are_immutable(self):
        """Validate command fields and prevent rewriting old audit entries."""
        invalid = ({'enabled': 1}, {'feature': 'unknown'}, {'reason': ' '},
                   {'expectedRevision': True}, {'operationId': 'x'})
        for patch_data in invalid:
            with self.assertRaises(ControlError):
                self.store.change('42', {**self.command, **patch_data})
        self.store.change('42', self.command)
        with self.assertRaises(psycopg2.IntegrityError), self.store.connect() as db:
            db.execute('DELETE FROM control_audit')

    def test_bot_gates_read_current_settings_and_standalone_defaults(self):
        """Enforce current settings without requiring controls for standalone bots."""
        with patch.dict(os.environ, {'BOT_CONTROL_DATABASE_URL': ''}):
            self.assertTrue(all(bot_settings().values()))
        self.store.change('42', self.command)
        update = SimpleNamespace(effective_message=SimpleNamespace(reply_text=AsyncMock()))
        called = []

        @feature_gate('cutter')
        async def action(_update, _context):
            called.append(True)
        with patch.dict(os.environ, {'BOT_CONTROL_DATABASE_URL': str(self.path)}):
            asyncio.run(action(update, None))
            self.assertFalse(called)
            update.effective_message.reply_text.assert_awaited_once()
            self.assertEqual(self.store.read()['botRevision'], 1)
            self.store.change('42', {**self.command, 'enabled': True,
                              'expectedRevision': 1, 'operationId': 'reenable-control-operation'})
            asyncio.run(action(update, None))
            self.assertEqual(called, [True])
        unavailable = 'host=127.0.0.1 port=1 dbname=unavailable connect_timeout=1'
        with patch.dict(os.environ, {'BOT_CONTROL_DATABASE_URL': unavailable}):
            asyncio.run(action(update, None))
            self.assertEqual(called, [True])
