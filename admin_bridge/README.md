# Optional administrative bridge

Read-only, core-owned WSGI service for authorized admin membership, user search/profiles, overview totals and filtered export. No User/Admin schema is duplicated in private services. The polling bot never imports this package and needs no new dependency or private service to run.

## Local operation

Use the bot's existing Poetry environment and core database configuration. Add a separately generated `ADMIN_BRIDGE_TOKEN` (at least 32 random characters) to the bot environment. The private API must have the identical bridge token. Do not use `BOT_TOKEN` as the bridge secret.

```sh
make admin-bridge
```

This development entry point listens only on `127.0.0.1:6004` by default; `ADMIN_BRIDGE_PORT` overrides the port. For later hosted use, run `create_app(token)` under a production WSGI server and keep it on a private network/HTTPS boundary. No host deployment has been installed here.

The bridge connects to the configured core PostgreSQL database, with a read-only transaction, a connection timeout and statement timeout. Use a dedicated read-only database role when deployment is configured; the separate process can receive its own DB credentials through the existing DB environment fields. No migration or database refresh is required for these reads. Existing integer-ID schemas remain unchanged.

## Protocol v1

Every request requires `Authorization: Bearer <ADMIN_BRIDGE_TOKEN>` and `X-Admin-Telegram-ID: <verified Telegram ID>`. The trusted private API derives the actor from a verified login session; the browser never receives the bridge token. The bridge checks current `admins` membership in the same transaction as the requested read. All admins can perform these reads; `isOwner` is returned from core membership for later owner-only operations. There are no write operations.

| GET path | Response |
| --- | --- |
| `/v1/session` | Current actor Telegram ID and owner flag |
| `/v1/users` | Paginated users, including recorded Telegram display name and username, total count, page/pageSize and language choices |
| `/v1/users/<telegram_id>` | Available core user profile, including the recorded Telegram display name |
| `/v1/overview` | User total, Active status count, audio submissions and language counts |
| `/v1/users/export` | All matching profiles, bounded to 20000 rows; narrow filters beyond that |
| `/v1/files` | Current retained files, filtered and paginated from the filesystem |
| `/v1/files/download` | Authorized binary attachment for an exact Telegram ID and basename |

User filters are `q`, `status` (`active`, `blocked`, `deleted`), `language` (ISO), `page` and `pageSize` (1–100). Username and Telegram ID search is parameterized literal matching. Duplicate/unknown filters, malformed IDs and out-of-range pagination return 400. Unauthorized tokens return 401, revoked/non-admin actors return 403, missing profiles return 404, oversized exports return 413 and core failures return 503. Failure is never an empty successful collection.

IDs cross the JSON boundary as strings. Missing interaction/status/language relations remain missing, without invented inactivity or Active status. Naive core ORM timestamps are interpreted as UTC and exposed with an offset; verify the historical database's timestamp convention when connecting an existing deployment. Counts describe current records, not daily activity/history. File inventory comes from `DATA_DIR/downloads/<Telegram ID>/`, never from submission counters.

## Verification

```sh
make test-admin-bridge
```

The seventeen tests run the real bridge/repository with a PostgreSQL adapter for isolated query and authorization behavior. They do not establish live PostgreSQL connectivity; that remains an integration check. The old sample suite under `tests/unit` still has its unrelated known placeholder failure.

## Code organization

This remains a standalone WSGI package rather than a Telegram handler module. It has no
registration in `bot.py`. Its layers follow the bot's service/helper separation:

- `app.py`: request authentication, HTTP handling and safe JSON responses.
- `service.py`: authorized, read-only core database operations.
- `utils.py`: ID/query validation and timestamp/profile serialization.
- `exceptions.py`: public bridge errors with HTTP status codes.
- `__main__.py`: the explicit entry point, using the bot's environment and logging setup.

Public functions have type hints and `:param` / `:return` / `:raises` docstrings matching
existing helpers. Imports, named arguments and line breaks follow the surrounding Python
code, including the repository's 100-character line limit. Refactoring these layers does
not change the v1 endpoint paths or response field names consumed by the private API.

Run the existing development tools in the Poetry environment:

```sh
poetry run autopep8 --diff --max-line-length 100 --recursive admin_bridge tests/bridge
poetry run pylint --persistent=no --disable=useless-option-value,unknown-option-value admin_bridge tests/bridge
```

The Pylint command ignores only obsolete diagnostics from the existing `.pylintrc`;
the project configuration itself is unchanged. Specific inline exceptions describe the
single authorized repository entry point and unittest fixture lifecycle. CI checks these
same files with dependency constraints read from `pyproject.toml`.

## Retained file reads

`/v1/files` accepts `q` (literal, case-insensitive basename or Telegram ID search),
`telegramId` (exact owner), `page` and `pageSize` (1–100). Results contain `basename`,
`telegramId`, `bytes` and `modifiedAt`, sorted newest modification first. Timestamps are
filesystem modification times, not upload times. Empty directories are not files; removed
files disappear on the next scan. A missing/unreadable storage root is an error, not an
empty successful collection. The scan is bounded to 100000 entries/five seconds; an exact
owner filter avoids scanning unrelated users.

`/v1/files/download?telegramId=42&basename=<stored basename>` returns a no-store,
`application/octet-stream` attachment. Both operations check current admin membership
before storage access. Only direct regular files are served. Path separators, traversal,
control characters, symlinks, multiply linked files and special files are rejected. Linux
non-following directory/file descriptors prevent directory replacement from redirecting a
read outside the configured root. The descriptor is opened before headers, streamed in
64 KiB chunks and closed on completion or cancellation. A file removed before opening
returns 404. In-place modification/truncation during transfer may interrupt the download;
this does not introduce retention leases or change the bot's cleanup policy.

Mount the bot's `/data` volume read-only in the bridge. The private admin API receives
neither a storage mount nor database credentials; it proxies authorized binary transfers.
There are no new core tables, polling dependencies or file mutations.

## Owner controls

Optional `BOT_CONTROL_DB` enables a separate core-owned runtime configuration
store; no core database write privileges are needed. `ADMIN_CONTROL_TOKEN` must
be distinct from the read credential and at least 32 characters. Only current
owners can POST reasoned, revision-checked `/v1/controls` changes. Current admins
can GET controls and the immutable audit history. `BOT_PREMIUM_CONTROLS=true`
reports the installed private premium tools as well. Mount the same store into
the existing bot; without that mount/environment setting, saved controls cannot
affect its handlers. Standalone deployments remain independent of this store.

## PostgreSQL controls and test storage

Optional runtime controls use `BOT_CONTROL_DATABASE_URL`. The bridge owns this
core-controlled PostgreSQL store; the bot has settings-read/observation-write
privileges and premium has a separate read-only role. No database file is shared.
`postgres_storage.py` uses the same PostgreSQL driver as the core repository.
Bridge tests require `TEST_DATABASE_URL` for an isolated `musictoolbot_tests`
database and create/drop unique schemas with the real PostgreSQL driver. No SQL
dialect adapter or in-memory database substitutes for PostgreSQL in these tests.
