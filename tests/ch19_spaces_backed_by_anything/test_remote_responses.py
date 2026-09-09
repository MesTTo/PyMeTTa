"""Purpose: reject malformed remote replies before exposing engine answers.

Guarantees:
  - response fields have protocol types instead of Python truthiness
    [tested: test_remote_rejects_malformed_response_fields; commit=089bc6036ae5039bce3963d8b4e80ecaf04dfb49]
"""

import pytest

import metta._binding.json as _json
import metta.remote._client as _moved_metta_remote__client
import metta.remote._transport as _moved_metta_remote__transport
from metta import S, V
from metta._declare import declarations as _space_declarations
from metta._errors.errors import MettaError
from metta.remote import _network


@pytest.mark.parametrize(("operation", "answer"), [
    ("remove", {}),
    ("remove", {"removed": "false"}),
    ("add", {}),
    ("add", {"added": 1}),
    ("add_many", {"added": True}),
    ("match", {"atoms": {}}),
    ("atoms", {"atoms": ""}),
    ("ask", {"atoms": [["s", "a"]]}),
    ("ask", {"atoms": [["s", "a"]], "cursor": ""}),
    ("stop", {"stopped": 1}),
    ("health", {"ok": True, "atoms": 0, "bound": "false"}),
    ("health", {"ok": True, "atoms": 0, "capabilities": "match"}),
    ("health", {"ok": True, "atoms": False}),
])
def test_remote_rejects_malformed_response_fields(monkeypatch, operation, answer):
    """The HTTP boundary rejects each malformed success envelope."""
    def request(_endpoint, _method, path, **_options):
        body = answer if path == operation else {"ok": True, "atoms": 0, "protocol": 3}
        return _network.Response(200, "OK", _json.dumps(body), {})

    monkeypatch.setattr(_network.HTTPEndpoint, "request", request)
    transport = _moved_metta_remote__transport.connect("http://example.test")
    with pytest.raises(MettaError, match=r"response|outcome"):
        if operation == "health":
            transport.health()
        else:
            transport(operation, {"atoms": [], "batch": 1})


@pytest.mark.parametrize("operation", ["match", "atoms"])
def test_custom_transport_validates_the_whole_atom_list_before_yield(operation):
    """No prefix can be consumed as a result of a malformed reply."""
    space = _moved_metta_remote__client.RemoteSpace(lambda *_: {"atoms": [["s", "valid"], ["n", "invalid"]]})
    answers = space.match(V.x) if operation == "match" else space.atoms()
    with pytest.raises(MettaError, match="response"):
        next(answers)


def test_failed_stop_schema_keeps_the_cursor_retryable():
    """An invalid acknowledgement does not discard the only release token."""
    stops = []

    def transport(operation, payload):
        if operation == "ask":
            return {"atoms": [S.a.to_wire()], "cursor": "first"}
        stops.append(payload["cursor"])
        return {} if len(stops) == 1 else {"stopped": True}

    cursor = _moved_metta_remote__client.RemoteCursor(transport, "&self", V.x)
    try:
        with pytest.raises(MettaError, match="response"):
            cursor.close()
    finally:
        cursor.close()
    assert stops == ["first", "first"], "invalid stop acknowledgement must retain its token"


@pytest.mark.parametrize("http", [False, True])
def test_invalid_initial_reply_stops_its_cursor(monkeypatch, http):
    """Rejecting an acquired cursor's chunk still releases its valid token."""
    stops = []

    def transport(operation, payload):
        if operation == "stop":
            stops.append(payload["cursor"])
            return {"stopped": True}
        return {"atoms": [["n", "bad number"]], "cursor": "initial"}

    def request(_endpoint, _method, operation, **options):
        return _network.Response(
            200, "OK", _json.dumps(transport(operation, _json.loads(options["body"]))), {}
        )

    monkeypatch.setattr(_network.HTTPEndpoint, "request", request)
    boundary = _moved_metta_remote__transport.connect("http://example.test") if http else transport
    with pytest.raises(_moved_metta_remote__transport.ProtocolError, match="response"):
        _moved_metta_remote__client.RemoteCursor(boundary, "&self", V.x)
    assert stops == ["initial"], "initial response rejection must release its acquired token"


def test_invalid_initial_reply_keeps_the_token_when_cleanup_also_fails():
    """The reported response error retains enough data to retry failed cleanup."""
    def transport(operation, _payload):
        if operation == "stop":
            msg = "injected initial cleanup failure"
            raise OSError(msg)
        return {"atoms": [[]], "cursor": "initial"}

    with pytest.raises(ExceptionGroup) as failure:
        _moved_metta_remote__client.RemoteCursor(transport, "&self", V.x)
    response, cleanup = failure.value.exceptions
    assert isinstance(response, _moved_metta_remote__transport.ProtocolError)
    assert response.cursor == "initial"
    assert str(cleanup) == "injected initial cleanup failure"


@pytest.mark.parametrize("mode", ["keep", "empty"])
@pytest.mark.parametrize("malformed", [None, b'not JSON', b'{"atoms":{}}'])
def test_protocol_errors_cannot_become_engine_answers(metta, monkeypatch, mode, malformed):
    """Application error policies cannot turn a malformed transport into data."""
    def request(_endpoint, _method, _path, **_options):
        return _network.Response(200, "OK", malformed, {})

    monkeypatch.setattr(_network.HTTPEndpoint, "request", request)
    transport = _moved_metta_remote__transport.connect("http://example.test") if malformed is not None else (
        lambda *_: {"atoms": {}}
    )
    backing = _moved_metta_remote__client.RemoteSpace(transport)
    space = metta._open(f"&remote-schema-{mode}")
    _space_declarations._register_space(metta, backing, space.name)
    try:
        declaration = space.on_error("(edge $x)", mode)
        with pytest.raises(_moved_metta_remote__transport.ProtocolError, match=r"response|invalid JSON"):
            metta.run(f"!(match {space.name} (edge $x) $x)")
    finally:
        metta._at("&metta").remove(declaration)
        space.drop()
