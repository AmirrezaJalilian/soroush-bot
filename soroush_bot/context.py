from typing import Dict, Any

class Context:
    def __init__(self, bot, update, user_data: Dict = None, chat_data: Dict = None):
        self.bot = bot
        self.update = update
        self.user_data = user_data or {}
        self.chat_data = chat_data or {}
        self.args = []

class ContextTypes:
    DEFAULT_TYPE = Context