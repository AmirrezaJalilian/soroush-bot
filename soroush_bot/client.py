import json
from typing import Any, Dict, List, Optional, Union, BinaryIO, Tuple
from urllib.parse import urlencode
import aiohttp
from .types import User, Message, Update, InlineKeyboardMarkup, ReplyKeyboardMarkup
from dataclasses import asdict, is_dataclass

class SoroushPlusAPIError(Exception):
    def __init__(self, description: str, error_code: int = None, parameters: dict = None):
        self.description = description
        self.error_code = error_code
        self.parameters = parameters
        super().__init__(description)

def _serialize_reply_markup(reply_markup: Any) -> Any:
    if reply_markup is None:
        return None
    if isinstance(reply_markup, (dict, str)):
        return reply_markup
    if isinstance(reply_markup, (InlineKeyboardMarkup, ReplyKeyboardMarkup)):
        return reply_markup.to_dict()
    if is_dataclass(reply_markup):
        return asdict(reply_markup)
    return reply_markup

class SoroushClient:
    BASE_URL = "https://api.splus.ir/bot"

    def __init__(self, token: str, session: Optional[aiohttp.ClientSession] = None):
        self.token = token
        self._session = session
        self._owns_session = session is None

    async def __aenter__(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._owns_session and self._session:
            await self._session.close()

    @property
    def session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._owns_session = True
        return self._session

    async def _request(
        self,
        method_name: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Tuple[str, BinaryIO, str]]] = None,
        http_method: str = "POST",
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{self.token}/{method_name}"
        if params and http_method.upper() == "GET":
            url += "?" + urlencode(params)
        kwargs: Dict[str, Any] = {}
        if http_method.upper() == "POST":
            if files:
                form_data = aiohttp.FormData()
                if data:
                    for key, value in data.items():
                        form_data.add_field(key, str(value))
                for field_name, (filename, file_obj, content_type) in files.items():
                    form_data.add_field(field_name, file_obj, filename=filename, content_type=content_type)
                kwargs["data"] = form_data
            elif data:
                kwargs["json"] = data
            else:
                kwargs["data"] = data
        async with self.session.request(http_method.upper(), url, **kwargs) as response:
            result = await response.json()
        if not result.get("ok", False):
            raise SoroushPlusAPIError(
                description=result.get("description", "Unknown error"),
                error_code=result.get("error_code"),
                parameters=result.get("parameters"),
            )
        return result

    # Core
    async def get_me(self) -> User:
        response = await self._request("getMe", http_method="GET")
        return User.from_dict(response.get('result', {}))

    async def log_out(self) -> bool:
        result = await self._request("logOut", http_method="POST")
        return result.get("result", False)

    async def close(self) -> bool:
        result = await self._request("close", http_method="POST")
        if self._owns_session and self._session:
            await self._session.close()
        return result.get("result", False)

    # Updates
    async def get_updates(
        self,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        timeout: Optional[int] = None,
        allowed_updates: Optional[List[str]] = None,
    ) -> List[Update]:
        params = {k: v for k, v in locals().items() if k != "self" and v is not None}
        result = await self._request("getUpdates", params=params, http_method="GET")
        updates_data = result.get("result", [])
        return [Update.from_dict(item) for item in updates_data if isinstance(item, dict)]

    async def set_webhook(
        self,
        url: str,
        certificate: Optional[BinaryIO] = None,
        ip_address: Optional[str] = None,
        max_connections: Optional[int] = None,
        allowed_updates: Optional[List[str]] = None,
        drop_pending_updates: Optional[bool] = None,
    ) -> bool:
        data = {"url": url}
        if ip_address:
            data["ip_address"] = ip_address
        if max_connections:
            data["max_connections"] = max_connections
        if allowed_updates:
            data["allowed_updates"] = json.dumps(allowed_updates)
        if drop_pending_updates is not None:
            data["drop_pending_updates"] = drop_pending_updates
        files = None
        if certificate:
            files = {"certificate": ("cert.pem", certificate, "application/x-pem-file")}
        result = await self._request("setWebhook", data=data, files=files, http_method="POST")
        return result.get("result", False)

    async def delete_webhook(self, drop_pending_updates: Optional[bool] = None) -> bool:
        data = {}
        if drop_pending_updates is not None:
            data["drop_pending_updates"] = drop_pending_updates
        result = await self._request("deleteWebhook", data=data, http_method="POST")
        return result.get("result", False)

    async def get_webhook_info(self) -> Dict[str, Any]:
        result = await self._request("getWebhookInfo", http_method="GET")
        return result.get("result", {})

    # Send Message
    async def send_message(
        self,
        chat_id: Union[int, str],
        text: str,
        parse_mode: Optional[str] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        disable_web_page_preview: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        if entities:
            data["entities"] = json.dumps(entities)
        if disable_web_page_preview is not None:
            data["disable_web_page_preview"] = disable_web_page_preview
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendMessage", data=data, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_photo(
        self,
        chat_id: Union[int, str],
        photo: Union[str, BinaryIO],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = None
        if isinstance(photo, str):
            data["photo"] = photo
        else:
            files = {"photo": ("photo.jpg", photo, "image/jpeg")}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendPhoto", data=data, files=files, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_audio(
        self,
        chat_id: Union[int, str],
        audio: Union[str, BinaryIO],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        duration: Optional[int] = None,
        performer: Optional[str] = None,
        title: Optional[str] = None,
        thumb: Optional[BinaryIO] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = {}
        if isinstance(audio, str):
            data["audio"] = audio
        else:
            files["audio"] = ("audio.mp3", audio, "audio/mpeg")
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if duration is not None:
            data["duration"] = duration
        if performer:
            data["performer"] = performer
        if title:
            data["title"] = title
        if thumb:
            files["thumb"] = ("thumb.jpg", thumb, "image/jpeg")
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendAudio", data=data, files=files or None, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_document(
        self,
        chat_id: Union[int, str],
        document: Union[str, BinaryIO],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = None
        if isinstance(document, str):
            data["document"] = document
        else:
            files = {"document": ("document.pdf", document, "application/pdf")}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendDocument", data=data, files=files, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_video(
        self,
        chat_id: Union[int, str],
        video: Union[str, BinaryIO],
        duration: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        thumb: Optional[BinaryIO] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        supports_streaming: Optional[bool] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = {}
        if isinstance(video, str):
            data["video"] = video
        else:
            files["video"] = ("video.mp4", video, "video/mp4")
        if duration is not None:
            data["duration"] = duration
        if width is not None:
            data["width"] = width
        if height is not None:
            data["height"] = height
        if thumb:
            files["thumb"] = ("thumb.jpg", thumb, "image/jpeg")
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if supports_streaming is not None:
            data["supports_streaming"] = supports_streaming
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendVideo", data=data, files=files or None, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_animation(
        self,
        chat_id: Union[int, str],
        animation: Union[str, BinaryIO],
        duration: Optional[int] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        thumb: Optional[BinaryIO] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = {}
        if isinstance(animation, str):
            data["animation"] = animation
        else:
            files["animation"] = ("animation.gif", animation, "image/gif")
        if duration is not None:
            data["duration"] = duration
        if width is not None:
            data["width"] = width
        if height is not None:
            data["height"] = height
        if thumb:
            files["thumb"] = ("thumb.jpg", thumb, "image/jpeg")
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendAnimation", data=data, files=files or None, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_voice(
        self,
        chat_id: Union[int, str],
        voice: Union[str, BinaryIO],
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        duration: Optional[int] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = None
        if isinstance(voice, str):
            data["voice"] = voice
        else:
            files = {"voice": ("voice.ogg", voice, "audio/ogg")}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if duration is not None:
            data["duration"] = duration
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendVoice", data=data, files=files, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_video_note(
        self,
        chat_id: Union[int, str],
        video_note: Union[str, BinaryIO],
        duration: Optional[int] = None,
        length: Optional[int] = None,
        thumb: Optional[BinaryIO] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = {}
        if isinstance(video_note, str):
            data["video_note"] = video_note
        else:
            files["video_note"] = ("video_note.mp4", video_note, "video/mp4")
        if duration is not None:
            data["duration"] = duration
        if length is not None:
            data["length"] = length
        if thumb:
            files["thumb"] = ("thumb.jpg", thumb, "image/jpeg")
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendVideoNote", data=data, files=files or None, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_media_group(
        self,
        chat_id: Union[int, str],
        media: List[Dict[str, Any]],
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
    ) -> List[Message]:
        data = {"chat_id": chat_id, "media": json.dumps(media)}
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        result = await self._request("sendMediaGroup", data=data, http_method="POST")
        messages = result.get("result", [])
        return [Message.from_dict(msg) for msg in messages if isinstance(msg, dict)]

    async def send_location(
        self,
        chat_id: Union[int, str],
        latitude: float,
        longitude: float,
        horizontal_accuracy: Optional[float] = None,
        live_period: Optional[int] = None,
        heading: Optional[int] = None,
        proximity_alert_radius: Optional[int] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id, "latitude": latitude, "longitude": longitude}
        if horizontal_accuracy is not None:
            data["horizontal_accuracy"] = horizontal_accuracy
        if live_period is not None:
            data["live_period"] = live_period
        if heading is not None:
            data["heading"] = heading
        if proximity_alert_radius is not None:
            data["proximity_alert_radius"] = proximity_alert_radius
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendLocation", data=data, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_contact(
        self,
        chat_id: Union[int, str],
        phone_number: str,
        first_name: str,
        last_name: Optional[str] = None,
        vcard: Optional[str] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id, "phone_number": phone_number, "first_name": first_name}
        if last_name:
            data["last_name"] = last_name
        if vcard:
            data["vcard"] = vcard
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendContact", data=data, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_dice(
        self,
        chat_id: Union[int, str],
        emoji: Optional[str] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        if emoji:
            data["emoji"] = emoji
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendDice", data=data, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def send_chat_action(self, chat_id: Union[int, str], action: str) -> bool:
        data = {"chat_id": chat_id, "action": action}
        result = await self._request("sendChatAction", data=data, http_method="POST")
        return result.get("result", False)

    # Forward & Copy
    async def forward_message(
        self,
        chat_id: Union[int, str],
        from_chat_id: Union[int, str],
        message_id: int,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
    ) -> Message:
        data = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        result = await self._request("forwardMessage", data=data, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def copy_message(
        self,
        chat_id: Union[int, str],
        from_chat_id: Union[int, str],
        message_id: int,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Dict[str, Any]:
        data = {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id}
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("copyMessage", data=data, http_method="POST")
        return result.get("result", {})

    # Stickers
    async def send_sticker(
        self,
        chat_id: Union[int, str],
        sticker: Union[str, BinaryIO],
        disable_notification: Optional[bool] = None,
        protect_content: Optional[bool] = None,
        reply_to_message_id: Optional[int] = None,
        allow_sending_without_reply: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> Message:
        data = {"chat_id": chat_id}
        files = None
        if isinstance(sticker, str):
            data["sticker"] = sticker
        else:
            files = {"sticker": ("sticker.webp", sticker, "image/webp")}
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        if protect_content is not None:
            data["protect_content"] = protect_content
        if reply_to_message_id is not None:
            data["reply_to_message_id"] = reply_to_message_id
        if allow_sending_without_reply is not None:
            data["allow_sending_without_reply"] = allow_sending_without_reply
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("sendSticker", data=data, files=files, http_method="POST")
        return Message.from_dict(result.get("result", {}))

    async def get_sticker_set(self, name: str) -> Dict[str, Any]:
        result = await self._request("getStickerSet", data={"name": name}, http_method="POST")
        return result.get("result", {})

    # Callback
    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: Optional[bool] = None,
        url: Optional[str] = None,
        cache_time: Optional[int] = None,
    ) -> bool:
        data = {"callback_query_id": callback_query_id}
        if text:
            data["text"] = text
        if show_alert is not None:
            data["show_alert"] = show_alert
        if url:
            data["url"] = url
        if cache_time is not None:
            data["cache_time"] = cache_time
        result = await self._request("answerCallbackQuery", data=data, http_method="POST")
        return result.get("result", False)

    # Edit
    async def edit_message_text(
        self,
        text: str,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        parse_mode: Optional[str] = None,
        entities: Optional[List[Dict[str, Any]]] = None,
        disable_web_page_preview: Optional[bool] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> bool:
        data = {"text": text}
        if chat_id is not None:
            data["chat_id"] = chat_id
        if message_id is not None:
            data["message_id"] = message_id
        if inline_message_id is not None:
            data["inline_message_id"] = inline_message_id
        if parse_mode:
            data["parse_mode"] = parse_mode
        if entities:
            data["entities"] = json.dumps(entities)
        if disable_web_page_preview is not None:
            data["disable_web_page_preview"] = disable_web_page_preview
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("editMessageText", data=data, http_method="POST")
        return result.get("result", True)

    async def edit_message_caption(
        self,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        caption: Optional[str] = None,
        parse_mode: Optional[str] = None,
        caption_entities: Optional[List[Dict[str, Any]]] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> bool:
        data = {}
        if chat_id is not None:
            data["chat_id"] = chat_id
        if message_id is not None:
            data["message_id"] = message_id
        if inline_message_id is not None:
            data["inline_message_id"] = inline_message_id
        if caption:
            data["caption"] = caption
        if parse_mode:
            data["parse_mode"] = parse_mode
        if caption_entities:
            data["caption_entities"] = json.dumps(caption_entities)
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("editMessageCaption", data=data, http_method="POST")
        return result.get("result", True)

    async def edit_message_media(
        self,
        media: Dict[str, Any],
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> bool:
        data = {"media": json.dumps(media)}
        if chat_id is not None:
            data["chat_id"] = chat_id
        if message_id is not None:
            data["message_id"] = message_id
        if inline_message_id is not None:
            data["inline_message_id"] = inline_message_id
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("editMessageMedia", data=data, http_method="POST")
        return result.get("result", True)

    async def edit_message_reply_markup(
        self,
        chat_id: Optional[Union[int, str]] = None,
        message_id: Optional[int] = None,
        inline_message_id: Optional[str] = None,
        reply_markup: Optional[Union[Dict[str, Any], str, Any]] = None,
    ) -> bool:
        data = {}
        if chat_id is not None:
            data["chat_id"] = chat_id
        if message_id is not None:
            data["message_id"] = message_id
        if inline_message_id is not None:
            data["inline_message_id"] = inline_message_id
        if reply_markup:
            serialized = _serialize_reply_markup(reply_markup)
            data["reply_markup"] = json.dumps(serialized) if not isinstance(serialized, str) else serialized
        result = await self._request("editMessageReplyMarkup", data=data, http_method="POST")
        return result.get("result", True)

    # Delete
    async def delete_message(self, chat_id: Union[int, str], message_id: int) -> bool:
        data = {"chat_id": chat_id, "message_id": message_id}
        result = await self._request("deleteMessage", data=data, http_method="POST")
        return result.get("result", False)

    # File
    async def get_file(self, file_id: str) -> Dict[str, Any]:
        result = await self._request("getFile", data={"file_id": file_id}, http_method="POST")
        return result.get("result", {})

    async def download_file(self, file_path: str, destination: str) -> None:
        url = f"https://api.splus.ir/file/bot/{file_path}"
        async with self.session.get(url) as response:
            with open(destination, "wb") as f:
                f.write(await response.read())

    # Commands
    async def set_my_commands(
        self,
        commands: List[Dict[str, str]],
        scope: Optional[Dict[str, Any]] = None,
        language_code: Optional[str] = None,
    ) -> bool:
        data = {"commands": json.dumps(commands)}
        if scope:
            data["scope"] = json.dumps(scope)
        if language_code:
            data["language_code"] = language_code
        result = await self._request("setMyCommands", data=data, http_method="POST")
        return result.get("result", False)

    async def delete_my_commands(
        self,
        scope: Optional[Dict[str, Any]] = None,
        language_code: Optional[str] = None,
    ) -> bool:
        data = {}
        if scope:
            data["scope"] = json.dumps(scope)
        if language_code:
            data["language_code"] = language_code
        result = await self._request("deleteMyCommands", data=data, http_method="POST")
        return result.get("result", False)

    async def get_my_commands(
        self,
        scope: Optional[Dict[str, Any]] = None,
        language_code: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        data = {}
        if scope:
            data["scope"] = json.dumps(scope)
        if language_code:
            data["language_code"] = language_code
        result = await self._request("getMyCommands", data=data, http_method="POST")
        return result.get("result", [])

    # Chat & User
    async def get_user_profile_photos(
        self,
        user_id: int,
        offset: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        data = {"user_id": user_id}
        if offset is not None:
            data["offset"] = offset
        if limit is not None:
            data["limit"] = limit
        result = await self._request("getUserProfilePhotos", data=data, http_method="POST")
        return result.get("result", {})

    async def pin_chat_message(
        self,
        chat_id: Union[int, str],
        message_id: int,
        disable_notification: Optional[bool] = None,
    ) -> bool:
        data = {"chat_id": chat_id, "message_id": message_id}
        if disable_notification is not None:
            data["disable_notification"] = disable_notification
        result = await self._request("pinChatMessage", data=data, http_method="POST")
        return result.get("result", False)

    async def unpin_chat_message(
        self,
        chat_id: Union[int, str],
        message_id: Optional[int] = None,
    ) -> bool:
        data = {"chat_id": chat_id}
        if message_id is not None:
            data["message_id"] = message_id
        result = await self._request("unpinChatMessage", data=data, http_method="POST")
        return result.get("result", False)

    async def get_chat(self, chat_id: Union[int, str]) -> Dict[str, Any]:
        result = await self._request("getChat", data={"chat_id": chat_id}, http_method="POST")
        return result.get("result", {})