/* Built-in Node.js modules */
const fs = require('fs');


/* Third-part Node.js modules */
const axios = require('axios');
const download = require('download');
const mkdirp = require('mkdirp');
const NodeID3 = require('node-id3');


/* Import Telegraf and its middlewares */
const Telegraf = require('telegraf');
const Extra = require('telegraf/extra');
const Markup = require('telegraf/markup');
const LocalSession = require('telegraf-session-local');


/* Global variables */
const token = '932660872:AAGc1X8vwlyp88Vhwb1B7EDT9v5SJ2-VYH8';
const dirname = `${__dirname}/user_data/`;
const defaultMessage = 'Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁';


/* Bot configuration */
const bot = new Telegraf(token);


/* Middlewares configuration */
bot.use((new LocalSession({ database: 'db.json' })).middleware());
bot.startPolling();


/* Bot commands */
bot.start((ctx) => {
  const userId = ctx.update.message.from.id;

  /* Set initial status */
  ctx.session.status = ctx.session.status || {
    firstInteraction: (new Date()).toUTCString(),
  };
  ctx.session.status.active = true;
  ctx.session.status.blocked = false;

  /* Set initial stats */
  ctx.session.stats = ctx.session.stats || {
    tagEditor: 0,
    toVoiceConverter: 0,
    bitrateChanger: 0,
    cutter: 0,
  };

  ctx.session.tagEditor = null;
  ctx.session.toVoiceConverter = null;
  ctx.session.bitrateChanger = null;
  ctx.session.cutter = null;

  mkdirp(`${dirname}/${userId}`, (err) => {
    let message;

    if (err) {
      console.log(`Error lunching the bot: ${err.name}: ${err.message}`);
      message = 'Bot Error!';
    } else {
      message = 'Hello there! 👋\nLet\'s get started. Just send me a music and see how awesome I am!';
    }

    return ctx.reply(message, Extra.markup((m) => m.removeKeyboard()));
  });
});

bot.help((ctx) => ctx.reply('It\'s simple! Just send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁'));


bot.hears('🗣 Artist', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = defaultMessage;
  } else {
    ctx.session.tagEditor.currentTag = 'artist';
    message = 'Enter the name of the Artist:';
  }

  return ctx.reply(message);
});

bot.hears('🎵 Title', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = defaultMessage;
  } else {
    ctx.session.tagEditor.currentTag = 'title';
    message = 'Enter the Title of the music:';
  }

  return ctx.reply(message);
});

bot.hears('🎼 Album', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = defaultMessage;
  } else {
    ctx.session.tagEditor.currentTag = 'album';
    message = 'Enter the name of the Album:';
  }

  return ctx.reply(message);
});

bot.hears('🎹 Genre', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = defaultMessage;
  } else {
    ctx.session.tagEditor.currentTag = 'genre';
    message = 'Enter the Genre:';
  }

  return ctx.reply(message);
});

bot.hears('📅 Year', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = defaultMessage;
  } else {
    ctx.session.tagEditor.currentTag = 'year';
    message = 'Enter the publish Year:';
  }

  return ctx.reply(message);
});

bot.command('done', (ctx) => {
  if (ctx.session.tagEditor) {
    const tags = ctx.session.tagEditor.tags || undefined;
    const musicPath = ctx.session.tagEditor.musicPath || undefined;

    if (musicPath) {
      fs.readFile(musicPath, (err) => {
        if (err) {
          console.log(`Error reading the file: ${err.name}: ${err.message}`);
          return ctx.reply('Oops! Did you forget to send me a file? 🤔');
        }
        NodeID3.update(tags, musicPath, (err) => {
          if (err) {
            console.log(`Error updating tags: ${err.name}: ${err.message}`);
            return ctx.reply('Bot Error!');
          }
          ctx.telegram.sendDocument(ctx.from.id, {
            source: musicPath,
            filename: `@MusicToolBot_${tags.artist}_${tags.title}.mp3`,
          }, Extra.markup((m) => m.removeKeyboard()))
            .then(() => {
              ctx.session.stats.tagEditor++;
              ctx.session.tagEditor = null;

              fs.unlink(musicPath, (err) => {
                if (err) {
                  console.log(`Error deleting the file: ${err.name}: ${err.message}`);
                }
                console.log('Finished!');
              });
            })
            .catch((err) => {
              console.log(`Error reading the file: ${err.name}: ${err.message}`);
            });
        });
      });
    } else {
      return ctx.reply(defaultMessage);
    }
  } else {
    return ctx.reply(defaultMessage);
  }
});


