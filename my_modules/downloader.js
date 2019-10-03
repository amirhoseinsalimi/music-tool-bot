const download = require('download');
const axios = require('axios');
const config = require('../config');

const BASE_URL = 'https://api.telegram.org';
const BASE_DIR = `${__dirname}/../user_data`;

const downloader = (ctx, fileType) => new Promise((resolve, reject) => {
  const userId = ctx.update.message.from.id;
  const fileId = fileType === 'photo' ? ctx.update.message[fileType][0].file_id : ctx.update.message[fileType].file_id;
  const url = `bot${config.BOT_TOKEN}/getFile?file_id=${fileId}`;

  axios({
    baseURL: BASE_URL,
    url,
    method: 'get',
    responseType: 'json',
  })
    .then((result) => {
      const filePath = result.data.result.file_path;
      const fileName = filePath.split('/')[1];
      const url = `file/bot${config.BOT_TOKEN}/${filePath}`;

      axios({
        baseURL: BASE_URL,
        url,
        method: 'get',
        responseType: 'blob',
      })
        .then(() => {
          download(`${BASE_URL}/${url}`, `${BASE_DIR}/${userId}`)
            .then(() => {
              resolve({
                message: `File successfully downloaded in ${this.downloadPath}`,
                downloadPath: `${BASE_DIR}/${userId}`,
                fileName,
              });
            })
            .catch((err) => {
              reject(new Error(`Error downloading the file: ${err.name}: ${err.message}`));
            });
        })
        .catch((err) => {
          reject(new Error(`Error downloading the file: ${err.name}: ${err.message}`));
        });
    })
    .catch((err) => {
      reject(new Error(`Error downloading the file: ${err.name}: ${err.message}`));
    });
});

module.exports = downloader;
