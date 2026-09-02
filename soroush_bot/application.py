import asyncio
import logging
from typing import List, Optional
from .handlers import Handler
from .context import Context
from .client import SoroushClient
from .types import Update

logger = logging.getLogger(__name__)

class Application:
    def __init__(self, token: str, client_class=None):
        self.token = token
        self.client_class = client_class or SoroushClient
        self.bot = None
        self.handlers = []
        self._update_offset = 0
        self.running = False

    def add_handler(self, handler: Handler):
        self.handlers.append(handler)

    async def initialize(self):
        self.bot = self.client_class(self.token)
        try:
            me = await self.bot.get_me()
            logger.info(f"Bot initialized as {me.username}")
        except Exception as e:
            logger.error(f"Failed to initialize bot: {e}")
            raise

    async def process_update(self, update: Update):
        if update.message:
            update.message._bot = self.bot
        if update.callback_query:
            update.callback_query._bot = self.bot
            if update.callback_query.message:
                update.callback_query.message._bot = self.bot

        context = Context(self.bot, update)
        for handler in self.handlers:
            if handler.check_update(update):
                try:
                    await handler.handle(update, context)
                except Exception as e:
                    logger.error(f"Error in handler: {e}")
                break

    async def _run_polling(self, timeout: int = 30, limit: int = 100):
        await self.initialize()
        self.running = True
        logger.info("Started polling")
        try:
            while self.running:
                try:
                    updates = await self.bot.get_updates(
                        offset=self._update_offset,
                        limit=limit,
                        timeout=timeout
                    )
                    for update in updates:
                        await self.process_update(update)
                        self._update_offset = update.update_id + 1
                except Exception as e:
                    logger.error(f"Error in polling loop: {e}")
                    await asyncio.sleep(1)
        finally:
            if self.bot:
                await self.bot.close()
                logger.info("Polling stopped and client closed")

    def run_polling(self, timeout: int = 30, limit: int = 100):
        try:
            asyncio.run(self._run_polling(timeout, limit))
        except KeyboardInterrupt:
            logger.info("Polling stopped by user")
        finally:
            self.stop()

    def stop(self):
        self.running = False