def generate_music_info(tag_editor_context: dict) -> str:
    """Generate the details of the music based on the values in `tag_editor_context`
    dictionary

    **Keyword arguments:**
     - tag_editor_context (dict) -- The context object of the user

    **Returns:**
     `str`
    """
    ctx = tag_editor_context

    return (
        f"*🗣 Artist:* {ctx['artist'] if ctx['artist'] else '-'}\n"
        f"*🎵 Title:* {ctx['title'] if ctx['title'] else '-'}\n"
        f"*🎼 Album:* {ctx['album'] if ctx['album'] else '-'}\n"
        f"*🎹 Genre:* {ctx['genre'] if ctx['genre'] else '-'}\n"
        f"*📅 Year:* {ctx['year'] if ctx['year'] else '-'}\n"
        f"*💿 Disk Number:* {ctx['disknumber'] if ctx['disknumber'] else '-'}\n"
        f"*▶️ Track Number:* {ctx['tracknumber'] if ctx['tracknumber'] else '-'}\n"
        "{}\n"
    )