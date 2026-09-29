from __future__ import annotations

from typing import Any

import httpx

from .errors import error_for_status


def compact(**kwargs: Any) -> dict[str, Any]:
    """Drop None values.

    The server uses `#[serde(deny_unknown_fields)]`, so sending a key
    with a null value causes a 400. Only set fields should reach the wire.
    """
    return {k: v for k, v in kwargs.items() if v is not None}


class HTTPCore:
    def __init__(
        self,
        base_url: str,
        client_token: str,
        *,
        client_header_key: str = "x-ppdrive-client",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {client_header_key: client_token}
        self._client = httpx.Client(
            base_url=self.base_url,
            headers=self._headers,
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "HTTPCore":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def handle(self, response: httpx.Response) -> Any:
        if response.is_success:
            if not response.content:
                return None
            return response.json()

        try:
            payload = response.json()
            message = payload.get("error", response.text)
        except Exception:
            message = response.text

        raise error_for_status(response.status_code, message)

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        return self.handle(self._client.request(method, url, **kwargs))

    def raw(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        response = self._client.request(method, url, **kwargs)
        if response.is_error:
            self.handle(response)
        return response
