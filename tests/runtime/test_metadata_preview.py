"""Actual core preview, edit and save handlers, without Telegram or database writes."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
import modules.core.handlers  # Match the application's existing import order.
from modules.tag_editor.handlers import display_preview, handle_tag_editor, finish_editing_tags
from modules.tag_editor.registerer import registry
from modules.tag_editor.utils import generate_tag_editor_keyboard
from utils import t
from telegram.ext import MessageHandler


def inner(handler):
    while hasattr(handler, '__wrapped__'):
        handler = handler.__wrapped__
    return handler


class MetadataPreviewTests(unittest.TestCase):
    def test_preview_handles_callback_updates_and_exposes_localized_edit_preview_save_keyboard(self):
        async def run():
            for lang in ('en','fa','ru','es','fr','ar','hi','id'):
                message=SimpleNamespace(message_id=99, reply_text=AsyncMock(), reply_photo=AsyncMock())
                update=SimpleNamespace(message=None,effective_message=message)
                data={'language':lang,'music_path':'owned-song.mp3','tag_editor':{'artist':'Artist','title':'<unsafe>','year':'2019'}}
                await inner(display_preview)(update,SimpleNamespace(user_data=data))
                reply=message.reply_text.call_args.kwargs
                self.assertIn('&lt;unsafe&gt;',reply['text'])
                labels=[button.text for row in reply['reply_markup'].keyboard for button in row]
                self.assertIn(t(lang,'btnPreviewTags'),labels)
                self.assertIn(t(lang,'btnSaveTags'),labels)
                self.assertIn(t(lang,'btnArtist'),labels)
                self.assertNotIn('missing translation',str(labels))
                for key, name in [('btnPreviewTags','display_preview'),('btnSaveTags','finish_editing_tags')]:
                    matching=[h for h in registry() if isinstance(h,MessageHandler) and h.callback.__name__==name and h.filters.filter(SimpleNamespace(text=t(lang,key)))]
                    self.assertTrue(matching, (lang,key))
        asyncio.run(run())

    def test_edit_then_save_uses_current_draft_and_resets_only_after_sending(self):
        async def run():
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'song.mp3';path.write_bytes(b'input')
                message=SimpleNamespace(text='My final title',message_id=100,chat_id=42,reply_text=AsyncMock())
                uploading=SimpleNamespace(delete=AsyncMock());message.reply_text.return_value=uploading
                user=SimpleNamespace(user_id=42)
                data={'user':user,'language':'en','music_path':str(path),'music_message_id':3,'music_duration':60,
                      'current_module':'tag_editor','tag_editor':{'artist':'Recognized artist','title':'Suggested','current_tag':'title'}}
                context=SimpleNamespace(user_data=data,bot=SimpleNamespace(send_audio=AsyncMock(),send_chat_action=AsyncMock()))
                update=SimpleNamespace(message=message,effective_message=message)
                await inner(handle_tag_editor)(update,context)
                self.assertEqual(data['tag_editor']['title'],'My final title')
                with patch('modules.tag_editor.handlers.save_tags_to_file') as save:
                    await inner(finish_editing_tags)(update,context)
                    self.assertEqual(save.call_args.kwargs['tags']['title'],'My final title')
                self.assertEqual(context.bot.send_audio.call_args.kwargs['title'],'My final title')
                self.assertEqual(context.bot.send_audio.call_args.kwargs['performer'],'Recognized artist')
                self.assertEqual(data['music_path'],'')
                self.assertEqual(data['language'],'en')
        asyncio.run(run())

    def test_failed_upload_keeps_the_editable_draft_for_retry(self):
        from telegram.error import TelegramError
        async def run():
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'song.mp3';path.write_bytes(b'input')
                message=SimpleNamespace(message_id=100,chat_id=42,reply_text=AsyncMock())
                data={'user':SimpleNamespace(user_id=42),'language':'en','music_path':str(path),
                      'music_message_id':3,'music_duration':60,'tag_editor':{'title':'Final edit','artist':'Artist'}}
                context=SimpleNamespace(user_data=data,bot=SimpleNamespace(send_audio=AsyncMock(side_effect=TelegramError('test upload failure')),send_chat_action=AsyncMock()))
                update=SimpleNamespace(message=message,effective_message=message)
                with patch('modules.tag_editor.handlers.save_tags_to_file'),patch('modules.tag_editor.handlers.logger'):
                    await inner(finish_editing_tags)(update,context)
                self.assertEqual(data['music_path'],str(path))
                self.assertEqual(data['tag_editor']['title'],'Final edit')
        asyncio.run(run())

if __name__=='__main__':unittest.main()
