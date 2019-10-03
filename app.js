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
const { hasAlbumArt, extractAlbumArt } = require('./my_modules/album-arter');
const config = require('./my_modules/config');


/* Global variables */
const dirname = `${__dirname}/user_data/`;


/* Bot configuration */
const bot = new Telegraf(config.BOT_TOKEN);


/* Messages */
const START_MESSAGE = 'Hello there! 👋\nLet\'s get started. Just send me a music and see how awesome I am!';
const HELP_MESSAGE = 'It\'s simple! Just send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁';
const DEFAULT_MESSAGE = 'Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁';
const ASK_WHICH_TAG = 'Which tag do you want to edit?';
const EXPECTED_NUMBER_MESSAGE = 'You entered a string instead of a number. Although this is not a problem, I guess you entered this input by mistake.';
const CLICK_PREVIEW_MESSAGE = 'If you want to preview your changes click /preview.';
const CLICK_DONE_MESSAGE = 'Click /done to save your changes.';


/* Error Messages */
const REPORT_BUG_MESSAGE = 'That\'s my fault!. This bug will be reported and fixed very soon!';
const REPORT_CREATING_USER_FOLDER = `Error initializing myself for you... ${REPORT_BUG_MESSAGE}`;
const ERR_ON_DOWNLOAD_MP3_MESSAGE = `Sorry, I could't download your file... ${REPORT_BUG_MESSAGE}`;
const ERR_ON_DOWNLOAD_PHOTO_MESSAGE = `Sorry, I could't download your file... ${REPORT_BUG_MESSAGE}`;
const ERR_ON_READING_TAGS = `Sorry, I could't read the tags of the file... ${REPORT_BUG_MESSAGE}`;
const ERR_ON_UPDATING_TAGS = `Sorry, I could't tags the tags of the file... ${REPORT_BUG_MESSAGE}`;


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
      console.error(`Error creating user directory: ${err.name}: ${err.message}`);
      message = REPORT_CREATING_USER_FOLDER;
    } else {
      message = START_MESSAGE;
    }

    return ctx.reply(message, Extra.markup((m) => m.removeKeyboard()));
  });
});

bot.help((ctx) => ctx.reply(HELP_MESSAGE));


bot.hears('🗣 Artist', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = DEFAULT_MESSAGE;
  } else {
    ctx.session.tagEditor.currentTag = 'artist';
    message = 'Enter the name of the Artist:';
  }

  return ctx.reply(message);
});

bot.hears('🎵 Title', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = DEFAULT_MESSAGE;
  } else {
    ctx.session.tagEditor.currentTag = 'title';
    message = 'Enter the Title of the music:';
  }

  return ctx.reply(message);
});

bot.hears('🎼 Album', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = DEFAULT_MESSAGE;
  } else {
    ctx.session.tagEditor.currentTag = 'album';
    message = 'Enter the name of the Album:';
  }

  return ctx.reply(message);
});

bot.hears('🎹 Genre', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = DEFAULT_MESSAGE;
  } else {
    ctx.session.tagEditor.currentTag = 'genre';
    message = 'Enter the Genre:';
  }

  return ctx.reply(message);
});

bot.hears('📅 Year', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = DEFAULT_MESSAGE;
  } else {
    ctx.session.tagEditor.currentTag = 'year';
    message = 'Enter the publish Year:';
  }

  return ctx.reply(message);
});

bot.hears('🖼 Album Art', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = DEFAULT_MESSAGE;
  } else {
    ctx.session.tagEditor.currentTag = 'album-art';
    message = 'Now send me a photo:';
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
          console.error(`Error reading the file: ${err.name}: ${err.message}`);
          return ctx.reply('Oops! Did you forget to send me a file? 🤔');
        }
        NodeID3.update(tags, musicPath, (err) => {
          if (err) {
            console.error(`Error updating tags: ${err.name}: ${err.message}`);
            return ctx.reply(ERR_ON_UPDATING_TAGS);
          }

          const image = { image: ctx.session.tagEditor.tags.albumArt.tempAlbumArt };

          NodeID3.update(image, musicPath, (err) => {
            if (err) {
              console.error(`Error updating tags: ${err.name}: ${err.message}`);
              return ctx.reply(ERR_ON_UPDATING_TAGS);
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
                    console.error(`Error deleting the file: ${err.name}: ${err.message}`);
                  }
                });
              })
              .catch((err) => {
                console.error(`Error reading the file: ${err.name}: ${err.message}`);
              });
          });
        });
      });
    } else {
      return ctx.reply(DEFAULT_MESSAGE);
    }
  } else {
    return ctx.reply(DEFAULT_MESSAGE);
  }
});


bot.command('preview', (ctx) => {
  if (ctx.session.tagEditor) {
    const musicPath = ctx.session.tagEditor.musicPath || undefined;

    if (musicPath) {
      return ctx.reply('ℹ️ Modified MP3 Info:\n\n'
        + `🗣 Artist: ${ctx.session.tagEditor.tags.artist}\n`
        + `🎵 Title: ${ctx.session.tagEditor.tags.title}\n`
        + `🎼 Album: ${ctx.session.tagEditor.tags.album}\n`
        + `🎹 Genre: ${ctx.session.tagEditor.tags.genre}\n`
        + `📅 Year: ${ctx.session.tagEditor.tags.year}\n`
        + `🖼 Album Art: ${ctx.session.tagEditor.tags.albumArt.exists ? 'Included' : 'Not Included'}\n`
        // + `\n${ASK_WHICH_TAG}`
        + `\n${CLICK_DONE_MESSAGE} Or feel free to continue editing tags.`);
    }
    return ctx.reply(DEFAULT_MESSAGE);
  }
  return ctx.reply(DEFAULT_MESSAGE);
});


