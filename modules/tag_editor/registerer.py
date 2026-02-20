from telegram.ext import CommandHandler, MessageHandler, BaseHandler, filters

from .handlers import finish_editing_tags, display_preview, handle_photo_message, ask_for_tag, \
    ask_which_tag_to_edit


def registry() -> list[BaseHandler]:
    """
    Build and return this module's handlers.
    """
    return [
        CommandHandler('done', finish_editing_tags),
        CommandHandler('preview', display_preview),
        MessageHandler(filters.PHOTO, handle_photo_message),
        MessageHandler(
            (
                    filters.Regex('^(🎵 Tag/Art Editor)$') |
                    filters.Regex('^(🎵 ادیت تگ/عکس آلبوم)$') |
                    filters.Regex('^(🎵 Редактор тегов/обложки)$') |
                    filters.Regex('^(🎵 Editor de Etiquetas/Portada)$') |
                    filters.Regex('^(🎵 Éditeur Tags/Pochette)$') |
                    filters.Regex('^(🎵 محرّر الوسوم/الصور)$')
            ),
            ask_which_tag_to_edit
        ),
        MessageHandler(
            (
                    filters.Regex('^(🎵 Title)$') | filters.Regex('^(🎵 عنوان)$') | filters.Regex(
                '^(🎵 Название)$') | filters.Regex('^(🎵 Título)$') | filters.Regex('^(🎵 Titre)$') | filters.Regex(
                '^(🎵 العنوان)$') |
                    filters.Regex('^(🗣 Artist)$') | filters.Regex('^(🗣 آرتیست)$') | filters.Regex(
                '^(🗣 Исполнитель)$') | filters.Regex('^(🗣 Artista)$') | filters.Regex('^(🗣 Artiste)$') | filters.Regex(
                '^(🗣 الفنان)$') |
                    filters.Regex('^(🎼 Album)$') | filters.Regex('^(🎼 آلبوم)$') | filters.Regex(
                '^(🎼 Альбом)$') | filters.Regex('^(🎼 Álbum)$') | filters.Regex('^(🎼 Album)$') | filters.Regex(
                '^(🎼 الألبوم)$') |
                    filters.Regex('^(🎹 Genre)$') | filters.Regex('^(🎹 سبک)$') | filters.Regex(
                '^(🎹 Жанр)$') | filters.Regex('^(🎹 Género)$') | filters.Regex('^(🎹 Genre)$') | filters.Regex(
                '^(🎹 النوع)$') |
                    filters.Regex('^(🖼 Album Art)$') | filters.Regex('^(🖼 عکس آلبوم)$') | filters.Regex(
                '^(🖼 Обложка альбома)$') | filters.Regex('^(🖼 Portada del Álbum)$') | filters.Regex(
                '^(🖼 Pochette)$') | filters.Regex('^(🖼 صورة الألبوم)$') |
                    filters.Regex('^(🧹 Remove Album Art)$') | filters.Regex('^(🧹 حذف عکس آلبوم)$') | filters.Regex(
                '^(🧹 Удалить обложку)$') | filters.Regex('^(🧹 Eliminar Portada)$') | filters.Regex(
                '^(🧹 Supprimer la pochette)$') | filters.Regex('^(🧹 إزالة صورة الألبوم)$') |
                    filters.Regex('^(📅 Year)$') | filters.Regex('^(📅 سال)$') | filters.Regex(
                '^(📅 Год)$') | filters.Regex('^(📅 Año)$') | filters.Regex('^(📅 Année)$') | filters.Regex(
                '^(📅 السنة)$') |
                    filters.Regex('^(💿 Disk Number)$') | filters.Regex('^(💿 شماره دیسک)$') | filters.Regex(
                '^(💿 Номер диска)$') | filters.Regex('^(💿 Número de Disco)$') | filters.Regex(
                '^(💿 Numéro de disque)$') | filters.Regex('^(💿 رقم القرص)$') |
                    filters.Regex('^(▶️ Track Number)$') | filters.Regex('^(▶️ شماره ترک)$') | filters.Regex(
                '^(▶️ Номер трека)$') | filters.Regex('^(▶️ Número de Pista)$') | filters.Regex(
                '^(▶️ Numéro de piste)$') | filters.Regex('^(▶️ رقم المقطع)$')
            ),
            ask_for_tag
        )
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.\
    """
    for h in registry():
        add_handler(h)
