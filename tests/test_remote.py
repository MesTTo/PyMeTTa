"""Purpose: verify the remote transport's boundary, authorization, and lifecycle.
Guarantees:
  - petta installs a NullHandler and reports transport lifecycle events only
    through configured logging [tested test_library_logging_is_opt_in,
    test_remote_transport_logs_operation_without_payload]
  - server startup and shutdown expose attached-engine lifecycle failures
    [tested test_remote_serve_reports_worker_startup_failure,
    test_remote_close_waits_for_worker_detach]
  - malformed HTTP request framing and JSON receive explicit client errors
    [tested test_remote_server_rejects_malformed_request_bodies]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import logging
import threading
from http.client import HTTPConnection, HTTPException

import pytest

import petta
import petta._network as network
from petta import S, remote
from petta.errors import PettaError


def test_library_logging_is_opt_in():
    assert any(
        isinstance(handler, logging.NullHandler)
        for handler in logging.getLogger("petta").handlers
    )


def test_remote_transport_logs_operation_without_payload(monkeypatch, caplog):
    transport = remote.connect("http://example.test/api")

    def request(*args, **kwargs):
        return 200, "OK", b'{"atoms": []}'

    monkeypatch.setattr(network.HTTPEndpoint, "request", request)
    sensitive_value = "payload-must-not-be-logged"
    with caplog.at_level(logging.DEBUG, logger="petta.remote"):
        assert transport("match", {"value": sensitive_value}) == {"atoms": []}

    text = caplog.text
    assert "sending remote engine operation match" in text
    assert "answered with HTTP 200" in text
    assert sensitive_value not in text


def test_bearer_token_uses_constant_time_comparison(monkeypatch):
    calls = []
    policies = []

    def compare(supplied, expected):
        calls.append((supplied, expected))
        return supplied == expected

    def authorize(request):
        policies.append(request)
        return True

    def asking(headers):
        return remote.Request("atoms", "&self", headers)

    monkeypatch.setattr(remote.hmac, "compare_digest", compare)

    matching = {"authorization": "Bearer secret"}
    assert remote._is_authorized(asking(matching), "secret", authorize)
    assert not remote._is_authorized(
        asking({"authorization": "Bearer wrong"}), "secret", authorize
    )
    assert not remote._is_authorized(asking({}), "secret", authorize)

    assert calls == [
        ("Bearer secret", "Bearer secret"),
        ("Bearer wrong", "Bearer secret"),
        ("", "Bearer secret"),
    ]
    # The policy hook runs only behind a good credential, and it is told
    # what is being asked for, not only who is asking.
    assert policies == [remote.Request("atoms", "&self", matching)]


@pytest.mark.parametrize(
    ("url", "scheme"),
    [
        ("file:///etc/passwd", "file"),
        ("ftp://example.test/data", "ftp"),
        ("data:text/plain,secret", "data"),
        ("example.test/api", "<missing>"),
    ],
)
def test_remote_connect_refuses_non_http_urls(url, scheme):
    with pytest.raises(PettaError, match=scheme):
        remote.connect(url)


@pytest.mark.parametrize(
    "headers",
    [None, {"Authorization": "Basic c2VjcmV0"}],
)
def test_remote_connect_refuses_credentials_over_http(headers):
    options = {"token": "secret"} if headers is None else {"headers": headers}
    with pytest.raises(PettaError, match="credentials require an https URL"):
        remote.connect("http://example.test", **options)


def test_remote_connect_accepts_http_and_https_urls():
    assert callable(remote.connect("http://example.test/api/"))
    assert callable(remote.connect("https://example.test/api/", token="secret"))


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), "invalid"])
def test_network_clients_refuse_invalid_timeouts(timeout):
    with pytest.raises(ValueError, match="timeout"):
        remote.connect("http://example.test", timeout=timeout)


@pytest.mark.parametrize(
    ("url", "message"),
    [
        ("http:///api", "no host"),
        ("https://example.test:invalid", "invalid"),
        ("https://example.test/api?token=value", "query or fragment"),
        ("https://example.test/api#section", "query or fragment"),
    ],
)
def test_remote_connect_refuses_malformed_base_urls(url, message):
    with pytest.raises(PettaError, match=message):
        remote.connect(url)


def test_remote_connect_refuses_embedded_credentials_without_echoing_them():
    with pytest.raises(PettaError, match="embedded credentials") as failure:
        remote.connect("https://operator:top-secret@example.test")
    assert "top-secret" not in str(failure.value)


def test_remote_serve_reports_worker_startup_failure(metta, monkeypatch):
    def fail_attach():
        raise RuntimeError("injected remote attach failure")

    monkeypatch.setattr(petta.janus, "attach_engine", fail_attach)

    with pytest.raises(PettaError, match="injected remote attach failure"):
        remote.serve(metta)


def test_remote_close_waits_for_worker_detach(metta, monkeypatch):
    original = petta.janus.detach_engine
    detach_started = threading.Event()
    release_detach = threading.Event()
    detached = threading.Event()

    def delayed_detach():
        detach_started.set()
        release_detach.wait(2.0)
        original()
        detached.set()

    monkeypatch.setattr(petta.janus, "detach_engine", delayed_detach)
    server = remote.serve(metta)
    failures = []

    def close():
        try:
            server.close(timeout=2.0)
        except BaseException as exc:
            failures.append(exc)

    closer = threading.Thread(target=close)
    closer.start()
    try:
        assert detach_started.wait(2.0)
        assert closer.is_alive()
    finally:
        release_detach.set()
        closer.join(2.0)

    assert not failures
    assert detached.is_set()
    assert not closer.is_alive()
    assert not server._worker.thread.is_alive()
    server.close()


@pytest.mark.parametrize(
    ("headers", "body", "status", "detail"),
    [
        ({}, b"", 411, "content-length is required"),
        ({"Content-Length": "nope"}, b"", 400, "decimal digits"),
        ({"Content-Length": "-1"}, b"", 400, "decimal digits"),
        (
            {"Content-Length": str(remote._MAX_REQUEST_BYTES + 1)},
            b"",
            413,
            "exceeds",
        ),
        ({"Content-Length": "1"}, b"[", 400, "not valid JSON"),
        ({"Content-Length": "2"}, b"[]", 400, "JSON object"),
        (
            {"Transfer-Encoding": "chunked", "Content-Length": "2"},
            b"{}",
            400,
            "transfer-encoding",
        ),
    ],
)
def test_remote_server_rejects_malformed_request_bodies(
    metta,
    headers,
    body,
    status,
    detail,
):
    server = remote.serve(metta)
    connection = HTTPConnection(server.host, server.port, timeout=2.0)
    try:
        connection.putrequest("POST", "/atoms")
        for name, value in headers.items():
            connection.putheader(name, value)
        connection.endheaders(body)
        response = connection.getresponse()
        assert response.status == status
        assert detail.encode() in response.read()
    finally:
        connection.close()
        server.close()


def test_authorize_can_serve_a_space_read_only(metta):
    # The hook saw the headers alone, so it could not tell a read from a
    # write and read-only was inexpressible.
    served = metta.fresh_space()
    served.add(S.stock(S.apple))
    name = served.space_name
    seen = []

    def read_only(request):
        seen.append((request.operation, request.space))
        return request.operation in ("atoms", "match")

    server = remote.serve(metta, spaces=[name], authorize=read_only)
    try:
        transport = remote.connect(server.url)
        space = remote.RemoteSpace(transport, name)
        assert list(space.atoms()) == [S.stock(S.apple)]
        with pytest.raises(PettaError, match="not authorized"):
            space.add(S.stock(S.pear))
        assert list(space.atoms()) == [S.stock(S.apple)]
    finally:
        server.close()
        served.drop()

    assert seen == [("atoms", name), ("add", name), ("atoms", name)]


@pytest.mark.parametrize(
    ("read_fails", "oversized"),
    [(False, False), (True, False), (False, True)],
)
def test_http_endpoint_closes_transport_resources(monkeypatch, read_fails, oversized):
    class Response:
        status = 200
        reason = "OK"
        closed = False

        def __init__(self):
            self._body = b"12345" if oversized else b"{}"
            self._offset = 0

        def getheader(self, _name):
            return None

        def read(self, amount):
            if read_fails:
                raise OSError("injected read failure")
            chunk = self._body[self._offset : self._offset + amount]
            self._offset += len(chunk)
            return chunk

        def close(self):
            self.closed = True

    class Connection:
        closed = False

        def __init__(self):
            self.response = Response()

        def request(self, method, target, *, body, headers):
            assert (method, target, body, headers) == (
                "GET",
                "/api/probe",
                None,
                {},
            )

        def getresponse(self):
            return self.response

        def close(self):
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(network, "HTTPConnection", lambda *args, **kwargs: connection)
    if oversized:
        monkeypatch.setattr(network, "MAX_HTTP_RESPONSE_BYTES", 4)
    endpoint = network.HTTPEndpoint(
        "http://example.test/api",
        subject="test",
        error_type=PettaError,
    )

    if read_fails:
        with pytest.raises(OSError, match="injected read failure"):
            endpoint.request("GET", "/probe", timeout=1.0)
    elif oversized:
        with pytest.raises(HTTPException, match="response body exceeds"):
            endpoint.request("GET", "/probe", timeout=1.0)
    else:
        assert endpoint.request("GET", "/probe", timeout=1.0) == (
            200,
            "OK",
            b"{}",
        )

    assert connection.response.closed
    assert connection.closed
