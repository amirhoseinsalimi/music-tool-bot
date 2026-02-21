import re

from telegram import ReplyKeyboardMarkup


def generate_bitrate_selector_keyboard(language: str) -> ReplyKeyboardMarkup:
    """
    Create and returns an instance of ``bitrate_selector_keyboard`` with the specified language

    :param language: str: The language to generate the labels
    :return: ReplyKeyboardMarkup: Bitrate selector keyboard
    """
    return (
        ReplyKeyboardMarkup(
            keyboard=[
                [
                    '128 kb/s',
                    '192 kb/s',
                ],
                [

                    '256 kb/s',
                    '320 kb/s',
                ],
                [
                    t(language, 'btnBack')
                ]
            ],
            resize_keyboard=True,
        )
    )


def parse_bitrate_number(message: str) -> int | None:
    """
    Parses, converts and returns a bitrate in a text.

    The ``message`` is expected to look like `320 kb/s`.

    :param message: str: A message text containing a bitrate
    :return: int | None: The extracted bitrate
    """
    number_pattern = r'^\d+'

    matches = re.findall(number_pattern, message)

    if matches:
        return int(matches[0])
    else:
        return None
