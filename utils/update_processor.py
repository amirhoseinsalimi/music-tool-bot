"""Bounded concurrent update processing with same-user serialization."""

import asyncio
from typing import Any, Awaitable

from telegram.ext import BaseUpdateProcessor


class UserUpdateProcessor(BaseUpdateProcessor):
    """Process a few users at once while serializing each user's updates."""

    _LOCK_STRIPES = 64

    def __init__(self, max_concurrent_updates: int = 4) -> None:
        super().__init__(max_concurrent_updates)
        self._user_locks = tuple(asyncio.Lock() for _ in range(self._LOCK_STRIPES))
        self._anonymous_lock = asyncio.Lock()

    async def do_process_update(self, update: Any, coroutine: Awaitable[Any]) -> None:
        user = getattr(update, 'effective_user', None)
        chat = getattr(update, 'effective_chat', None)
        user_id = getattr(user, 'id', None)
        key = user_id if user_id is not None else getattr(chat, 'id', None)
        if key is None:
            async with self._anonymous_lock:
                await coroutine
            return

        async with self._user_locks[key % self._LOCK_STRIPES]:
            await coroutine

    async def initialize(self) -> None:
        """No resources need initialization."""

    async def shutdown(self) -> None:
        """No resources need shutdown."""
