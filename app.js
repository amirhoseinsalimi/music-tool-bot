/* Built-in Node.js modules */
const fs = require('fs');
const {execSync} = require("child_process");


/* Third-part Node.js modules */
const axios = require('axios');
const download = require('download');
const mkdirp = require('mkdirp');
const NodeID3 = require('node-id3');


/* Import Telegraf and its middlewares */
const Telegraf = require('telegraf');
const Extra = require('telegraf/extra');
const Markup = require('telegraf/markup');
const TelegrafInlineMenu = require('telegraf-inline-menu');


/* Global variables */
const token = '932660872:AAEZcszl7iBsthPVipj_a7_M9BNUKGDW80A';
const dirname = __dirname + '/user_data/';

let currentTag = '';
let currentMusic = '';
let artistName = undefined;
let albumName = undefined;
let titleName = undefined;


/* Bot configuration */
const bot = new Telegraf(token);


/* Bot commands */
bot.start(ctx => {
  const userId = ctx.update.message.from.id;

  mkdirp(`${dirname}/${userId}`, (err) => {
    if (err) {
      console.log(`Error lunching the bot: ${err.name}: ${err.message}`);
      ctx.reply('Bot Error!');
    } else {
      console.log('Dir ready to use!');
    }
  });

  ctx.reply('Hello there! 👋\nLet\'s get started. Just send me a music and see how awesome I am!')
});

bot.help(ctx =>
  ctx.reply('It\'s simple! Just send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁')
);


/* Catch Audio files */
bot.on('audio', ctx => {
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
    .then(res => {
      const filePath = res.data.result.file_path;
      const fileName = filePath.split('/')[1];
      const fileId = res.data.result.file_id;
      const url = `file/bot${token}/${filePath}`;

      axios({
        url,
        method: 'get',
        baseURL: 'https://api.telegram.org',
        responseType: 'blob',
      })
        .then(res => {
          download(`https://api.telegram.org/${url}`, `${dirname}/${userId}`)
            .then(() => {
              const tags = NodeID3.read(`${dirname}/${userId}/${fileName}`);
              const {
                artist,
                album,
                title,
              } = tags;

              artistName = artist;
              albumName = album;
              titleName = title;

              console.log(artist, album, title);

              currentMusic = `${dirname}/${userId}/${fileName}`.toString();

              const firstReply = "ℹ️ MP3 Info:\n\n" +
                `👤 Artist: ${artistName}\n` +
                `🎼 Album: ${albumName}\n` +
                `🎵 Title: ${titleName}\n` +
                "\nWhich tag do you want to edit?";

              ctx.reply(firstReply, Markup
                .keyboard([
                  ['👤 Artist', '🎼 Album'],
                  ['🎵 Title'],
                  // ['📢 Ads', '⭐️ Rate us', '👥 Share']
                ])
                .resize()
                .extra()
              );
            })
            .catch(err => {
              console.log(`Error downloading the music: ${err.name}: ${err.message}`);
            });
        })
        .catch(err => {
          console.log(`Error getting blob: ${err.name}: ${err.message}`);
        });
    })
    .catch(err => {
      console.log(`Error getting JSON: ${err.name}: ${err.message}`);
    });
});


bot.hears('👤 Artist', ctx => {
  if (currentMusic === '') {
    console.log('Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁');
  } else {
    currentTag = 'artist';
    ctx.reply('Enter the name of the Artist:')
  }
});

bot.hears('🎼 Album', ctx => {
  if (currentMusic === '') {
    console.log('Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁')
  } else {
    currentTag = 'album';
    return ctx.reply('Enter the name of the Album:')
  }
});

bot.hears('🎵 Title', ctx => {
  if (currentMusic === '') {
    console.log('Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁');
  } else {
    currentTag = 'title';
    return ctx.reply('Enter the Title of the music:')
  }
});


bot.command('done', (ctx) => {
  const tags = {
    artist: artistName,
    album: albumName,
    title: titleName,
  };

  console.log('/done');

  fs.readFile(currentMusic, (err, data) => {
    if (err) {
      console.log(`Error reading the file: ${err.name}: ${err.message}`);
      ctx.reply('Bot Error!');
    } else {
      NodeID3.update(tags, currentMusic, (err, buffer) => {
        if (err) {
          console.log(`Error updating tags: ${err.name}: ${err.message}`);
          ctx.reply('Bot Error!');
        } else {
          console.log('updated');
          ctx.telegram.sendDocument(ctx.from.id, {
            source: currentMusic,
            filename: `@MusicToolBot_${tags.artist}_${tags.title}.mp3`
          })
            .then(() => {
              currentMusic = '';
              artistName = undefined;
              albumName = undefined;
              titleName = undefined;

              console.log('Finished!');
            })
            .catch((err) => {
              console.log(`Error reading the file: ${err.name}: ${err.message}`);
            });
        }
      });
    }
  })
});


bot.on('text', ctx => {
  if (currentTag === 'artist') {
    artistName = ctx.update.message.text;
    return ctx.reply('Artist name changed. If you\'re finished click /done');
  } else if (currentTag === 'album') {
    albumName = ctx.update.message.text;
    return ctx.reply('Album name changed. If you\'re finished click /done');
  } else if (currentTag === 'title') {
    titleName = ctx.update.message.text;
    return ctx.reply('Music title changed. If you\'re finished click /done');
  } else {
    return ctx.reply('Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁');
  }
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
], ctx => {
  ctx.reply('Send or forward me an audio track, an MP3 file or a music. I\'m waiting... 😁');
});


/* Launch bot! */
bot.launch()
  .catch((err) => {
    console.log(`Error lunching the bot: ${err.name}: ${err.message}`);
  });
