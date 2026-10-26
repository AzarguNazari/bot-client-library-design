from __future__ import annotations

from collections.abc import Callable, Generator

import httpx


class BearerTokenAuth(httpx.Auth):
    def __init__(self, token: str | Callable[[], str]) -> None:
        if isinstance(token, str) and not token.strip():
            raise ValueError("token must not be empty")
        self._token = token

    def auth_flow(self, request: httpx.Request) -> Generator[httpx.Request, httpx.Response, None]:
        token = self._token() if callable(self._token) else self._token
        request.headers["Authorization"] = f"Bearer {token}"
        yield request

    def __repr__(self) -> str:
        return "BearerTokenAuth(token=***)"
