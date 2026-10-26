"""Exceptions raised by chatbot_client.

Every error this library raises on purpose derives from :class:`ChatbotError`, so an
application can catch one type at its integration boundary. Invalid arguments
(an empty bot id, chat id or message) raise ``ValueError`` before any request is sent.

    ChatbotError
    ├── ChatbotConnectionError      no complete response received
    │   └── ChatbotTimeoutError
    ├── ChatbotAPIError             non-2xx response
    │   ├── BadRequestError         400
    │   ├── AuthenticationError     401
    │   ├── PermissionDeniedError   403
    │   ├── NotFoundError           404
    │   ├── RateLimitError          429
    │   └── ServerError             5xx
    └── InvalidResponseError        2xx response with an unexpected body
"""

from __future__ import annotations

import httpx

_MAX_BODY_IN_MESSAGE = 300


class ChatbotError(Exception):
    """Base class for all errors raised by chatbot_client."""


class ChatbotConnectionError(ChatbotError):
    """No complete response was received: DNS failure, refused or dropped connection."""


class ChatbotTimeoutError(ChatbotConnectionError):
    """The server did not respond within the configured timeout."""


class ChatbotAPIError(ChatbotError):
    """The server returned a non-success HTTP status. ``body`` is the raw response text."""

    def __init__(self, message: str, *, status_code: int, body: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class BadRequestError(ChatbotAPIError):
    """400: the request was invalid or rejected by the server."""


class AuthenticationError(ChatbotAPIError):
    """401: credentials are missing or invalid."""


class PermissionDeniedError(ChatbotAPIError):
    """403: the caller may not use this bot or chat."""


class NotFoundError(ChatbotAPIError):
    """404: the bot or chat does not exist."""


class RateLimitError(ChatbotAPIError):
    """429: too many requests, still refused after retrying."""


class ServerError(ChatbotAPIError):
    """5xx: the server failed to handle the request."""


class InvalidResponseError(ChatbotError):
    """The server returned a success status, but the body does not match the specification."""

    def __init__(self, message: str, *, status_code: int, body: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


_ERRORS_BY_STATUS: dict[int, type[ChatbotAPIError]] = {
    400: BadRequestError,
    401: AuthenticationError,
    403: PermissionDeniedError,
    404: NotFoundError,
    429: RateLimitError,
}


def api_error_from_response(response: httpx.Response) -> ChatbotAPIError:
    """The matching :class:`ChatbotAPIError` subclass for a non-success response."""
    status = response.status_code
    error_class = _ERRORS_BY_STATUS.get(status, ServerError if status >= 500 else ChatbotAPIError)
    message = f"{_describe(response.request)} failed with HTTP {status}"
    body = response.text.strip()
    if body:
        message = f"{message}: {_truncate(body)}"
    return error_class(message, status_code=status, body=response.text)


def invalid_response(response: httpx.Response, problem: str) -> InvalidResponseError:
    """An :class:`InvalidResponseError` for a success response whose body has ``problem``."""
    return InvalidResponseError(
        f"{_describe(response.request)} returned HTTP {response.status_code}, "
        f"but the response body {problem}: {_truncate(response.text)!r}",
        status_code=response.status_code,
        body=response.text,
    )


def error_from_httpx(exc: httpx.RequestError) -> ChatbotConnectionError:
    """Translate an httpx request failure into a chatbot_client exception."""
    where = _describe(exc.request)
    if isinstance(exc, httpx.TimeoutException):
        return ChatbotTimeoutError(f"{where} timed out ({type(exc).__name__})")
    return ChatbotConnectionError(f"{where} failed: {exc}")


def _describe(request: httpx.Request) -> str:
    return f"{request.method} {request.url.path}"


def _truncate(text: str) -> str:
    return text if len(text) <= _MAX_BODY_IN_MESSAGE else f"{text[:_MAX_BODY_IN_MESSAGE]}..."

