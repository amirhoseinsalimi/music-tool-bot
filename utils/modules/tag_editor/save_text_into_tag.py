from telegram.ext import CallbackContext


def save_text_into_tag(
        value: str,
        current_tag: str,
        context: CallbackContext,
        is_number: bool = False
) -> None:
    """Store a value of the given tag in the corresponding context.

    **Keyword arguments:**
     - value (str) -- The value to be stored as the value of `current_tag`
     - current_tag (str) -- The key to store the value into
     - context (CallbackContext) -- The context of a user to store the key:value pair into
    """
    if is_number:
        if isinstance(int(value), int):
            context.user_data['tag_editor'][current_tag] = value
        else:
            context.user_data['tag_editor'][current_tag] = 0
    else:
        context.user_data['tag_editor'][current_tag] = value