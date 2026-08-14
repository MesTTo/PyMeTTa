"""Purpose: petta.das against a scripted command router. Request bodies
are pinned to the router's own validated parameter schema, event shapes
are copied from the C++ emitters (query_answers carries "answers",
completion carries "total_items", errors carry "message"), answers read
back as petta atoms, and a DASSpace registered on a real engine joins
DAS candidates with native facts through the engine's own unification.
A live-router test runs only when PETTA_DAS_URL answers ping.
Guarantees:
  - incomplete and aborted answer streams never return partial data [tested
    test_query_and_count_require_completed_terminal_event]
  - a terminal event closes its event iterator before query returns [tested
    test_completed_query_closes_its_event_stream]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import logging
import os

import pytest

from petta import EngineError, PettaError, S, V, expr
from petta.atoms import Gnd, parse
from petta.das import DAS, DASError, DASSpace, _render_tokens


class ScriptedDAS(DAS):
    """A DAS whose transport is a script: posts are recorded, events
    replay the shapes the router's own C++ emits."""

    def __init__(self, events):
        super().__init__("http://scripted:0")
        self.posted = []
        self._script = list(events)

    def _request(self, method, path, body=None):
        self.posted.append((method, path, body))
        if path == "/ping":
            return "PONG!"
        if path == "/command-router/executions":
            return {"execution_id": "exec-1"}
        return {}

    def _events(self, execution_id):
        yield from self._script


def _answer_item(binding_text, expression_text, importance=0.5):
    return {
        "handles": [["h1"]],
        "metta_expressions": [[expression_text]],
        "assignment": {"x": "h2"},
        "assignment_metta": {"x": binding_text},
        "importance": importance,
        "strength": 0.9,
    }


_COMPLETED = {
    "command": "execution_status",
    "params": {"status": "completed", "total_items": 2, "duration_ms": 3},
}


def test_query_pins_the_request_and_reads_answers_as_atoms():
    das = ScriptedDAS([
        {
            "command": "query_answers",
            "params": {
                "execution_id": "exec-1",
                "seq": 1,
                "answers": [
                    _answer_item('"monkey"', '(Similarity "human" "monkey")'),
                    _answer_item('"chimp"', '(Similarity "human" "chimp")', 0.4),
                ],
                "received_count": 2,
            },
        },
        _COMPLETED,
    ])
    answers = das.query(S.Similarity(Gnd("human"), V.x), max_answers=5)

    method, path, body = das.posted[-1]
    assert (method, path) == ("POST", "/command-router/executions")
    assert body == {
        "command": "query",
        "params": {
            "query": {
                "syntax": "metta",
                "tokens": ['(Similarity "human" %x)'],
            },
            "use_metta_as_query_tokens": True,
            "populate_metta_mapping": True,
            "max_answers": 5,
        },
    }
    assert [a["x"] for a in answers] == [Gnd("monkey"), Gnd("chimp")]
    assert answers[0].expressions == [parse('(Similarity "human" "monkey")')]
    assert answers[0].importance == 0.5


def test_two_patterns_compose_as_a_server_side_and():
    das = ScriptedDAS([_COMPLETED])
    das.query(S.f(V.x), S.g(V.x))
    token = das.posted[-1][2]["params"]["query"]["tokens"][0]
    assert token == "(and (f %x) (g %x))"


def test_error_status_raises_with_the_servers_message():
    das = ScriptedDAS([
        {
            "command": "execution_status",
            "params": {"status": "error", "message": "no such context"},
        },
    ])
    with pytest.raises(DASError, match="no such context"):
        das.query(S.f(V.x))


def test_query_and_count_require_completed_terminal_event():
    partial = {
        "command": "query_answers",
        "params": {"answers": [_answer_item('"partial"', "(f partial)")]},
    }
    with pytest.raises(DASError, match="query stream closed before completing"):
        ScriptedDAS([partial]).query(S.f(V.x))
    with pytest.raises(DASError, match="answer stream closed before completing"):
        ScriptedDAS([partial]).count(S.f(V.x))

    aborted = {
        "command": "execution_status",
        "params": {"status": "aborted", "message": "worker stopped"},
    }
    with pytest.raises(DASError, match=r"query was aborted.*worker stopped"):
        ScriptedDAS([aborted]).query(S.f(V.x))
    with pytest.raises(DASError, match=r"count was aborted.*worker stopped"):
        ScriptedDAS([aborted]).count(S.f(V.x))


