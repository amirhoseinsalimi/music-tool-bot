def generate_music_info(tag_editor_context: dict) -> str:
    return (
        f"*🗣 Artist:* {tag_editor_context['artist'] if tag_editor_context['artist'] else '-'}\n"
        f"*🎵 Title:* {tag_editor_context['title'] if tag_editor_context['title'] else '-'}\n"
        f"*🎼 Album:* {tag_editor_context['album'] if tag_editor_context['album'] else '-'}\n"
        f"*🎹 Genre:* {tag_editor_context['genre'] if tag_editor_context['genre'] else '-'}\n"
        f"*📅 Year:* {tag_editor_context['year'] if tag_editor_context['year'] else '-'}\n"
        f"*💿 Disk Number:* {tag_editor_context['disknumber'] if tag_editor_context['disknumber'] else '-'}\n"
        f"*▶️ Track Number:* {tag_editor_context['tracknumber'] if tag_editor_context['tracknumber'] else '-'}\n\n"
        "🆔 {}\n"
    )
