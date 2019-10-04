const fs = require('fs');
const mm = require('music-metadata');
const isPng = require('is-png');
const isJpg = require('is-jpg');

const BASE_DIR = `${__dirname}/../user_data`;

const hasAlbumArt = (metadata) => (Object.prototype.hasOwnProperty.call(metadata.common, 'picture')
                                  && (isPng(metadata.common.picture[0].data
                                    || isJpg(metadata.common.picture[0].data))));

const extractAlbumArt = (ctx, metadata) => {
  if (!hasAlbumArt(metadata)) {
    return {
      message: 'No album art!',
      path: undefined,
    };
  }
  const userId = ctx.update.message.from.id;
  const albumArt = metadata.common.picture[0].data;
  const fileName = `${BASE_DIR}/${userId}/album-art.${isPng(albumArt) ? 'png' : 'jpg'}`;

  // fs.writeFile(fileName, albumArt, (err) => {
  //   if (err) {
  //     // reject(new Error(`Error creating a temp album art: ${err.name}: ${err.message}`));
  //   } else {
  //     return {
  //       message: `Album art successfully extracted to ${BASE_DIR}/${userId}`,
  //       path: `${BASE_DIR}/${userId}/${fileName}`,
  //       fileName,
  //     };
  //   }
  // });

  fs.writeFileSync(fileName, albumArt);

  return {
    message: `Album art successfully extracted to ${BASE_DIR}/${userId}`,
    path: `${BASE_DIR}/${userId}/${fileName}`,
  };
};

function updateAlbumArt(musicPath, albumArtPath) {
  return new Promise((resolve, reject) => {
    mm.parseFile(musicPath, { native: true })
      .then((metadata) => {
        fs.readFile(albumArtPath, (err, data) => {
          if (err) {
            reject(new Error(`Couldn't read file: ${err.name}: ${err.message}`));
          } else {
            metadata.common.picture[0].data = data;
            resolve(musicPath);
          }
        });
      });
  });
}

module.exports = {
  hasAlbumArt,
  extractAlbumArt,
  updateAlbumArt,
};