bot.on('text', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = defaultMessage;
  } else if (ctx.session.tagEditor) {
    if (ctx.session.tagEditor.currentTag) {
      const { currentTag } = ctx.session.tagEditor;

      if (currentTag === 'artist') {
        ctx.session.tagEditor.tags.artist = ctx.update.message.text;
        message = 'Artist name changed. If you\'re finished click /done';
      } else if (currentTag === 'title') {
        ctx.session.tagEditor.tags.title = ctx.update.message.text;
        message = 'Music title changed. If you\'re finished click /done';
      } else if (currentTag === 'album') {
        ctx.session.tagEditor.tags.album = ctx.update.message.text;
        message = 'Album name changed. If you\'re finished click /done';
      } else if (currentTag === 'genre') {
        ctx.session.tagEditor.tags.genre = ctx.update.message.text;
        message = 'Genre changed. If you\'re finished click /done';
      } else if (currentTag === 'year') {
        ctx.session.tagEditor.tags.year = ctx.update.message.text;
        message = 'Year changed. If you\'re finished click /done';
      }
    } else {
      message = 'Please select the tag you want to edit! 😅';
    }
  } else {
    message = defaultMessage;
  }

  return ctx.reply(message);
});


/* Catch Audio files */
bot.on('audio', (ctx) => {
  ctx.session.tagEditor = {};

  const userId = ctx.update.message.from.id;
  const baseURL = 'https://api.telegram.org';
  const fileId = ctx.update.message.audio.file_id;
  const url = `bot${token}/getFile?file_id=${fileId}`;

  axios({
    baseURL,
    url,
    method: 'get',
    responseType: 'json',
  })
    .then((res) => {
      const filePath = res.data.result.file_path;
      const fileName = filePath.split('/')[1];
      const url = `file/bot${token}/${filePath}`;

      axios({
        url,
        method: 'get',
        baseURL,
        responseType: 'blob',
      })
        .then(() => {
          download(`https://api.telegram.org/${url}`, `${dirname}/${userId}`)
            .then(() => {
              const tags = NodeID3.read(`${dirname}/${userId}/${fileName}`);
              const {
                artist,
                title,
                album,
                genre,
                year,
              } = tags;

              ctx.session.tagEditor.musicPath = `${dirname}/${userId}/${fileName}`;

              ctx.session.tagEditor.tags = {
                artist: artist || undefined,
                title: title || undefined,
                album: album || undefined,
                genre: genre || undefined,
                year: year || undefined,
              };

              ctx.session.tagEditor.currentTag = '';

              const firstReply = 'ℹ️ MP3 Info:\n\n'
                + `🗣 Artist: ${ctx.session.tagEditor.tags.artist}\n`
                + `🎵 Title: ${ctx.session.tagEditor.tags.title}\n`
                + `🎼 Album: ${ctx.session.tagEditor.tags.album}\n`
                + `🎹 Genre: ${ctx.session.tagEditor.tags.genre}\n`
                + `📅 Year: ${ctx.session.tagEditor.tags.year}\n`
                + '\nWhich tag do you want to edit?';

              return ctx.reply(firstReply, Markup
                .keyboard([
                  ['🗣 Artist', '🎵 Title'],
                  ['🎼 Album', '🎹 Genre', '📅 Year'],
                ])
                .resize()
                .extra());
            })
            .catch((err) => {
              console.log(`Error downloading the music: ${err.name}: ${err.message}`);
            });
        })
        .catch((err) => {
          console.log(`Error getting blob: ${err.name}: ${err.message}`);
        });
    })
    .catch((err) => {
      console.log(`Error getting JSON: ${err.name}: ${err.message}`);
    });
});


/* Replies to anything except audio files */
bot.on([
  'video',
  'video_note',
  'document',
  'game',
  'animation',
  'photo',
  'sticker',
  'voice',
  'contact',
  'location',
  'poll',
  'venue',
], (ctx) => ctx.reply(defaultMessage));


/* Launch bot! */
bot.launch()
  .catch((err) => {
    console.log(`Error lunching the bot: ${err.name}: ${err.message}`);
  });
