from typing import Callable, Optional
from .types import Update
from .context import Context
from .filters import BaseFilter

class Handler:
    async def handle(self, update: Update, context: Context):
        raise NotImplementedError

    def check_update(self, update: Update) -> bool:
        raise NotImplementedError

class CommandHandler(Handler):
    def __init__(self, command: str, callback: Callable, filters: Optional[BaseFilter] = None):
        self.command = command.lstrip('/')
        self.callback = callback
        self.filters = filters

    def check_update(self, update: Update) -> bool:
        if not update.message:
            return False
        if not update.message.text:
            return False
        text = update.message.text
        if not text.startswith('/'):
            return False
        parts = text.split()
        cmd = parts[0].lstrip('/')
        if cmd != self.command:
            return False
        if self.filters is not None:
            return self.filters(update.message)
        return True

    async def handle(self, update: Update, context: Context):
        text = update.message.text
        args = text.split()[1:] if text else []
        context.args = args
        await self.callback(update, context)

class MessageHandler(Handler):
    def __init__(self, filters: BaseFilter, callback: Callable):
        self.filters = filters
        self.callback = callback

    def check_update(self, update: Update) -> bool:
        if not update.message:
            return False
        return self.filters(update.message)

    async def handle(self, update: Update, context: Context):
        await self.callback(update, context)

class CallbackQueryHandler(Handler):
    def __init__(self, pattern: Optional[str], callback: Callable):
        self.pattern = pattern
        self.callback = callback

    def check_update(self, update: Update) -> bool:
        if not update.callback_query:
            return False
        if self.pattern is None:
            return True
        data = update.callback_query.data
        if data is None:
            return False
        return self.pattern in data

    async def handle(self, update: Update, context: Context):
        await self.callback(update, context)