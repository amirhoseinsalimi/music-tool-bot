"""Core-owned reads with parameterized SQL and authorization in each transaction."""
from datetime import datetime, timezone
from contextlib import closing


class BridgeError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


def telegram_id(value):
    if not isinstance(value, str) or not value.isascii() or not value.isdecimal():
        raise BridgeError(400, "Invalid Telegram ID")
    number = int(value)
    if not 0 < number <= 9223372036854775807:
        raise BridgeError(400, "Invalid Telegram ID")
    return str(number)


def filters(params):
    if set(params) - {"q", "status", "language", "page", "pageSize"}:
        raise BridgeError(400, "Unknown filter")
    q = params.get("q", "").strip().lstrip("@")
    status = params.get("status", "")
    language = params.get("language", "")
    if len(q) > 80 or status not in {"", "active", "blocked", "deleted"}:
        raise BridgeError(400, "Invalid filter")
    if len(language) > 10 or (language and not language.isascii()):
        raise BridgeError(400, "Invalid language")
    try:
        page = int(params.get("page", "1"))
        size = int(params.get("pageSize", "10"))
    except ValueError as error:
        raise BridgeError(400, "Invalid pagination") from error
    if not 1 <= page <= 100000 or not 1 <= size <= 100:
        raise BridgeError(400, "Invalid pagination")
    clauses, values = [], []
    if q:
        # A search is literal text, including SQL LIKE wildcards.
        escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        clauses.append("(u.username ILIKE %s OR CAST(u.user_id AS TEXT) LIKE %s)")
        values.extend([f"%{escaped}%", f"%{escaped}%"])
    if status:
        clauses.append("s.slug = %s")
        values.append(status)
    if language:
        clauses.append("l.iso = %s")
        values.append(language)
    return (" WHERE " + " AND ".join(clauses) if clauses else ""), values, page, size


def timestamp(value):
    if value is None:
        return None
    if not isinstance(value, datetime):
        value = datetime.fromisoformat(str(value))
    # Core ORM stores UTC timestamps without an offset; expose an explicit offset.
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def profile(row):
    return {
        "id": row["id"], "telegramId": str(row["user_id"]),
        "username": row["username"], "language": row["language_name"] or "Not recorded",
        "languageIso": row["language_iso"], "status": row["status_slug"],
        "audioSubmissions": row["number_of_files_sent"],
        "createdAt": timestamp(row["created_at"]), "updatedAt": timestamp(row["updated_at"]),
        "lastInteractionAt": timestamp(row["last_interaction_at"]),
    }


JOINS = " FROM users u LEFT JOIN languages l ON l.id=u.language_id LEFT JOIN user_statuses s ON s.id=u.user_status_id"
COLUMNS = "u.id,u.user_id,u.username,u.number_of_files_sent,u.created_at,u.updated_at,u.last_interaction_at,l.name AS language_name,l.iso AS language_iso,s.slug AS status_slug"


class CoreRepository:
    def __init__(self, connect):
        self.connect = connect

    def dispatch(self, actor_id, path, params):
        from psycopg2.extras import RealDictCursor
        with closing(self.connect()) as connection:
            connection.set_session(readonly=True, isolation_level="REPEATABLE READ")
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("SET LOCAL statement_timeout = '5000ms'")
                cursor.execute("SELECT is_owner FROM admins WHERE admin_user_id=%s LIMIT 1", (int(actor_id),))
                admin = cursor.fetchone()
                if admin is None:
                    raise BridgeError(403, "Admin access required")
                if path == "/v1/session":
                    return {"telegramId": actor_id, "isOwner": bool(admin["is_owner"])}
                if path == "/v1/overview":
                    cursor.execute("SELECT COUNT(*) AS total,COALESCE(SUM(u.number_of_files_sent),0) AS audio" + JOINS)
                    counts = cursor.fetchone()
                    cursor.execute("SELECT COUNT(*) AS total" + JOINS + " WHERE s.slug='active'")
                    active = cursor.fetchone()["total"]
                    cursor.execute("SELECT COALESCE(l.name,'Not recorded') AS name,COUNT(*) AS count" + JOINS + " GROUP BY l.name ORDER BY count DESC,name")
                    return {"totalUsers": counts["total"], "activeStatus": active,
                            "audioSubmissions": counts["audio"], "languages": list(cursor.fetchall())}
                if path in {"/v1/users", "/v1/users/export"}:
                    where, values, page, size = filters(params)
                    cursor.execute("SELECT COUNT(*) AS total" + JOINS + where, values)
                    total = cursor.fetchone()["total"]
                    exporting = path.endswith("/export")
                    if exporting and total > 20000:
                        raise BridgeError(413, "Export exceeds 20000 rows; narrow the filters")
                    pages = max(1, (total + size - 1) // size)
                    page = min(page, pages)
                    limit, offset = (20000, 0) if exporting else (size, (page - 1) * size)
                    cursor.execute("SELECT " + COLUMNS + JOINS + where + " ORDER BY u.created_at DESC,u.id DESC LIMIT %s OFFSET %s", [*values, limit, offset])
                    users = [profile(row) for row in cursor.fetchall()]
                    cursor.execute("SELECT iso,name FROM languages ORDER BY id")
                    return {"users": users, "total": total, "page": page, "pageSize": size,
                            "languages": list(cursor.fetchall())}
                if path.startswith("/v1/users/"):
                    target_id = telegram_id(path.removeprefix("/v1/users/"))
                    cursor.execute("SELECT " + COLUMNS + JOINS + " WHERE u.user_id=%s", (int(target_id),))
                    row = cursor.fetchone()
                    if row is None:
                        raise BridgeError(404, "User not found")
                    return profile(row)
                raise BridgeError(404, "Not found")


def connect_core():
    import psycopg2
    from config.envs import DB_DATABASE, DB_HOST, DB_PASSWORD, DB_PORT, DB_USERNAME
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_DATABASE,
                            user=DB_USERNAME, password=DB_PASSWORD, connect_timeout=5)
