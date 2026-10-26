"""Configuration for :class:`chatbot_client.ChatbotClient`."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

import httpx

from .auth import BearerTokenAuth


@dataclass(frozen=True)
class ChatbotConfig:
    """Connection settings for :class:`chatbot_client.ChatbotClient`.

    Attributes:
        base_url: Root URL of the API, e.g. ``https://chatbot-dev.example.com``.
            A path prefix is allowed when the API sits behind a gateway.
        auth: Any ``httpx.Auth``, e.g. :class:`chatbot_client.BearerTokenAuth`. ``None`` sends no credentials.
        timeout: Seconds to wait for a response. Completions wait for a language model,
            so the default is generous.
        connect_timeout: Seconds to wait while opening a connection.
        max_retries: Retries for requests the server cannot have processed; see the README.
        backoff_factor: Base delay in seconds for exponential backoff between retries.
        headers: Extra headers sent with every request, e.g. a correlation id.
    """

    base_url: str
    auth: httpx.Auth | None = None
    timeout: float = 60.0
    connect_timeout: float = 10.0
    max_retries: int = 2
    backoff_factor: float = 0.5
    headers: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        url = httpx.URL(self.base_url)
        if url.scheme not in ("http", "https") or not url.host:
            raise ValueError(f"base_url must be an absolute http(s) URL, got {self.base_url!r}")
        if self.timeout <= 0 or self.connect_timeout <= 0:
            raise ValueError("timeout and connect_timeout must be > 0")
        if self.max_retries < 0 or self.backoff_factor < 0:
            raise ValueError("max_retries and backoff_factor must be >= 0")

    @classmethod
    def from_env(cls) -> ChatbotConfig:
        """Read ``CHATBOT_BASE_URL`` (required) and ``CHATBOT_API_TOKEN`` (optional, sent as a bearer token)."""
        base_url = os.environ.get("CHATBOT_BASE_URL")
        if not base_url:
            raise ValueError("CHATBOT_BASE_URL is not set")
        token = os.environ.get("CHATBOT_API_TOKEN")
        return cls(base_url=base_url, auth=BearerTokenAuth(token) if token else None)
