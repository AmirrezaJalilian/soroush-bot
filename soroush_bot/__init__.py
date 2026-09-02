"""
soroush-bot - Async Python client for Soroush Plus Bot API
with python-telegram-bot-like syntax.
"""

from .application import Application
from .handlers import CommandHandler, MessageHandler, CallbackQueryHandler
from .filters import COMMAND, TEXT, PHOTO
from .filters import filters
from .types import (
    Update,
    Message,
    Chat,
    User,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
)
from .context import Context, ContextTypes
from .client import SoroushClient, SoroushPlusAPIError

__all__ = [
    # Core
    "Application",
    "SoroushClient",
    "SoroushPlusAPIError",
    # Handlers
    "CommandHandler",
    "MessageHandler",
    "CallbackQueryHandler",
    # Filters
    "COMMAND",
    "TEXT",
    "PHOTO",
    "filters",
    # Types
    "Update",
    "Message",
    "Chat",
    "User",
    "CallbackQuery",
    "InlineKeyboardButton",
    "InlineKeyboardMarkup",
    "ReplyKeyboardMarkup",
    # Context
    "Context",
    "ContextTypes",
]

__version__ = "1.0.0"
__author__ = "Amirreza Jalilian"
__license__ = "MIT"
__description__ = "Async Python client for Soroush Plus Bot API with python-telegram-bot-like syntax"
__url__ = "https://github.com/AmirrezaJalilian/soroush-bot"