def test_completed_query_closes_its_event_stream(monkeypatch):
    class TrackedStream:
        def __init__(self):
            self._events = iter([("status", _COMPLETED["params"])])
            self.closed = False

        def __iter__(self):
            return self

        def __next__(self):
            return next(self._events)

        def close(self):
            self.closed = True

    das = ScriptedDAS([])
    stream = TrackedStream()
    monkeypatch.setattr(das, "_answer_stream", lambda _execution_id: stream)

    assert das.query(S.f(V.x)) == []
    assert stream.closed


def test_count_answers_the_servers_total():
    das = ScriptedDAS([
        {
            "command": "execution_status",
            "params": {"status": "completed", "total_items": 41999},
        },
    ])
    assert das.count(S.f(V.x)) == 41999
    assert das.posted[-1][2]["params"]["count_flag"] is True


def test_das_space_joins_with_native_facts(metta):
    das = ScriptedDAS([
        {
            "command": "query_answers",
            "params": {
                "execution_id": "exec-1",
                "seq": 1,
                "answers": [
                    _answer_item('"monkey"', '(Similarity human monkey)'),
                ],
                "received_count": 1,
            },
        },
        _COMPLETED,
    ])
    metta.register_space("&das-scripted", DASSpace(das))
    try:
        space = metta.space("&das-scripted")
        rows = space.query(S.Similarity(S.human, V.who))
        assert [row.who for row in rows] == [S.monkey]
        metta.add(S.habitat(S.monkey, S.jungle))
        groups = metta.run(
            "!(match &das-scripted (Similarity human $who)"
            " (match &self (habitat $who $where) ($who $where)))"
        )
        assert groups == [[expr(S.monkey, S.jungle)]]
        # Direct provider calls raise DASError; through the engine the
        # refusal crosses janus and surfaces as EngineError, the provider
        # convention, still naming the unsupported operation.
        with pytest.raises(DASError, match="read-only"):
            DASSpace(das).add(S.f(S.a))
        with pytest.raises(EngineError, match="does not implement add"):
            space.add(S.f(S.a))
    finally:
        metta.unregister_space("&das-scripted")
        metta.remove(S.habitat(S.monkey, S.jungle))


def test_ping_is_false_when_nothing_listens():
    assert DAS("http://127.0.0.1:9", timeout=0.5).ping() is False


@pytest.mark.parametrize(
    ("url", "scheme"),
    [
        ("file:///etc/passwd", "file"),
        ("ftp://example.test/data", "ftp"),
        ("data:text/plain,secret", "data"),
        ("example.test/api", "<missing>"),
    ],
)
def test_das_refuses_non_http_urls(url, scheme):
    with pytest.raises(DASError, match=scheme):
        DAS(url)


def test_das_accepts_http_and_https_urls():
    assert DAS("http://example.test/api/")._base == "http://example.test/api"
    assert DAS("https://example.test/api/")._base == "https://example.test/api"


@pytest.mark.parametrize("timeout", [0, -1, float("inf"), float("nan"), "invalid"])
def test_das_refuses_invalid_timeouts(timeout):
    with pytest.raises(ValueError, match="timeout"):
        DAS("http://example.test", timeout=timeout)


def test_plain_http_error_body_is_reported(monkeypatch):
    das = DAS("http://scripted")
    monkeypatch.setattr(
        type(das._endpoint),
        "request",
        lambda self, *args, **kwargs: (500, "failure", b"router failure"),
    )
    with pytest.raises(DASError, match=r"500.*router failure"):
        das._request("GET", "/probe")


