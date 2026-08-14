"""Purpose: validate endpoints and issue bounded HTTP client requests.
Guarantees:
  - validated_http_base accepts only absolute HTTP and HTTPS URLs with a host
    [tested test_remote_connect_refuses_non_http_urls,
    test_das_refuses_non_http_urls]
  - HTTPEndpoint.request closes its response and connection on success and
    failure [tested test_http_endpoint_closes_transport_resources]
Owns:
  - HTTPEndpoint.request owns each response and connection until the request
    returns or raises [tested test_http_endpoint_closes_transport_resources]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections.abc import Mapping
from http.client import HTTPConnection, HTTPSConnection
from typing import Any
from urllib.parse import urlsplit


def validated_http_base(
    url: str,
    *,
    subject: str,
    error_type: type[Exception],
) -> tuple[str, str]:
    """Return a slash-trimmed base and scheme, or raise error_type."""
    try:
        parsed = urlsplit(url)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
    except (TypeError, ValueError) as exc:
        raise error_type(f"{subject} URL {url!r} is invalid: {exc}") from exc
    if parsed.username is not None or parsed.password is not None:
        raise error_type(f"{subject} URL must not contain embedded credentials")
    try:
        _ = parsed.port
    except ValueError as exc:
        raise error_type(f"{subject} URL {url!r} is invalid: {exc}") from exc
    if scheme not in {"http", "https"}:
        shown = scheme or "<missing>"
        raise error_type(
            f"{subject} URL scheme {shown!r} is not allowed; use http or https"
        )
    if hostname is None:
        raise error_type(f"{subject} URL {url!r} has no host")
    if parsed.query or parsed.fragment:
        raise error_type(f"{subject} URL {url!r} must not contain a query or fragment")
    normalized = parsed._replace(scheme=scheme).geturl().rstrip("/")
    return normalized, scheme


class HTTPEndpoint:
    """A validated endpoint that creates and closes one connection per call."""

    __slots__ = ("_context", "_host", "_path", "_port", "scheme", "url")

    def __init__(
        self,
        url: str,
        *,
        subject: str,
        error_type: type[Exception],
        ssl_context: Any = None,
    ) -> None:
        self.url, self.scheme = validated_http_base(
            url, subject=subject, error_type=error_type
        )
        parsed = urlsplit(self.url)
        hostname = parsed.hostname
        if hostname is None:
            raise AssertionError("validated HTTP URL lost its host")
        self._host = hostname
        self._port = parsed.port
        self._path = parsed.path.rstrip("/")
        self._context = ssl_context

    def request(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: Mapping[str, str] | None = None,
        timeout: float,
    ) -> tuple[int, str, bytes]:
        """Return status, reason and body after closing transport resources."""
        connection: HTTPConnection
        if self.scheme == "https":
            connection = HTTPSConnection(
                self._host,
                self._port,
                timeout=timeout,
                context=self._context,
            )
        else:
            connection = HTTPConnection(self._host, self._port, timeout=timeout)
        target = f"{self._path}/{path.lstrip('/')}"
        response = None
        try:
            connection.request(method, target, body=body, headers=dict(headers or {}))
            response = connection.getresponse()
            return response.status, response.reason, response.read()
        finally:
            if response is not None:
                response.close()
            connection.close()
