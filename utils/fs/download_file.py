from telegram.ext import CallbackContext


def download_file(user_id: int, file_to_download, file_type: str, context: CallbackContext) -> str:
    """Download a file using convenience methods of "python-telegram-bot"

    **Keyword arguments:**
     - user_id (int) -- The user's id
     - file_to_download (*) -- The file object to download
     - file_type (str) -- The type of the file, either 'photo' or 'audio'
     - context (CallbackContext) -- The context object of the user

    **Returns:**
     The path of the downloaded file
    """
    user_download_dir = f"downloads/{user_id}"
    file_id = ''
    file_extension = ''

    if file_type == 'audio':
        file_id = context.bot.get_file(file_to_download.file_id)
        file_name = file_to_download.file_name
        file_extension = file_name.split(".")[-1]
    elif file_type == 'photo':
        file_id = context.bot.get_file(file_to_download.file_id)
        file_extension = 'jpg'

    file_download_path = f"{user_download_dir}/{file_id.file_id}.{file_extension}"

    try:
        file_id.download(f"{user_download_dir}/{file_id.file_id}.{file_extension}")
    except ValueError as error:
        raise Exception(f"Couldn't download the file with file_id: {file_id}") from error

    return file_download_path