bot.on('text', (ctx) => {
  let message;

  if (!ctx.session.tagEditor) {
    message = DEFAULT_MESSAGE;
  } else if (ctx.session.tagEditor) {
    if (ctx.session.tagEditor.currentTag) {
      const { currentTag } = ctx.session.tagEditor;

      if (currentTag === 'artist') {
        ctx.session.tagEditor.tags.artist = ctx.update.message.text;
        message = `Artist name changed. ${CLICK_PREVIEW_MESSAGE}\n\n${CLICK_DONE_MESSAGE}`;
      } else if (currentTag === 'title') {
        ctx.session.tagEditor.tags.title = ctx.update.message.text;
        message = `Title name changed. ${CLICK_PREVIEW_MESSAGE}\n\n${CLICK_DONE_MESSAGE}`;
      } else if (currentTag === 'album') {
        ctx.session.tagEditor.tags.album = ctx.update.message.text;
        message = `Album name changed. ${CLICK_PREVIEW_MESSAGE}\n\n${CLICK_DONE_MESSAGE}`;
      } else if (currentTag === 'genre') {
        ctx.session.tagEditor.tags.genre = ctx.update.message.text;
        message = `Genre changed. ${CLICK_PREVIEW_MESSAGE}\n\n${CLICK_DONE_MESSAGE}`;
      } else if (currentTag === 'year') {
        const year = ctx.update.message.text;
        ctx.session.tagEditor.tags.year = ctx.update.message.text;

        if (Number.isNaN(Number(year))) {
          message = `${EXPECTED_NUMBER_MESSAGE} ${CLICK_PREVIEW_MESSAGE}\n\n${CLICK_DONE_MESSAGE}`;
        } else {
          message = `Year changed. ${CLICK_PREVIEW_MESSAGE}\n\n${CLICK_DONE_MESSAGE}`;
        }
      }
    } else {
      message = 'Please select the tag you want to edit! 😅';
    }
  } else {
    message = DEFAULT_MESSAGE;
  }

  return ctx.reply(message);
});


/* Catch audio files */
bot.on('audio', (ctx) => {
  ctx.session.tagEditor = {};
  ctx.session.tagEditor.tags = {};
  ctx.session.tagEditor.tags.albumArt = {
    exists: false,
    data: '',
  };

  downloader(ctx, 'audio')
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

          ctx.session.tagEditor.tags.albumArt = {
            exists: hasAlbumArt(metadata),
            data: `${extractAlbumArt(ctx, metadata).path}`,
          };

          ctx.session.tagEditor.currentTag = '';

          const firstReply = 'ℹ️ MP3 Info:\n\n'
            + `🗣 Artist: ${ctx.session.tagEditor.tags.artist}\n`
            + `🎵 Title: ${ctx.session.tagEditor.tags.title}\n`
            + `🎼 Album: ${ctx.session.tagEditor.tags.album}\n`
            + `🎹 Genre: ${ctx.session.tagEditor.tags.genre}\n`
            + `📅 Year: ${ctx.session.tagEditor.tags.year}\n`
            + `🖼 Album Art: ${ctx.session.tagEditor.tags.albumArt.exists ? 'Included' : 'Not Included'}\n`
            + `\n${ASK_WHICH_TAG}`;

          return ctx.reply(firstReply, Markup
            .keyboard([
              ['🗣 Artist', '🎵 Title', '🎼 Album'],
              ['🎹 Genre', '📅 Year', '🖼 Album Art'],
            ])
            .resize()
            .extra());
        }).catch((err) => {
          console.error(`Error reading tags: ${err.name}: ${err.message}`);
          ctx.reply(ERR_ON_READING_TAGS)
            .then(() => {
            }).catch((err) => {
              console.error(err);
            });
        });
    })
    .catch(((err) => {
      console.error(err);
      ctx.reply(ERR_ON_DOWNLOAD_MP3_MESSAGE)
        .then(() => {
        }).catch((err) => {
          console.error(err);
        });
    }));
});


/* Catch photos */
bot.on('photo', (ctx) => {
  let message;

  if (ctx.session.tagEditor) {
    if (ctx.session.tagEditor.currentTag) {
      if (ctx.session.tagEditor.currentTag === 'album-art') {
        ctx.session.tagEditor.tags.albumArt.tempAlbumArt = '';

        downloader(ctx, 'photo')
          .then(({ downloadPath, fileName }) => {
            ctx.session.tagEditor.tags.albumArt = {
              tempAlbumArt: `${downloadPath}/${fileName}`,
            };

            message = `Album art changed! ${CLICK_PREVIEW_MESSAGE}\n\n${CLICK_DONE_MESSAGE}`;
            return ctx.reply(message)
              .then(() => {
              }).catch((err) => {
                console.error(err);
              });
          })
          .catch(((err) => {
            console.error(err);
            return ctx.reply(ERR_ON_DOWNLOAD_PHOTO_MESSAGE)
              .then(() => {
              }).catch((err) => {
                console.error(err);
              });
          }));
      } else {
        message = DEFAULT_MESSAGE;
      }
    } else {
      message = DEFAULT_MESSAGE;
    }
  } else {
    message = DEFAULT_MESSAGE;
  }

  return ctx.reply(message)
    .then(() => {
    }).catch((err) => {
      console.error(err);
    });
});


/* Replies to anything except audio files */
bot.on([
  'video',
  'video_note',
  'document',
  'game',
  'animation',
  'sticker',
  'voice',
  'contact',
  'location',
  'poll',
  'venue',
], (ctx) => ctx.reply(DEFAULT_MESSAGE));


/* Launch bot! */
bot.launch()
  .then(() => {
    console.log('Bot started successfully!');
  })
  .catch((err) => {
    console.error(`Error launching the bot: ${err.name}: ${err.message}`);
  });
