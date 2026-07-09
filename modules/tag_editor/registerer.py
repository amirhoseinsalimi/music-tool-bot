from telegram.ext import (
    CommandHandler,
    MessageHandler,
    BaseHandler,
    filters,
)

from .handlers import (
    finish_editing_tags,
    display_preview,
    handle_photo_message,
    ask_for_tag,
    ask_which_tag_to_edit,
)


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
                    filters.Regex('^(🎵 محرّر الوسوم/الصور)$') |
                    filters.Regex('^(🎵 टैग/आर्ट एडिटर)$') |
                    filters.Regex('^(🎵 Editor Tag/Sampul)$')
            ),
            ask_which_tag_to_edit
        ),
        MessageHandler(
            (
                    filters.Regex('^(🎵 Title|🎵 عنوان|🎵 Название|🎵 Título|🎵 Titre|🎵 العنوان|🎵 शीर्षक|🎵 Judul)$') |
                    filters.Regex('^(🗣 Artist|🗣 آرتیست|🗣 Исполнитель|🗣 Artista|🗣 Artiste|🗣 الفنان|🗣 कलाकार|🗣 Artis)$') |
                    filters.Regex('^(🎼 Album|🎼 آلبوم|🎼 Альбом|🎼 Álbum|🎼 Album|🎼 الألبوم|🎼 एल्बम|🎼 Album)$') |
                    filters.Regex('^(🎹 Genre|🎹 سبک|🎹 Жанр|🎹 Género|🎹 Genre|🎹 النوع|🎹 शैली|🎹 Genre)$') |
                    filters.Regex(
                        '^(🖼 Album Art|🖼 عکس آلبوم|🖼 Обложка альбома|🖼 Portada del Álbum|🖼 Pochette|🖼 صورة الألبوم'
                        '|🖼 एल्बम आर्ट|🖼 Sampul Album)$') |
                    filters.Regex(
                        '^(🧹 Remove Album Art|🧹 حذف عکس آلبوم|🧹 Удалить обложку|🧹 Eliminar Portada'
                        '|🧹 Supprimer la pochette|🧹 إزالة صورة الألبوم|🧹 एल्बम आर्ट हटाएँ|🧹 Hapus Sampul Album)$') |
                    filters.Regex('^(📅 Year|📅 سال|📅 Год|📅 Año|📅 Année|📅 السنة|📅 वर्ष|📅 Tahun)$') |
                    filters.Regex(
                        '^(💿 Disk Number|💿 شماره دیسک|💿 Номер диска|💿 Número de Disco|💿 Numéro de disque'
                        '|💿 رقم القرص|💿 डिस्क नंबर|💿 Nomor Disk)$') |
                    filters.Regex(
                        '^(▶️ Track Number|▶️ شماره ترک|▶️ Номер трека|▶️ Número de Pista|▶️ Numéro de piste'
                        '|▶️ رقم المقطع|▶️ ट्रैक नंबर|▶️ Nomor Trek)$')
            ),
            ask_for_tag
        )
    ]


def register(add_handler):
    """
    Register handlers using the host app's add_handler callable.
    """
    for h in registry():
        add_handler(h)
