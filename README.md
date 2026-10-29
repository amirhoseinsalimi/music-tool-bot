# Music Tool Bot

Music Tool Bot is a Telegram bot for working with audio files. It runs in Docker and stores its database and persistent files in PostgreSQL and a Docker volume.

## Runtime services

The production Compose stack can run these five services together:

| Service | Purpose |
|---|---|
| `bot` | Receives Telegram updates and processes requests. |
| `postgres` | Stores bot records. |
| `sweeper` | Removes downloaded files that have passed the configured retention period. |
| `backup` | Writes compressed database and bot-data backups to `./backups/`. |
| `alloy` | Optional log collector that forwards the bot container's logs to Grafana Cloud. |

The first four services are defined by the base and production Compose files. Alloy is added with the Grafana Compose file. The complete command is in [Run the production stack](#run-the-production-stack).

## Requirements

- Docker Engine with Docker Compose
- A Telegram bot token from [BotFather](https://t.me/BotFather)

## Configuration

Copy the example file and set the required values:

```bash
cp .env.example .env
```

| Variable | Purpose | Default |
|---|---|---|
| `BOT_TOKEN` | Token issued by BotFather. | — |
| `BOT_USERNAME` | Bot username used in generated captions. | — |
| `BOT_NAME` | Name used by the Make commands for container naming. | `music-tool-bot` |
| `OWNER_USER_ID` | Telegram numeric ID that receives owner privileges. | `0` |
| `APP_ENV` | Runtime environment label. | `development` |
| `DATA_DIR` | Persistent bot data directory inside the container. | `/data` |
| `DB_HOST` | PostgreSQL host; Compose sets this to `postgres` for the bot container. | `localhost` |
| `DB_PORT` | PostgreSQL port. | `6003` |
| `DB_DATABASE` | PostgreSQL database name. | — |
| `DB_USERNAME` | PostgreSQL username used by the bot. | — |
| `DB_PASSWORD` | PostgreSQL password. | — |
| `DB_ADMIN_USERNAME` | Optional PostgreSQL maintenance username used by Compose. | `DB_USERNAME` |
| `COMPOSE_PROJECT_NAME` | Optional prefix for Compose container and volume names. | `music-tool-bot` |
| `PTB_TIMEDELTA` | Set internally by Compose for Telegram retry timing; do not set it in `.env`. | `True` in Compose |
| `DEBUGGER` | Enable the PyCharm remote debugger. | `false` |
| `DEBUGGER_HOST` | Debugger host; Docker uses `host.docker.internal` when available. | — |
| `DEBUGGER_PORT` | Debugger port. | `6011` |
| `DEBUGGER_SUSPEND` | Wait for a debugger connection before continuing. | `false` |
| `SWEEPER_RETENTION_DAYS` | Age in days after which downloaded files are removed. | `30` |
| `SWEEPER_INTERVAL` | Seconds between sweeps. | `86400` |
| `BACKUP_RETENTION` | Days to keep backup files. | `7` |
| `BACKUP_INTERVAL` | Seconds between backup runs. | `86400` |
| `GRAFANA_CLOUD_LOKI_URL` | Grafana Cloud Loki push URL; required when Alloy is enabled. | — |
| `GRAFANA_CLOUD_LOKI_USERNAME` | Grafana Cloud Loki username; required when Alloy is enabled. | — |
| `GRAFANA_CLOUD_API_KEY` | Grafana Cloud token with log-write permission. | — |
| `BTC_WALLET_ADDRESS` | Optional Bitcoin donation address. | — |
| `ETH_WALLET_ADDRESS` | Optional Ethereum donation address. | — |
| `TRX_WALLET_ADDRESS` | Optional TRX donation address. | — |
| `USDT_TRC20_WALLET_ADDRESS` | Optional USDT TRC20 donation address. | — |
| `USDT_ERC20_WALLET_ADDRESS` | Optional USDT ERC20 donation address. | — |
| `SHIBA_BEP20_WALLET_ADDRESS` | Optional SHIBA BEP20 donation address. | — |
| `SHIBA_ERC20_WALLET_ADDRESS` | Optional SHIBA ERC20 donation address. | — |
| `DOGE_WALLET_ADDRESS` | Optional Dogecoin donation address. | — |
| `ZARIN_LINK_ADDRESS` | Optional ZarinPal donation link. | — |


## Run the production stack

Clone the repository and enter its directory, then create `.env` as shown above. Set the bot token and database values before starting the stack.

Apply the database schema and seed the owner and language records:

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml run --rm bot make db-migrate
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml run --rm bot make db-seed
```

To start the bot, database, sweeper, backup service, and Alloy together, set the three Grafana Cloud values in `.env` and run:

```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.prod.yaml \
  -f docker-compose.grafana.yaml \
  up -d
```

If Alloy is not needed, omit `-f docker-compose.grafana.yaml`; the other four services still start. PostgreSQL is available to the bot on the internal Compose network at `postgres:6003`. The database port is not published on the host.

Check service state and logs:

```bash
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml -f docker-compose.grafana.yaml ps
docker compose -f docker-compose.yaml -f docker-compose.prod.yaml -f docker-compose.grafana.yaml logs -f bot
```

The Compose stack can also be run for local development with hot reload:

```bash
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up
```

## Alloy log collection

Alloy is optional. It reads Docker container logs and sends the `bot` service logs to the configured Loki endpoint. Set `GRAFANA_CLOUD_LOKI_URL`, `GRAFANA_CLOUD_LOKI_USERNAME`, and `GRAFANA_CLOUD_API_KEY` in `.env`, then include `docker-compose.grafana.yaml` in the Compose command. Alloy's local status UI is bound to `127.0.0.1:6010`.

## Backups and restore

The production `backup` service starts a backup immediately, then repeats at `BACKUP_INTERVAL`. Each run writes a compressed PostgreSQL dump and an archive of `/data` into `./backups/`. Files older than `BACKUP_RETENTION` days are removed. The defaults are one run per day and seven days of local backup retention.

Restore instructions are in [docker/backup/RESTORE.md](docker/backup/RESTORE.md).

## File cleanup

The `sweeper` service scans `/data/downloads` at startup and then every `SWEEPER_INTERVAL` seconds. It removes files older than `SWEEPER_RETENTION_DAYS` and deletes empty directories. The default sweeper interval is 24 hours and its file age threshold is 30 days. The bot also runs an hourly in-process cleanup with a 59-day threshold.

## Make commands

| Command | Purpose |
|---|---|
| `make dev` | Start the bot for development with hot reload. |
| `make deploy` | Build the bot image and recreate the bot container. |
| `make db-migrate` | Apply database migrations. |
| `make db-refresh` | Roll back and reapply migrations. Use with care. |
| `make db-status` | Show migration status. |
| `make db-seed` | Seed the owner and language records. |
| `make test` | Run the test command. |

Run `make help` for the complete command list.

## Contributing

Keep changes focused and include the checks you ran in the pull request description. Do not commit `.env`, user files, database dumps, or backup archives.