def test_das_transport_logs_method_path_and_status(monkeypatch, caplog):
    das = DAS("http://scripted")
    monkeypatch.setattr(
        type(das._endpoint),
        "request",
        lambda self, *args, **kwargs: (200, "OK", b'{"ready": true}'),
    )
    with caplog.at_level(logging.DEBUG, logger="petta.das"):
        assert das._request("GET", "/probe") == {"ready": True}
    assert "sending DAS GET /probe" in caplog.text
    assert "answered with HTTP 200" in caplog.text


def test_das_space_refuses_unsupported_composed_operations_at_entry(metta):
    name = "&das-capability-test"
    metta.register_space(name, DASSpace(ScriptedDAS([_COMPLETED])))
    try:
        space = metta.space(name)
        with pytest.raises(PettaError, match=r"DASSpace.*cannot enumerate"):
            space.lint()
        with pytest.raises(PettaError, match=r"DASSpace.*cannot enumerate"):
            space.digest()
        with pytest.raises(
            PettaError, match=r"DASSpace.*no event source.*subscription"
        ):
            space.subscribe(S.watched(V.x))
    finally:
        metta.unregister_space(name)


class LegacyScriptedDAS(DAS):
    """Speaks like the deployed 1.2.0-rc images: refuses the enveloped
    shape with the router's own 400 text, accepts the flat one, and
    streams flat events with answer chunks under data."""

    def __init__(self, events):
        super().__init__("http://scripted:0")
        self.posted = []
        self._script = list(events)

    def _request(self, method, path, body=None):
        self.posted.append((method, path, body))
        if path == "/command-router/executions":
            if "command_type" not in (body or {}):
                raise DASError(
                    "DAS POST /command-router/executions answered 400: "
                    '{"error":"Missing fields: command_type, command_text"}'
                )
            return {"execution_id": "exec-legacy", "status": "pending"}
        return {}

    def _events(self, execution_id):
        yield from self._script


def test_legacy_dialect_negotiates_tokens_and_handle_answers():
    das = LegacyScriptedDAS([
        {"execution_id": "exec-legacy", "status": "running"},
        {"data": [{
            "assignment": {"a": "3225ea79", "b": "181a1943"},
            "assignment_metta": {},
            "handles": [["ecb646aa"]],
            "metta_expressions": [[]],
            "importance": 0.0,
            "strength": 0.0,
        }]},
        {"execution_id": "exec-legacy", "status": "completed",
         "total_items": 1},
    ])
    answers = das.query(S.Similarity(V.a, V.b))
    body = das.posted[-1][2]
    assert body["command_type"] == "query"
    assert body["command_text"] == (
        "LINK_TEMPLATE Expression 3 NODE Symbol Similarity "
        "VARIABLE a VARIABLE b"
    )
    assert answers[0].handles == {"a": "3225ea79", "b": "181a1943"}
    assert answers[0]["a"] == Gnd("3225ea79")
    assert das._dialect == "legacy"


def test_token_rendering_distinguishes_ground_links_from_templates():
    assert _render_tokens(S.f(S.g(S.a), V.x)) == (
        "LINK_TEMPLATE Expression 3 NODE Symbol f "
        "LINK Expression 2 NODE Symbol g NODE Symbol a VARIABLE x"
    )


_LIVE_URL = os.environ.get("PETTA_DAS_URL", "http://localhost:40009")


@pytest.fixture(scope="module")
def live_das():
    pytest.importorskip("websocket")
    das = DAS(_LIVE_URL, timeout=1.0)
    if not das.ping():
        pytest.skip(f"no DAS command router answering at {_LIVE_URL}")
    return DAS(_LIVE_URL, timeout=20.0)


def test_live_router_round_trip(live_das):
    das = live_das
    answers = das.query(S.Similarity(V.a, V.b), max_answers=5)
    assert answers, "the loaded knowledge base answered nothing"
    assert all(answer.handles for answer in answers)
    total = das.count(S.Similarity(V.a, V.b))
    assert total >= len(answers) > 0
    execution_id = das._start_query(
        (S.Similarity(V.a, V.b),), False, False, None, {}
    )
    das.cancel(execution_id)
    assert das.status(execution_id)["status"] in (
        "pending", "running", "completed", "aborted"
    )
