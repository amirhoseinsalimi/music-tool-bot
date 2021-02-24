from telegram.ext import CallbackContext

def save_text_into_tag(value: str, current_tag: str, context: CallbackContext) -> None:
    # TODO: Check if the value is of the correct type
    context.user_data['tag_editor'][current_tag] = value