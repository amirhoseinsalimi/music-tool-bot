import json
import sqlite3
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from wsgiref.util import setup_testing_defaults

from admin_bridge.app import create_app
from admin_bridge.service import CoreRepository, filters, telegram_id, timestamp


class Cursor:
    def __init__(self, connection):
        self.cursor = connection.cursor()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.cursor.close()

    def execute(self, query, values=()):
        if query.startswith("SET LOCAL"):
            return
        self.cursor.execute(query.replace("%s", "?").replace("ILIKE", "LIKE"), values)

    def fetchone(self):
        row = self.cursor.fetchone()
        return dict(row) if row is not None else None

    def fetchall(self):
        return [dict(row) for row in self.cursor.fetchall()]


class Connection:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row

    def set_session(self, **kwargs):
        assert kwargs == {"readonly": True, "isolation_level": "REPEATABLE READ"}
        self.connection.execute("PRAGMA query_only=ON")

    def cursor(self, **kwargs):
        return Cursor(self.connection)

    def close(self):
        self.connection.close()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / "core.sqlite")
        self.addCleanup(self.directory.cleanup)
        with sqlite3.connect(self.path) as db:
            db.executescript("""
                CREATE TABLE admins(admin_user_id INTEGER,is_owner BOOLEAN);
                CREATE TABLE languages(id INTEGER,iso TEXT,name TEXT);
                CREATE TABLE user_statuses(id INTEGER,slug TEXT);
                CREATE TABLE users(id INTEGER,user_id INTEGER,username TEXT,number_of_files_sent INTEGER,language_id INTEGER,user_status_id INTEGER,created_at TEXT,updated_at TEXT,last_interaction_at TEXT);
                INSERT INTO admins VALUES(42,1);
                INSERT INTO languages VALUES(1,'en','English'),(2,'fa','Persian');
                INSERT INTO user_statuses VALUES(1,'active'),(2,'blocked');
                INSERT INTO users VALUES(1,7000000001,'listener',4,1,1,'2026-10-10 12:00:00','2026-10-10 12:00:00',NULL);
                INSERT INTO users VALUES(2,7000000002,NULL,0,2,2,'2026-10-11 12:00:00','2026-10-11 12:00:00','2026-10-11 12:00:00');
            """)
        self.app = create_app("s" * 32, CoreRepository(lambda: Connection(self.path)))

    def request(self, path="/v1/users", query="", actor="42", token="s" * 32, method="GET"):
        env = {}; setup_testing_defaults(env)
        env.update(PATH_INFO=path, QUERY_STRING=query, REQUEST_METHOD=method,
                   HTTP_AUTHORIZATION="Bearer " + token, HTTP_X_ADMIN_TELEGRAM_ID=actor)
        status = []
        body = b"".join(self.app(env, lambda code, headers: status.append(int(code.split()[0]))))
        return status[0], json.loads(body)

    def test_authentication_membership_and_revocation(self):
        self.assertEqual(self.request(token="wrong")[0], 401)
        self.assertEqual(self.request(actor="999")[0], 403)
        self.assertEqual(self.request("/v1/session")[1], {"telegramId": "42", "isOwner": True})
        with sqlite3.connect(self.path) as db:
            db.execute("DELETE FROM admins")
        for path in ["/v1/session", "/v1/users", "/v1/users/7000000001", "/v1/overview", "/v1/users/export"]:
            self.assertEqual(self.request(path)[0], 403)

    def test_filters_pagination_and_nullable_profile(self):
        code, data = self.request(query="pageSize=1&page=9")
        self.assertEqual(code, 200)
        self.assertEqual((data["page"], data["total"]), (2, 2))
        self.assertEqual(data["users"][0]["telegramId"], "7000000001")
        self.assertIsNone(data["users"][0]["lastInteractionAt"])
        self.assertTrue(data["users"][0]["createdAt"].endswith("+00:00"))
        self.assertEqual(self.request(query="q=%40listener&status=active&language=en")[1]["total"], 1)
        self.assertEqual(self.request(query="q=%27%20OR%201%3D1--")[1]["total"], 0)
        self.assertEqual(self.request("/v1/users/7000000002")[1]["language"], "Persian")
        self.assertEqual(self.request("/v1/users/999")[0], 404)

    def test_invalid_inputs_and_methods(self):
        for query in ["pageSize=101", "page=0", "status=reachable", "q=a&q=b", "unknown=1"]:
            self.assertEqual(self.request(query=query)[0], 400)
        self.assertEqual(self.request(actor="-42")[0], 400)
        self.assertEqual(self.request(method="POST")[0], 405)
        self.assertEqual(self.request("/v1/users/..%2F")[0], 400)

    def test_overview_export_and_unknown_relations(self):
        data = self.request("/v1/overview")[1]
        self.assertEqual((data["totalUsers"], data["activeStatus"], data["audioSubmissions"]), (2, 1, 4))
        self.assertEqual(self.request("/v1/users/export", query="status=blocked")[1]["total"], 1)
        with sqlite3.connect(self.path) as db:
            db.execute("UPDATE users SET user_status_id=999 WHERE id=1")
        self.assertIsNone(self.request("/v1/users/7000000001")[1]["status"])

    def test_id_and_search_validation(self):
        self.assertEqual(telegram_id("007000000001"), "7000000001")
        _, values, _, _ = filters({"q": "_%\\"})
        self.assertEqual(values, ["%\\_\\%\\\\%"] * 2)
        self.assertEqual(timestamp(datetime(2026, 10, 10)), "2026-10-10T00:00:00+00:00")
