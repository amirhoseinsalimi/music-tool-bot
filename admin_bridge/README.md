# Optional administrative bridge

Read-only, core-owned WSGI service for authorized admin membership, user search/profiles, overview totals and filtered export. No User/Admin schema is duplicated in private services. The polling bot never imports this package and needs no new dependency or private service to run.

## Local operation

Use the bot's existing Poetry environment and core database configuration. Add a separately generated `ADMIN_BRIDGE_TOKEN` (at least 32 random characters) to the bot environment. The private API must have the identical bridge token. Do not use `BOT_TOKEN` as the bridge secret.

```sh
poetry run python -m admin_bridge
```

This development entry point listens only on `127.0.0.1:5001` by default; `ADMIN_BRIDGE_PORT` overrides the port. For later hosted use, run `create_app(token)` under a production WSGI server and keep it on a private network/HTTPS boundary. No host deployment has been installed here.

The bridge connects to the configured core PostgreSQL database, with a read-only transaction, a connection timeout and statement timeout. Use a dedicated read-only database role when deployment is configured; the separate process can receive its own DB credentials through the existing DB environment fields. No migration or database refresh is required for these reads. Existing integer-ID schemas remain unchanged.

## Protocol v1

Every request requires `Authorization: Bearer <ADMIN_BRIDGE_TOKEN>` and `X-Admin-Telegram-ID: <verified Telegram ID>`. The trusted private API derives the actor from a verified login session; the browser never receives the bridge token. The bridge checks current `admins` membership in the same transaction as the requested read. All admins can perform these reads; `isOwner` is returned from core membership for later owner-only operations. There are no write operations.

| GET path | Response |
| --- | --- |
| `/v1/session` | Current actor Telegram ID and owner flag |
| `/v1/users` | Paginated users, total count, page/pageSize and language choices |
| `/v1/users/<telegram_id>` | Available core user profile |
| `/v1/overview` | User total, Active status count, audio submissions and language counts |
| `/v1/users/export` | All matching profiles, bounded to 20000 rows; narrow filters beyond that |

User filters are `q`, `status` (`active`, `blocked`, `deleted`), `language` (ISO), `page` and `pageSize` (1–100). Username and Telegram ID search is parameterized literal matching. Duplicate/unknown filters, malformed IDs and out-of-range pagination return 400. Unauthorized tokens return 401, revoked/non-admin actors return 403, missing profiles return 404, oversized exports return 413 and core failures return 503. Failure is never an empty successful collection.

IDs cross the JSON boundary as strings. Missing interaction/status/language relations remain missing, without invented inactivity or Active status. Naive core ORM timestamps are interpreted as UTC and exposed with an offset; verify the historical database's timestamp convention when connecting an existing deployment. Counts describe current records, not daily activity/history. File inventory/downloads are outside this increment.

## Verification

```sh
poetry run python -m unittest discover -s tests/bridge -v
```

The five tests run the real bridge/repository with a SQLite adapter for isolated query and authorization behavior. They do not establish live PostgreSQL connectivity; that remains an integration check. The old sample suite under `tests/unit` still has its unrelated known placeholder failure.
