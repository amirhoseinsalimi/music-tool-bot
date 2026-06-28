# Music Tool Bot

Music Tool Bot is the ultimate bot for managing your music files effortlessly! 🎵✨. Check it out here:
[@MusicToolBot](https://t.me/MusicToolBot)

Currently, supports 6 languages: **English** and **Persian**, **Russian**, **Spanish**, **French**, **Arabic**. 
([Add more if you want](#contribution))

The bot runs in **Docker** - no need to install Python, Poetry, or ffmpeg on your machine.

Start by filling in your [configuration](#configuration).

---

## Configuration

First, **register a Telegram bot** at [BotFather](https://t.me/BotFather) and grab its token. Then create your env
file with `cp .env.example .env` and fill in your credentials:

| Field                      | Type      | Description                                                                                                                         |
|----------------------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------|
| APP_ENV                    | `str`     | Defines app's environment. Valid values: `production` \| `development`                                                              |
| BOT_NAME                   | `str`     | The name of the bot                                                                                                                 |
| BOT_USERNAME               | `str`     | The username of the bot. This username is sent as signature in captions.                                                            |
| BOT_TOKEN                  | `str`     | The bot token you grabbed from @BotFather                                                                                           |
| DATA_DIR                   | `str`     | Directory for bot file persistence. In Docker this should be `/data` so the pickle and downloaded files survive container restarts. |
| DB_HOST                    | `str`     | Database host (for postgres).                                                                                                       |
| DB_PORT                    | `int`     | Database port (for postgres).                                                                                                       |
| DB_DATABASE                | `str`     | Database name (for postgres).                                                                                                       |
| DB_USERNAME                | `str`     | Database username (for postgres).                                                                                                   |
| DB_PASSWORD                | `str`     | Database password (for postgres).                                                                                                   |
| OWNER_USER_ID              | `int`     | The user ID of the owner of the bot. This user has more privileges.                                                                 |
| DEBUGGER                   | `boolean` | Enables remote attach with `pydevd-pycharm`                                                                                         |
| DEBUGGER_HOST              | `str`     | Optional PyCharm debug server host. Defaults to `127.0.0.1` locally and tries `host.docker.internal` in Docker                      |
| DEBUGGER_PORT              | `int`     | PyCharm debug server port. Defaults to `5400`                                                                                       |
| DEBUGGER_SUSPEND           | `boolean` | Suspends on debugger attach when `true`                                                                                             |
| BACKUP_RETENTION           | `int`     | Days to keep daily backups. Defaults to `7`.                                                                                        |
| BACKUP_INTERVAL            | `int`     | Seconds between backups. Defaults to `86400` (24 hours).                                                                            |
| SWEEPER_RETENTION_DAYS     | `int`     | Days to keep downloaded user files before automatic cleanup. Defaults to `30`.                                                      |
| SWEEPER_INTERVAL           | `int`     | Seconds between sweeps. Defaults to `86400` (24 hours).                                                                             |
| BTC_WALLET_ADDRESS         | `str`     | BTC wallet address to receive donations.                                                                                            |
| ETH_WALLET_ADDRESS         | `str`     | ETH wallet address to receive donations.                                                                                            |
| TRX_WALLET_ADDRESS         | `str`     | TRX wallet address to receive donations.                                                                                            |
| USDT_TRC20_WALLET_ADDRESS  | `str`     | USDT (TRC20) wallet address to receive donations.                                                                                   |
| USDT_ERC20_WALLET_ADDRESS  | `str`     | USDT (ERC20) wallet address to receive donations.                                                                                   |
| SHIBA_BEP20_WALLET_ADDRESS | `str`     | SHIBA (BEP20) wallet address to receive donations.                                                                                  |
| SHIBA_ERC20_WALLET_ADDRESS | `str`     | SHIBA (ERC20) wallet address to receive donations.                                                                                  |
| DOGE_WALLET_ADDRESS        | `str`     | DOGE wallet address to receive donations.                                                                                           |
| ZARIN_LINK_ADDRESS         | `str`     | ZarinLink address to receive donations.                                                                                             |

---

## Running the Bot (Docker needed)

Run the bot without installing Python, Poetry, or ffmpeg on your machine.

**Requirements:** Docker and Docker Compose.

1. **Clone the repo**
   ```bash
   git clone https://github.com/amirhoseinsalimi/music-tool-bot.git music-tool-bot
   cd music-tool-bot
   ```

2. **Prepare your environment file** — see [Configuration](#configuration) (`cp .env.example .env` and fill it in).

3. **Run database migrations and seeds**
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm bot make db-migrate
   docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm bot make db-seed
   ```
   (For production, swap `docker-compose.dev.yaml` for `docker-compose.prod.yaml`.)

4. **Development (hot reload)**
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up
   ```
   In dev mode, Docker Compose starts a local Postgres container and publishes it on `${DB_PORT:-5432}`.
   The bot persistence file and downloaded files are stored under `/data` in the container, which maps to `./data` on the host.

5. **Production**
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
   ```
   The bot persistence file and downloaded files are stored under `/data` in the container, backed by the `bot_data` Docker volume.

   To ship a new version afterwards, see [Deploying a New Version](#with-docker-near-zero-downtime).

---

## Deploying a New Version

### With Docker (near-zero downtime)

To ship a code change, **do not** stop the stack and rebuild — that takes the bot
down for the whole build. Instead, build the new image while the old container
keeps running, then recreate only the bot in one fast step:

```bash
make deploy
# equivalent to:
# docker compose -f docker-compose.yaml -f docker-compose.prod.yaml build bot
# docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d bot
```

`build` runs against the still-running bot, so the only outage is the recreate
itself — a few seconds. On recreate the old container gets `SIGTERM`; PTB stops
polling and lets the in-flight update (e.g. an ffmpeg job) finish within the
`stop_grace_period` (30s) before exiting. Postgres is untouched.

> **Why only "near-zero", not truly zero:** the bot runs in **polling** mode, and
> Telegram allows only one `getUpdates` consumer per token — so two bot instances
> can't poll at once, and the new container must wait for the old one to stop. The
> few-second gap is handed off cleanly: updates that arrive meanwhile are queued by
> Telegram and delivered once the new instance starts polling, so nothing is lost.
> True overlapping (blue-green) deploys would require switching to webhooks behind a
> reverse proxy.

If the new version includes database migrations, apply them before recreating:

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml run --rm bot make db-migrate
make deploy
```

---

## Make Commands

| Command `make <cmd>` | Description |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `dev`                | Start the bot for development with hot reload thanks to `jurigged`                         |
| `deploy`             | Build the new Docker image, then recreate only the bot with near-zero downtime             |
| `db-migrate`         | Run migrations                                                                             |
| `db-refresh`         | Rollback all migrations and re-run them (Use with caution)                                 |
| `db-status`          | Print the status of migrations                                                             |
| `db-seed`            | Run seeds to create a user with owner privileges                                           |
| `test`               | Run tests (Not implemented yet)                                                            |
| `t`                  | Alias for `test` command                                                                   |

Run `make help` to see this list from the terminal.

---

## Shipping Logs To Grafana Cloud

This repo includes an optional Grafana Alloy setup that tails the bot container logs from Docker and forwards them to
Grafana Cloud Logs.

Why this uses a separate Compose file:
- Grafana log shipping is optional, so it is kept as an overlay instead of being forced into every local run.
- This lets you enable or disable log shipping by adding or removing one `-f docker-compose.grafana.yaml`.

### Get your Grafana Cloud credentials

You need three values:
- Loki push URL
- Loki username
- Grafana Cloud API token

How to find them in Grafana Cloud:

1. Sign in to Grafana Cloud and open your stack.
2. Select **Details** for the stack.
3. Open the **Loki / Logs** section.
4. Copy the stack URL and user ID from the Loki details page.
   The push URL should look similar to:
   ```dotenv
   GRAFANA_CLOUD_LOKI_URL=https://logs-xxx.grafana.net/loki/api/v1/push
   ```
   The username is the numeric stack user / instance ID.
5. Create a token:
   - Open **Administration -> Cloud access policies** inside the stack, or use the Cloud Portal access policies page.
   - Create an access policy scoped to your stack.
   - Give it `logs:write` permission.
   - Add a token under that policy and copy it immediately. Grafana only shows it once.

Add these values to `.env`:
```dotenv
GRAFANA_CLOUD_LOKI_URL=https://logs-xxx.grafana.net/loki/api/v1/push
GRAFANA_CLOUD_LOKI_USERNAME=123456
GRAFANA_CLOUD_API_KEY=your-token
```

### Run with Grafana

Add the `-f docker-compose.grafana.yaml` overlay to your normal run command.

Development:
```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.dev.yaml \
  -f docker-compose.grafana.yaml \
  up
```

Production:
```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.prod.yaml \
  -f docker-compose.grafana.yaml \
  up -d
```

### Check logs in Grafana

Open Grafana Explore and query:
```logql
{app="music-tool-bot"}
```

You can also filter by environment:
```logql
{app="music-tool-bot", environment="development"}
```

or:
```logql
{app="music-tool-bot", environment="production"}
```

The included Alloy config only ships logs from the Compose service named `bot`, and adds these labels:
- `app="music-tool-bot"`
- `compose_project`
- `compose_service`
- `service_name`
- `environment`

Alloy's local debug UI is exposed on `http://127.0.0.1:12345`.

---

## Daily Backups

A backup service is included in `docker-compose.prod.yaml` that automatically creates daily backups of:

- **PostgreSQL database** — full dump (`pg_dump --clean`) of users, admins, and all data.
- **Bot data** — compressed archive of the `DATA_DIR` volume (downloaded files, pickles, etc.).

### How it works

The backup service runs a dedicated container (`postgres:16-alpine`) that:
1. Connects to the `postgres` container and dumps the database → gzipped.
2. Archives the `bot_data` volume content → tar.gz.
3. Saves both files to `./backups/` on the host machine.
4. Deletes files older than `BACKUP_RETENTION` days (default: 7).

The first backup runs immediately when the container starts, then repeats every `BACKUP_INTERVAL` seconds (default: 86400 = 24 hours).

### Start the backup service

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d backup
```

Check the logs:

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml logs -f backup
```

Example output:
```
[2026-06-27 11:25:00] Backup service started
[2026-06-27 11:25:00]   Interval:  86400s (24h)
[2026-06-27 11:25:00]   Retention: 7 days
[2026-06-27 11:25:00] === Starting backup: 2026-06-27_11-25-00 ===
[2026-06-27 11:25:02] PostgreSQL backup completed: 1.2M
[2026-06-27 11:25:03] Bot data archive completed: 3.5M
[2026-06-27 11:25:03] === Backup completed successfully ===
```

### Backup files

Backups are written to `./backups/` on the host machine:

```
backups/
├── postgres_2026-06-27_11-25-00.sql.gz    (database dump)
└── bot_data_2026-06-27_11-25-00.tar.gz    (bot data archive)
```

This directory is on the **host filesystem** (not a Docker volume), so backups survive `docker system prune --volumes` and can be accessed, copied, or uploaded directly.

> **Note:** `backups/` is gitignored to prevent sensitive data from being committed to version control.

### Configuration

| Env Variable       | Default | Description |
|--------------------|---------|-------------|
| `BACKUP_RETENTION` | `7`     | Days to keep backup files before automatic cleanup |
| `BACKUP_INTERVAL`  | `86400` | Seconds between backups (86400 = 24 hours) |

### Restoring from a backup

See [docker/backup/RESTORE.md](docker/backup/RESTORE.md) for step-by-step restore instructions covering:

- Restoring the PostgreSQL database
- Restoring bot data files
- Full disaster recovery on a fresh machine

### Why not in development?

The backup service is only included in `docker-compose.prod.yaml` to avoid running unnecessary containers during local development. When running `docker-compose.dev.yaml`, the backup service is not started.

---

## File Retention & Sweeper

The bot doesn't delete downloaded user files immediately after processing. Instead, files are preserved on disk for a configurable retention period (default: **30 days**) and cleaned up by a dedicated **sweeper** service that runs daily.

### How it works

The sweeper service runs a separate container (`sweeper`) that:

1. Scans the `DATA_DIR/downloads/` directory for files.
2. Deletes any file older than `SWEEPER_RETENTION_DAYS` (default: 30).
3. Removes empty user directories after deletion.
4. Runs the first sweep immediately on startup, then repeats every `SWEEPER_INTERVAL` seconds (default: 86400 = 24 hours).

### Start the sweeper service

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d sweeper
```

Check the logs:

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml logs -f sweeper
```

### Processing artifacts

Temporary output files generated during processing (e.g., `_bitrate.mp3`, `_cut.mp3`, `.opus`, intermediate `.m4a`) are still deleted immediately after upload - only the original downloaded files are retained by the sweeper.

### Why not in development?

Like the backup service, the sweeper is only defined in `docker-compose.prod.yaml` to avoid unnecessary containers during local development.


## Contribution

In the beginning, I had written this bot in JavaScript, but due to a lack of quality packages, it was full of bugs. Then
I decided to learn Python and thought: Why not re-write @MusicToolBot in Python? And then I began to revive the
project. <br />

This tiny bot is my first practical Python project. I tried to learn Python along with coding, so I could better wrap my
head around the syntax and the built-in functionality of the language. However, as a novice Python developer, I know
this bot can be written in a more smart way with better code structure. So, if you know Python, I would really
appreciate any help to make this kid better. My main concern is the application structure, but please feel free to
create PRs, open discussions and make small fixes (like typos). In addition, I have some plans and features for this
bot, you can find them on the [issue board](https://github.com/amirhoseinsalimi/music-tool-bot/issues). Also, I'd really appreciate it if you can translate the bot to 
your language.
