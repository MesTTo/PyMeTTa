"""Purpose: validate endpoints and issue bounded HTTP client requests.
Guarantees:
  - validated_http_base accepts only absolute HTTP and HTTPS URLs with a host
    [tested test_remote_connect_refuses_non_http_urls,
    test_das_refuses_non_http_urls]
  - client timeouts are finite and positive and response bodies stop at a
    fixed byte limit [tested test_network_clients_refuse_invalid_timeouts,
    test_http_endpoint_closes_transport_resources]
  - HTTPEndpoint.request closes its response and connection on success and
    failure [tested test_http_endpoint_closes_transport_resources]
Owns:
  - HTTPEndpoint.request owns each response and connection until the request
    returns or raises [tested test_http_endpoint_closes_transport_resources]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import math
from collections.abc import Mapping
from http.client import HTTPConnection, HTTPException, HTTPResponse, HTTPSConnection
from typing import Any
from urllib.parse import SplitResult, urlsplit

MAX_HTTP_RESPONSE_BYTES = 16 * 1024 * 1024


def validated_timeout(timeout: Any, *, subject: str) -> float:
    """Return a finite positive timeout or reject the caller's value."""
    try:
        value = float(timeout)
    except (TypeError, ValueError) as exc:
        msg = f"{subject} must be a number, got {timeout!r}"
        raise ValueError(msg) from exc
    if not math.isfinite(value) or value <= 0:
        msg = f"{subject} must be finite and positive, got {timeout!r}"
        raise ValueError(msg)
    return value


def _bounded_response_body(response: HTTPResponse) -> bytes:
    declared = response.getheader("Content-Length")
    if declared is not None:
        if not declared.isascii() or not declared.isdigit():
            msg = f"response content-length is invalid: {declared!r}"
            raise HTTPException(msg)
        if int(declared) > MAX_HTTP_RESPONSE_BYTES:
            msg = f"response body exceeds the {MAX_HTTP_RESPONSE_BYTES}-byte limit"
            raise HTTPException(
                msg
            )
    chunks: list[bytes] = []
    remaining = MAX_HTTP_RESPONSE_BYTES + 1
    while remaining:
        chunk = response.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    raw = b"".join(chunks)
    if len(raw) > MAX_HTTP_RESPONSE_BYTES:
        msg = f"response body exceeds the {MAX_HTTP_RESPONSE_BYTES}-byte limit"
        raise HTTPException(
            msg
        )
    return raw


def _split_url(url: str, subject: str, error_type: type[Exception]) -> SplitResult:
    try:
        return urlsplit(url)
    except (TypeError, ValueError) as exc:
        msg = f"{subject} URL {url!r} is invalid: {exc}"
        raise error_type(msg) from exc


def _validate_credentials_and_port(
    parsed: SplitResult,
    url: str,
    subject: str,
    error_type: type[Exception],
) -> None:
    if parsed.username is not None or parsed.password is not None:
        msg = f"{subject} URL must not contain embedded credentials"
        raise error_type(msg)
    try:
        _ = parsed.port
    except ValueError as exc:
        msg = f"{subject} URL {url!r} is invalid: {exc}"
        raise error_type(msg) from exc


def _validate_host(
    parsed: SplitResult, url: str, subject: str, error_type: type[Exception]
) -> None:
    if parsed.hostname is None:
        msg = f"{subject} URL {url!r} has no host"
        raise error_type(msg)


def _validated_scheme(
    parsed: SplitResult, subject: str, error_type: type[Exception]
) -> str:
    scheme = parsed.scheme.lower()
    # policy-inventory-exempt: mechanism-internal; reason=http and https are the two transports implemented by HTTPEndpoint; evidence=bindings/python/petta/_network.py:_validated_scheme
    if scheme not in {"http", "https"}:
        shown = scheme or "<missing>"
        msg = f"{subject} URL scheme {shown!r} is not allowed; use http or https"
        raise error_type(
            msg
        )
    return scheme


def _validate_suffix(parsed: SplitResult, url: str, subject: str, error_type: type[Exception]) -> None:
    if parsed.query or parsed.fragment:
        msg = f"{subject} URL {url!r} must not contain a query or fragment"
        raise error_type(msg)


def validated_http_base(
    url: str,
    *,
    subject: str,
    error_type: type[Exception],
) -> tuple[str, str]:
    """Return a slash-trimmed base and scheme, or raise error_type."""
    parsed = _split_url(url, subject, error_type)
    _validate_credentials_and_port(parsed, url, subject, error_type)
    scheme = _validated_scheme(parsed, subject, error_type)
    _validate_host(parsed, url, subject, error_type)
    _validate_suffix(parsed, url, subject, error_type)
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
            msg = "validated HTTP URL lost its host"
            raise AssertionError(msg)
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
        timeout = validated_timeout(timeout, subject="HTTP request timeout")
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
            return response.status, response.reason, _bounded_response_body(response)
        finally:
            if response is not None:
                response.close()
            connection.close()
