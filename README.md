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
   | DB_CONNECTION              | `str`     | Database driver. Use `postgres` for local Docker development.            |
   | DB_NAME                    | `str`     | SQLite filename (only when `DB_CONNECTION=sqlite`).                      |
   | DB_HOST                    | `str`     | Database host (for postgres).                                            |
   | DB_PORT                    | `int`     | Database port (for postgres).                                            |
   | DB_DATABASE                | `str`     | Database name (for postgres).                                            |
   | DB_USERNAME                | `str`     | Database username (for postgres).                                        |
   | DB_PASSWORD                | `str`     | Database password (for postgres).                                        |
   | OWNER_USER_ID              | `int`     | The user ID of the owner of the bot. This user has more privileges.      |
   | DEBUGGER                   | `boolean` | Attaches a PyCharm's debugger on port `5400`                             |
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
   This bot persists users/admins in a relational database (Postgres or SQLite). Run migrations:<br />
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

   In dev mode, Docker Compose starts a local Postgres container and the bot connects to it using your `.env` values.

5. **Start the bot (production mode)**
   `docker compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d`

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
