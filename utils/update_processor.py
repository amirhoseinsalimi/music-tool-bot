"""Bounded concurrent update processing with same-user serialization."""

import asyncio
from typing import Any, Awaitable

from telegram.ext import BaseUpdateProcessor


class UserUpdateProcessor(BaseUpdateProcessor):
    """Process a few users at once while serializing each user's updates."""

    def __init__(self, max_concurrent_updates: int = 4) -> None:
        super().__init__(max_concurrent_updates)
        self._user_locks: dict[tuple[str, int], tuple[asyncio.Lock, int]] = {}
        self._user_locks_guard = asyncio.Lock()

    @staticmethod
    def _user_key(update: Any) -> tuple[str, int]:
        user = getattr(update, 'effective_user', None)
        chat = getattr(update, 'effective_chat', None)
        user_id = getattr(user, 'id', None)
        chat_id = getattr(chat, 'id', None)
        if user_id is not None:
            return ('user', user_id)
        if chat_id is not None:
            return ('chat', chat_id)
        return ('anonymous', 0)

    async def process_update(self, update: Any, coroutine: Awaitable[Any]) -> None:
        """Serialize before taking a global slot, so queued user updates do not starve peers."""
        key = self._user_key(update)
        async with self._user_locks_guard:
            entry = self._user_locks.get(key)
            if entry is None:
                entry = (asyncio.Lock(), 0)
            user_lock, references = entry
            self._user_locks[key] = (user_lock, references + 1)

        try:
            async with user_lock:
                async with self._semaphore:
                    await self.do_process_update(update, coroutine)
        finally:
            async with self._user_locks_guard:
                lock, references = self._user_locks[key]
                if references == 1:
                    del self._user_locks[key]
                else:
                    self._user_locks[key] = (lock, references - 1)

    async def do_process_update(self, update: Any, coroutine: Awaitable[Any]) -> None:
        """Run the update; the per-user lock and global semaphore are held by process_update."""
        await coroutine

    async def initialize(self) -> None:
        """No resources need initialization."""

    async def shutdown(self) -> None:
        """No resources need shutdown."""
