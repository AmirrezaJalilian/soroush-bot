from dataclasses import dataclass
from typing import Optional, List, Any, Dict
from datetime import datetime

@dataclass
class User:
    id: int
    is_bot: bool
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    can_join_groups: Optional[bool] = False
    can_read_all_group_messages: Optional[bool] = False
    supports_inline_queries: Optional[bool] = False

    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in fields}
        return cls(**filtered)

@dataclass
class Chat:
    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Chat':
        fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in fields}
        return cls(**filtered)

@dataclass
class Message:
    message_id: int
    from_user: Optional[User] = None
    chat: Optional[Chat] = None
    date: Optional[datetime] = None
    text: Optional[str] = None
    photo: Optional[List[Any]] = None
    caption: Optional[str] = None
    reply_to_message: Optional['Message'] = None
    _bot = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Message':
        filtered = {}
        for k, v in data.items():
            if k == 'from':
                if isinstance(v, dict):
                    filtered['from_user'] = User.from_dict(v)
                else:
                    filtered['from_user'] = v
            elif k == 'chat' and isinstance(v, dict):
                filtered['chat'] = Chat.from_dict(v)
            elif k == 'reply_to_message' and isinstance(v, dict):
                filtered['reply_to_message'] = Message.from_dict(v)
            else:
                if k in cls.__dataclass_fields__:
                    filtered[k] = v
        if 'from_user' in data and isinstance(data['from_user'], dict):
            filtered['from_user'] = User.from_dict(data['from_user'])
        if 'message_id' not in filtered:
            filtered['message_id'] = data.get('message_id')
        return cls(**filtered)

    async def reply_text(self, text: str, **kwargs) -> 'Message':
        if self._bot is None:
            raise RuntimeError("Bot client not set for this message")
        chat_id = self.chat.id
        return await self._bot.send_message(chat_id, text, **kwargs)

    async def reply_photo(self, photo, caption: Optional[str] = None, **kwargs) -> 'Message':
        if self._bot is None:
            raise RuntimeError("Bot client not set for this message")
        chat_id = self.chat.id
        return await self._bot.send_photo(chat_id, photo, caption=caption, **kwargs)

@dataclass
class CallbackQuery:
    id: str
    from_user: User
    chat_instance: str
    message: Optional[Message] = None
    inline_message_id: Optional[str] = None
    data: Optional[str] = None
    game_short_name: Optional[str] = None
    _bot = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'CallbackQuery':
        filtered = {}
        for k, v in data.items():
            if k == 'from':
                if isinstance(v, dict):
                    filtered['from_user'] = User.from_dict(v)
                else:
                    filtered['from_user'] = v
            elif k == 'message' and isinstance(v, dict):
                filtered['message'] = Message.from_dict(v)
            else:
                if k in cls.__dataclass_fields__:
                    filtered[k] = v
        if 'from_user' in data and isinstance(data['from_user'], dict):
            filtered['from_user'] = User.from_dict(data['from_user'])
        if 'id' not in filtered:
            filtered['id'] = data.get('id')
        return cls(**filtered)

    async def answer(self, text: Optional[str] = None, show_alert: bool = False) -> bool:
        if self._bot is None:
            raise RuntimeError("Bot client not set for this callback query")
        return await self._bot.answer_callback_query(self.id, text, show_alert)

    async def edit_message_text(self, text: str, **kwargs) -> bool:
        if self._bot is None:
            raise RuntimeError("Bot client not set for this callback query")
        if self.message:
            chat_id = self.message.chat.id
            message_id = self.message.message_id
            return await self._bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, **kwargs)
        elif self.inline_message_id:
            return await self._bot.edit_message_text(text, inline_message_id=self.inline_message_id, **kwargs)
        else:
            raise ValueError("No message or inline_message_id to edit")

@dataclass
class Update:
    update_id: int
    message: Optional[Message] = None
    callback_query: Optional[CallbackQuery] = None

    @classmethod
    def from_dict(cls, data: Dict) -> 'Update':
        filtered = {}
        for k, v in data.items():
            if k == 'message' and isinstance(v, dict):
                filtered['message'] = Message.from_dict(v)
            elif k == 'callback_query' and isinstance(v, dict):
                filtered['callback_query'] = CallbackQuery.from_dict(v)
            else:
                if k in cls.__dataclass_fields__:
                    filtered[k] = v
        if 'update_id' not in filtered:
            filtered['update_id'] = data.get('update_id')
        return cls(**filtered)

@dataclass
class InlineKeyboardButton:
    text: str
    callback_data: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"text": self.text}
        if self.callback_data is not None:
            result["callback_data"] = self.callback_data
        if self.url is not None:
            result["url"] = self.url
        return result

@dataclass
class InlineKeyboardMarkup:
    inline_keyboard: List[List[InlineKeyboardButton]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inline_keyboard": [
                [button.to_dict() for button in row]
                for row in self.inline_keyboard
            ]
        }

@dataclass
class ReplyKeyboardMarkup:
    keyboard: List[List[str]]
    resize_keyboard: Optional[bool] = None
    one_time_keyboard: Optional[bool] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {"keyboard": self.keyboard}
        if self.resize_keyboard is not None:
            result["resize_keyboard"] = self.resize_keyboard
        if self.one_time_keyboard is not None:
            result["one_time_keyboard"] = self.one_time_keyboard
        return result