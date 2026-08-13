"""Purpose: petta.das against a scripted command router. Request bodies
are pinned to the router's own validated parameter schema, event shapes
are copied from the C++ emitters (query_answers carries "answers",
completion carries "total_items", errors carry "message"), answers read
back as petta atoms, and a DASSpace registered on a real engine joins
DAS candidates with native facts through the engine's own unification.
A live-router test runs only when PETTA_DAS_URL answers ping.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import json
import os

import pytest

from petta import EngineError, S, V, expr
from petta.atoms import Gnd, parse
from petta.das import DAS, DASAnswer, DASError, DASSpace


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
        # convention, still carrying the message.
        with pytest.raises(DASError, match="read-only"):
            DASSpace(das).add(S.f(S.a))
        with pytest.raises(EngineError, match="read-only"):
            space.add(S.f(S.a))
    finally:
        metta.unregister_space("&das-scripted")
        metta.remove(S.habitat(S.monkey, S.jungle))


def test_ping_is_false_when_nothing_listens():
    assert DAS("http://127.0.0.1:9", timeout=0.5).ping() is False


_LIVE_URL = os.environ.get("PETTA_DAS_URL", "http://localhost:40009")


@pytest.mark.skipif(
    not DAS(_LIVE_URL, timeout=1.0).ping(),
    reason=f"no DAS command router answering at {_LIVE_URL}",
)
def test_live_router_round_trip():
    das = DAS(_LIVE_URL)
    execution_id = das.execute(
        "query",
        {
            "query": {"syntax": "metta", "tokens": ["(Similarity %a %b)"]},
            "use_metta_as_query_tokens": True,
            "populate_metta_mapping": True,
            "max_answers": 1,
        },
    )
    assert das.status(execution_id)["status"] in (
        "pending", "running", "completed"
    )
    das.cancel(execution_id)
