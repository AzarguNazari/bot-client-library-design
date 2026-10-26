"""Client for the AiChatBot API."""

from __future__ import annotations

import logging
import math
import random
import time
from types import TracebackType
from typing import Any

import httpx

from . import _protocol
from ._version import __version__
from .config import ChatbotConfig
from .errors import api_error_from_response, error_from_httpx

logger = logging.getLogger("chatbot_client")

# Both endpoints are POSTs that store the message, so only failures where the server
# cannot have processed the request are retried. A read timeout is not one of them.
_NOT_SENT_ERRORS = (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout)
_REFUSED_STATUSES = frozenset({429, 503})
_MAX_RETRY_DELAY = 10.0


class ChatbotClient:
    def __init__(self, config: ChatbotConfig, *, transport: httpx.BaseTransport | None = None) -> None:
        self._config = config
        self._http = httpx.Client(
            base_url=config.base_url,
            auth=config.auth,
            headers={"Accept": "application/json", "User-Agent": f"chatbot-client/{__version__}", **config.headers},
            timeout=httpx.Timeout(config.timeout, connect=config.connect_timeout),
            transport=transport,
        )

    def create_chat(self, bot_id: str) -> ChatSession:
        _require_text(bot_id, "bot_id")
        response = self._post(_protocol.CREATE_CHAT_PATH, _protocol.create_chat_body(bot_id))
        return ChatSession(self, _protocol.parse_chat_id(response))

    def resume_chat(self, chat_id: str) -> ChatSession:
        return ChatSession(self, _require_text(chat_id, "chat_id"))

    def send_message(self, chat_id: str, message: str) -> str:
        _require_text(chat_id, "chat_id")
        _require_text(message, "message")
        response = self._post(_protocol.completion_path(chat_id), _protocol.completion_body(message))
        return _protocol.parse_assistant_message(response)

    def close(self) -> None:
        """Close the connection pool."""
        self._http.close()

    def __enter__(self) -> ChatbotClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _post(self, path: str, body: dict[str, Any]) -> httpx.Response:
        attempt = 0
        while True:
            try:
                response = self._http.post(path, json=body)
            except httpx.RequestError as exc:
                if isinstance(exc, _NOT_SENT_ERRORS) and attempt < self._config.max_retries:
                    self._wait_before_retry(attempt, None, f"{type(exc).__name__} on POST {path}")
                    attempt += 1
                    continue
                raise error_from_httpx(exc) from exc

            if response.is_success:
                return response
            if response.status_code in _REFUSED_STATUSES and attempt < self._config.max_retries:
                retry_after = response.headers.get("Retry-After")
                self._wait_before_retry(attempt, retry_after, f"HTTP {response.status_code} on POST {path}")
                attempt += 1
                continue
            raise api_error_from_response(response)

    def _wait_before_retry(self, attempt: int, retry_after: str | None, reason: str) -> None:
        delay = _retry_delay(attempt, self._config.backoff_factor, retry_after)
        logger.warning("%s; retry %d of %d in %.1fs", reason, attempt + 1, self._config.max_retries, delay)
        time.sleep(delay)


class ChatSession:
    """One chat with a bot. The server keeps the history, so the session only holds the chat id."""

    def __init__(self, client: ChatbotClient, chat_id: str) -> None:
        self._client = client
        self.chat_id = chat_id

    def send(self, message: str) -> str:
        """Send a user message and return the assistant's reply."""
        return self._client.send_message(self.chat_id, message)

    def __repr__(self) -> str:
        return f"ChatSession(chat_id={self.chat_id!r})"


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _retry_delay(attempt: int, backoff_factor: float, retry_after: str | None) -> float:
    try:
        delay = float(retry_after or "")
    except ValueError:
        delay = math.nan
    if math.isnan(delay):  # header absent, an HTTP date (not parsed), or garbage
        delay = random.uniform(0, backoff_factor * 2**attempt)
    return min(max(delay, 0.0), _MAX_RETRY_DELAY)
