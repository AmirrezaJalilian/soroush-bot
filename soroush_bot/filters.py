from typing import Callable, Any
from .types import Message

class BaseFilter:
    def __call__(self, message: Message) -> bool:
        raise NotImplementedError

    def __and__(self, other: 'BaseFilter') -> 'BaseFilter':
        return AndFilter(self, other)

    def __or__(self, other: 'BaseFilter') -> 'BaseFilter':
        return OrFilter(self, other)

    def __invert__(self) -> 'BaseFilter':
        return NotFilter(self)

class AndFilter(BaseFilter):
    def __init__(self, left: BaseFilter, right: BaseFilter):
        self.left = left
        self.right = right
    def __call__(self, message: Message) -> bool:
        return self.left(message) and self.right(message)

class OrFilter(BaseFilter):
    def __init__(self, left: BaseFilter, right: BaseFilter):
        self.left = left
        self.right = right
    def __call__(self, message: Message) -> bool:
        return self.left(message) or self.right(message)

class NotFilter(BaseFilter):
    def __init__(self, filter_obj: BaseFilter):
        self.filter_obj = filter_obj
    def __call__(self, message: Message) -> bool:
        return not self.filter_obj(message)

class CommandFilter(BaseFilter):
    def __call__(self, message: Message) -> bool:
        return message.text is not None and message.text.startswith('/')

class TextFilter(BaseFilter):
    def __call__(self, message: Message) -> bool:
        return message.text is not None

class PhotoFilter(BaseFilter):
    def __call__(self, message: Message) -> bool:
        return message.photo is not None

COMMAND = CommandFilter()
TEXT = TextFilter()
PHOTO = PhotoFilter()

class filters:
    BaseFilter = BaseFilter
    AndFilter = AndFilter
    OrFilter = OrFilter
    NotFilter = NotFilter
    COMMAND = COMMAND
    TEXT = TEXT
    PHOTO = PHOTO