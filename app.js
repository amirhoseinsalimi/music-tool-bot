/* Built-in Node.js modules */
const fs = require('fs');


/* Third-part Node.js modules */
const mkdirp = require('mkdirp');
const NodeID3 = require('node-id3');
const mm = require('music-metadata');


/* Import Telegraf and its middlewares */
const Telegraf = require('telegraf');
const Extra = require('telegraf/extra');
const Markup = require('telegraf/markup');
const LocalSession = require('telegraf-session-local');
const downloader = require('./my_modules/downloader');
const config = require('./my_modules/config');


/* Global variables */
const dirname = `${__dirname}/user_data/`;
const defaultMessage = 'Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁';


/* Bot configuration */
const bot = new Telegraf(config.BOT_TOKEN);

/* Error Messages */
const REPORT_BUG_MESSAGE = 'This bug will be reported and fixed very soon!';
const ERR_ON_DOWNLOAD_MESSAGE = `Sorry, I could't download your file... That's my fault! ${REPORT_BUG_MESSAGE}`;
const ERR_ON_READING_TAGS = `Sorry, I could't read the tags of the file... That's my fault! ${REPORT_BUG_MESSAGE}`;


/* Middlewares configuration */
bot.use((new LocalSession({ database: 'db.json' })).middleware());
bot.startPolling();


/* Bot commands */
bot.start((ctx) => {
  const userId = ctx.update.message.from.id;
  const { username } = ctx.update.message.from;

  /* Set initial status */
  ctx.session.status = ctx.session.status || {
    firstInteraction: (new Date()).toUTCString(),
  };
  ctx.session.status.active = true;
  ctx.session.status.blocked = false;
  ctx.session.status.name = username;

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


bot.command('preview', (ctx) => {
  if (ctx.session.tagEditor) {
    const musicPath = ctx.session.tagEditor.musicPath || undefined;

    if (musicPath) {
      return ctx.reply('ℹ️ MP3 Info:\n\n'
          + `🗣 Artist: ${ctx.session.tagEditor.tags.artist}\n`
          + `🎵 Title: ${ctx.session.tagEditor.tags.title}\n`
          + `🎼 Album: ${ctx.session.tagEditor.tags.album}\n`
          + `🎹 Genre: ${ctx.session.tagEditor.tags.genre}\n`
          + `📅 Year: ${ctx.session.tagEditor.tags.year}\n`
          + '\nWhich tag do you want to edit?'
          + '\n\nClick /done to save your changes.');
    }
    return ctx.reply(defaultMessage);
  }
  return ctx.reply(defaultMessage);
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
        message = 'Artist name changed. If you want to preview your changes click /preview.\n\nClick /done to save your changes.';
      } else if (currentTag === 'title') {
        ctx.session.tagEditor.tags.title = ctx.update.message.text;
        message = 'Music title changed. If you want to preview your changes click /preview.\n\nClick /done to save your changes.';
      } else if (currentTag === 'album') {
        ctx.session.tagEditor.tags.album = ctx.update.message.text;
        message = 'Album name changed. If you want to preview your changes click /preview.\n\nClick /done to save your changes.';
      } else if (currentTag === 'genre') {
        ctx.session.tagEditor.tags.genre = ctx.update.message.text;
        message = 'Genre changed. If you want to preview your changes click /preview.\n\nClick /done to save your changes.';
      } else if (currentTag === 'year') {
        const year = ctx.update.message.text;
        ctx.session.tagEditor.tags.year = year;

        if (Number.isNaN(Number(year))) {
          message = 'You entered a string instead of a number. While this is not a problem, but I guess you entered this value by mistake. However, If you want to preview your changes click /preview.\n\nClick /done to save your changes.';
        } else {
          message = 'Year changed. If you want to preview your changes click /preview.\n\nClick /done to save your changes.';
        }
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

  const fileId = ctx.update.message.audio.file_id;
  const url = `bot${config.BOT_TOKEN}/getFile?file_id=${fileId}`;

  downloader(ctx, url, 'audio')
    .then(({ downloadPath, fileName }) => {
      mm.parseFile(`${downloadPath}/${fileName}`, { native: true })
        .then((metadata) => {
          const {
            artist,
            title,
            album,
            genre,
            year,
          } = metadata.common;

          ctx.session.tagEditor.musicPath = `${downloadPath}/${fileName}`;

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
        }).catch((err) => {
          console.log(err);
          ctx.reply(ERR_ON_READING_TAGS)
            .then(() => {
            }).catch((err) => {
              console.log(err);
            });
        });
    })
    .catch(((err) => {
      console.log(err);
      ctx.reply(ERR_ON_DOWNLOAD_MESSAGE)
        .then(() => {
        }).catch((err) => {
          console.log(err);
        });
    }));
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
  .then(() => {
    console.log('Bot started successfully!');
  })
  .catch((err) => {
    console.log(`Error lunching the bot: ${err.name}: ${err.message}`);
  });
