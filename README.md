# Music Tool Bot

The one and only Telegram bot you want to manage your music and MP3 files. Check it out here:
[@MusicToolBot](https://t.me/MusicToolBot)

Supports 2 languages for now: **English** and **Persian**. ([Add more if you want](#contribution))

### Requirements to run this bot

1. Python 3.8 (Preferably)
2. MySQL Server
3. ffmpeg
4. `venv` and `pipenv`
5. Optionally you can install `pm2` (globally) which is a Node.js module to manage processes. Since `pm2` can also
   manage Python processes, I use it to run the bot in production. No Node.js/JavaScript knowledge is required. Just
   install `pm2` and run convenient script runners using pipenv. If you want to run the bot using other process
   managers, that's fine.

---

### Project setup

0. **Register for a Telegram Bot**:<br />
   Register a new bot at [Bot Father](https://t.me/BotFather) and get a bot token.

1. **Clone this repo:**<br />
   Run `git clone https://github.com/amirhoseinsalimi/music-tool-bot.git music-tool-bot && cd music-tool-bot`

2. **Fire up your venv shell:**<br />
   Run `python3 -m venv venv`, then install pipenv: `pip install pipenv`

3. **Install dependencies:**<br />
   Run `pipenv install`

4. **Setup environment variables:**<br />
   Run `cp .env.example .env`. Then put your credentials there:
   | Field           | Description                                                                                                                      |
   | --------------  | -------------------------------------------------------------------------------------------------------------------------------  |
   | OWNER_USER_ID   | The user ID of the owner of the bot (YOU). This user can add other admins and delete them. It should be something like 12345678. |
   | BOT_NAME        | The name of the bot                                                                                                              |
   | BOT_USERNAME    | The username of the bot. This username is sent as signature in captions                                                          |
   | BOT_TOKEN       | The bot token you grabbed from @BotFather                                                                                        |
   | DB_HOST         | Database host                                                                                                                    |
   | DB_PORT         | Database port                                                                                                                    |
   | DB_USERNAME     | Database username                                                                                                                |
   | DB_PASSWORD     | Database password                                                                                                                |
   | DB_NAME         | Database name. Read the next step for more information.                                                                          |
   
5. **Setup the database:**<br />
   This bot persists the IDs of users and admins in a MySQL database. So you need to create a database followed by 
   running migrations:<br />
   `pipenv run db:migrate`.<br />
   Then run seeds to populate the `admins` table with an owner-level 
   access:<br />
   `pipenv run db:seed`.

6. **Run the bot**<br />
   a. Start the bot `pipenv run start`<br />
   b. restart `pipenv run restart`<br /><br />
   
See below for all possible commands:
| Command `pipenv run <command>`   | Description                                                                                |
| ------------------------------   | ------------------------------------------------------------------------------------------ |
| `start`                          | Start the bot for production using `pm2` module. Creates a process called `music-tool-bot` |
| `restart`                        | Restarts the bot process with the name `music-tool-bot`                                    |
| `stop`                           | Stops the bot process with the name `music-tool-bot`                                       |
| `db:migrate`                     | Run migrations                                                                             |
| `db:refresh`                     | Rollback all migration and re-run them (Use with caution)                                  |
| `db:status`                      | Print the status of migrations                                                             |
| `db:seed`                        | Run seeds to create a user with owner privileges                                           |
| `test`                           | Run tests (Not implemented yet)                                                            |
| `t`                              | Alias for `test` command                                                                   |

---

# Contribution

At the beginning I had written this bot in JavaScript, but due to lack of quality packages, it was full of bugs. Then I
decided to learn Python and thought: **Why not re-write @MusicToolBot in Python?** And then I began to revive the
project. <br />

This tiny bot is my first practical Python project. I tried to learn Python along with coding, so I could better wrap my
head around the syntax and the built-in functionality of the language. However, as a novice Python developer, I know
this bot can be written in a more smart way with better code structure. So, if you know Python, I will really appreciate
any help to make this kid better. My main concern is the application structure, but please feel free to create PRs, open
discussions and make small fixes (like typos). In addition, I got some plans and features for this bot, you can find 
them [in TODOS file](https://github.com/amirhoseinsalimi/music-tool-bot/blob/master/TODOS) or the 
[issue board](https://github.com/amirhoseinsalimi/music-tool-bot/issues). Also, I'd be very appreciated if you can 
translate the bot to your language.
