"""Purpose: verify the remote transport's boundary, authorization, and lifecycle.
Guarantees:
  - petta installs a NullHandler and reports transport lifecycle events only
    through configured logging [tested test_library_logging_is_opt_in,
    test_remote_transport_logs_operation_without_payload]
  - server startup and shutdown expose attached-engine lifecycle failures
    [tested test_remote_serve_reports_worker_startup_failure,
    test_remote_close_waits_for_worker_detach]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import logging
import threading

import pytest

import petta
import petta._network as network
from petta import remote
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

    def authorize(headers):
        policies.append(headers)
        return True

    monkeypatch.setattr(remote.hmac, "compare_digest", compare)

    matching = {"authorization": "Bearer secret"}
    assert remote._is_authorized(matching, "secret", authorize)
    assert not remote._is_authorized(
        {"authorization": "Bearer wrong"}, "secret", authorize
    )
    assert not remote._is_authorized({}, "secret", authorize)

    assert calls == [
        ("Bearer secret", "Bearer secret"),
        ("Bearer wrong", "Bearer secret"),
        ("", "Bearer secret"),
    ]
    assert policies == [matching]


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


@pytest.mark.parametrize("read_fails", [False, True])
def test_http_endpoint_closes_transport_resources(monkeypatch, read_fails):
    class Response:
        status = 200
        reason = "OK"
        closed = False

        def read(self):
            if read_fails:
                raise OSError("injected read failure")
            return b"{}"

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
    endpoint = network.HTTPEndpoint(
        "http://example.test/api",
        subject="test",
        error_type=PettaError,
    )

    if read_fails:
        with pytest.raises(OSError, match="injected read failure"):
            endpoint.request("GET", "/probe", timeout=1.0)
    else:
        assert endpoint.request("GET", "/probe", timeout=1.0) == (
            200,
            "OK",
            b"{}",
        )

    assert connection.response.closed
    assert connection.closed
