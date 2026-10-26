from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

import httpx

from .errors import invalid_response

CREATE_CHAT_PATH = "/api/chats"


def completion_path(chat_id: str) -> str:
    return f"/api/chats/{quote(chat_id, safe='')}/completions"


def create_chat_body(bot_id: str) -> dict[str, Any]:
    return {"botId": bot_id}


def completion_body(message: str) -> dict[str, Any]:
    return {
        "userMessage": message,
        "ignoreChatHistory": False,
        "isAdminChat": False,
        "isTraceLogEnabled": False,
    }


def parse_chat_id(response: httpx.Response) -> str:
    value = _json_object(response).get("chatId")
    if not isinstance(value, str) or not value.strip():
        raise invalid_response(response, "has no 'chatId'")
    return value


def parse_assistant_message(response: httpx.Response) -> str:
    value = _json_object(response).get("assistantMessage")
    if not isinstance(value, str):
        raise invalid_response(response, "has no 'assistantMessage'")
    return value


def _json_object(response: httpx.Response) -> dict[str, Any]:
    try:
        data = json.loads(response.content)
    except ValueError as exc:
        raise invalid_response(response, "is not valid JSON") from exc
    if not isinstance(data, dict):
        raise invalid_response(response, "is not a JSON object")
    return data
