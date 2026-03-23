# Music Tool Bot

Music Tool Bot is the ultimate bot for managing your music files effortlessly! 🎵✨. Check it out here:
[@MusicToolBot](https://t.me/MusicToolBot)

Currently, supports 6 languages: **English** and **Persian**, **Russian**, **Spanish**, **French**, **Arabic**. 
([Add more if you want](#contribution))

---

### Requirements to run this bot (without Docker)

1. Python 3.8 or higher (Preferably)
2. `ffmpeg`
3. `venv`
4. Optionally you can install `pm2` (globally) which is a Node.js module to manage processes. Since `pm2` can also
   manage Python processes, I use it to run the bot in production. No Node.js/JavaScript knowledge is required. Just
   install `pm2` and run convenient script runners using `make`. If you want to run the bot using other process
   managers, that's fine.

---

### Project setup (without Docker)

1. **Register for a Telegram Bot**:<br />
   Register a new bot at [Bot Father](https://t.me/BotFather) and get a bot token.

2. **Clone this repo:**<br />
   Run `git clone https://github.com/amirhoseinsalimi/music-tool-bot.git music-tool-bot && cd music-tool-bot`

3. **Install Poetry (if not installed):**<br />
   Follow [Poetry’s official installation guide](https://python-poetry.org/docs/#installation).

4. **Install dependencies:**<br />
   Run `poetry install`.<br />
   This will also create a virtual environment for the project.
   Run commands inside this virtual environment with: `poetry run <command>`

5. **Setup environment variables:**<br />
   Run `cp .env.example .env`. Then put your credentials there:
   | Field                      | Type      | Description |
   | -------------------------- | --------- | -------------------------------------------------------------------------|
   | APP_ENV                    | `str`     | Defines app's environment. Valid values: `production` | `development`    |
   | BOT_NAME                   | `str`     | The name of the bot                                                      |
   | BOT_USERNAME               | `str`     | The username of the bot. This username is sent as signature in captions. |
   | BOT_TOKEN                  | `str`     | The bot token you grabbed from @BotFather                                |
   | DATA_DIR                   | `str`     | Directory for bot file persistence. In Docker this should be `/data` so the pickle and downloaded files survive container restarts. |
   | DB_HOST                    | `str`     | Database host (for postgres).                                            |
   | DB_PORT                    | `int`     | Database port (for postgres).                                            |
   | DB_DATABASE                | `str`     | Database name (for postgres).                                            |
   | DB_USERNAME                | `str`     | Database username (for postgres).                                        |
   | DB_PASSWORD                | `str`     | Database password (for postgres).                                        |
   | OWNER_USER_ID              | `int`     | The user ID of the owner of the bot. This user has more privileges.      |
   | DEBUGGER                   | `boolean` | Enables remote attach with `pydevd-pycharm`                              |
   | DEBUGGER_HOST              | `str`     | Optional PyCharm debug server host. Defaults to `127.0.0.1` locally and tries `host.docker.internal` in Docker |
   | DEBUGGER_PORT              | `int`     | PyCharm debug server port. Defaults to `5400`                            |
   | DEBUGGER_SUSPEND           | `boolean` | Suspends on debugger attach when `true`                                  |
   | BTC_WALLET_ADDRESS         | `str`     | BTC wallet address to receive donations.                                 |
   | ETH_WALLET_ADDRESS         | `str`     | ETH wallet address to receive donations.                                 |
   | TRX_WALLET_ADDRESS         | `str`     | TRX wallet address to receive donations.                                 |
   | USDT_TRC20_WALLET_ADDRESS  | `str`     | USDT (TRC20) wallet address to receive donations.                        |
   | USDT_ERC20_WALLET_ADDRESS  | `str`     | USDT (ERC20) wallet address to receive donations.                        |
   | SHIBA_BEP20_WALLET_ADDRESS | `str`     | SHIBA (BEP20) wallet address to receive donations.                       |
   | SHIBA_ERC20_WALLET_ADDRESS | `str`     | SHIBA (ERC20) wallet address to receive donations.                       |
   | DOGE_WALLET_ADDRESS        | `str`     | DOGE wallet address to receive donations.                                |
   | ZARIN_LINK_ADDRESS         | `str`     | ZarinLink address to receive donations.                                  |

6. **Set up the database:**<br />
   This bot persists users/admins in PostgreSQL. Run migrations:<br />
   `make db-migrate`.<br />
   Then run seeds to populate the `admins` table with an owner-level
   access:<br />
   `make db-seed`.

7. **Run the bot**<br />
   a. Start the bot `make start`<br />
   b. Restart the bot `make restart`<br /><br />

See below for all possible commands:
| Command `make <cmd>` | Description |
| -------------------- | ------------------------------------------------------------------------------------------ |
| `dev`                | Start the bot for development with hot reload thanks to `jurigged`                         |
| `start`              | Start the bot for production using `pm2` module. Creates a process called `music-tool-bot` |
| `restart`            | Restarts the bot process with the name `music-tool-bot`                                    |
| `stop`               | Stops the bot process with the name `music-tool-bot`                                       |
| `db:migrate`         | Run migrations                                                                             |
| `db:refresh`         | Rollback all migration and re-run them (Use with caution)                                  |
| `db:status`          | Print the status of migrations                                                             |
| `db:seed`            | Run seeds to create a user with owner privileges                                           |
| `test`               | Run tests (Not implemented yet)                                                            |
| `t`                  | Alias for `test` command                                                                   |

---

## Running with Docker

You can also run the bot in Docker, without installing Python, Poetry, or ffmpeg on your machine.

1. **Clone the repo**
   ```bash
   git clone https://github.com/amirhoseinsalimi/music-tool-bot.git music-tool-bot
   cd music-tool-bot
   ```

2. **Prepare your environment file**
   `cp .env.example .env`
   Fill in your bot credentials as explained above.

3. **Run database migrations**
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm bot make db-migrate
   docker compose -f docker-compose.yaml -f docker-compose.dev.yaml run --rm bot make db-seed
   ```

4. **Start the bot (development mode with hot reload)**
   `docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up`

   In dev mode, Docker Compose starts a local Postgres container and publishes it on `${DB_PORT:-5432}`.
   The bot persistence file and downloaded files are stored under `/data` in the container, which maps to `./data` on the host.

5. **Start the bot (production mode)**
   `docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d`
   The bot persistence file and downloaded files are stored under `/data` in the container, backed by the `bot_data` Docker volume.

6. **Apply migrations in production before first start**
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.prod.yaml run --rm bot make db-migrate
   docker compose -f docker-compose.yaml -f docker-compose.prod.yaml run --rm bot make db-seed
   ```

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

### Run with Grafana in development

```bash
docker compose \
  -f docker-compose.yaml \
  -f docker-compose.dev.yaml \
  -f docker-compose.grafana.yaml \
  up
```

### Run with Grafana in production

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

### Optional: run the normal stack without Grafana

Development:
```bash
docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up
```

Production:
   ```bash
   docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
   ```

The included Alloy config only ships logs from the Compose service named `bot`, and adds these labels:
- `app="music-tool-bot"`
- `compose_project`
- `compose_service`
- `service_name`
- `environment`

Alloy's local debug UI is exposed on `http://127.0.0.1:12345`.

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
