import re


def get_list_limit(message: str) -> int | None:
    number_pattern = r'\d+'

    limit = re.findall(number_pattern, message)

    if len(limit):
        limit = int(limit[0])
    else:
        limit = None

    return limit


def extract_user_id(message: str) -> str:
    """
    Extracts and returns the user ``id`` of `/{add/del}admin` commands.

    The `message` is expected to look like ``/addadmin <user_id>``.

    :param message: str: The ``/{add/del}admin`` command containing a user ``id``
    :return: int: The normalized user's ``id``
    """
    return message.partition(' ')[2]
