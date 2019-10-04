# Music Tool Bot

### Requirements to run this bot
1. Node.js and npm
2. Globally installed `pm2` module (Simply run `npm i -g pm2`)

### Project setup

1. **Clone this repo:**\
Run `git clone https://gitlab.com/Exceptional-Dev/IOException/WebException/music-tool-bot.git music-tool-bot && cd music-tool-bot`

2. **Install dependencies:**
Run `npm i -S`

3. **Enter Telegram Bot Token**\
Register a new bot at [Bot Father](https://telegram.me/BotFather) and get an bot token. Create a file named `config.js`
and export a configuration object as below and save the file:
    ```
    module.exports = {
      BOT_TOKEN: 'YOUT_BOT_TOKEN',
    };
    ```
   
5. **Run the bot**\
a. Start the bot `npm start`\
a. restart `npm run restart`\
c. See `package.json` for other possible commands
 ---
If you want to report a bug or willing a new feature feel free to open a issue. PRs are welcome as well!
