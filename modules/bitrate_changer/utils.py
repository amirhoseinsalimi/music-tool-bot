import re


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
