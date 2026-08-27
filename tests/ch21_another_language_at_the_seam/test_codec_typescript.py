"""Purpose: run the same golden corpus against an implementation that shares
no code with this package at all.

The two shipped codecs are two implementations in two languages and both of
them are ours, so both could be wrong the same way. The TypeScript reference
server under extensions/python/examples/integration/typescript_space/ is the
independent one: written from the protocol, zero dependencies, and it is a
STORE rather than a whole binding, which is what a Julia or Rust space
provider would be too. Certifying it is how the corpus earns the claim that
a new binding can be written from CODEC.md and checked against the kit.

It is driven over HTTP through the shipped .js bundle, so this test adds no
diff to the server's own sources and reads the wire exactly as a client
does.

Guarantees:
  - the reference server passes every corpus case its profile puts in
    scope, except the divergences named below, and the divergence set is
    pinned so a new one fails
    [tested test_a_second_implementation_passes_the_same_corpus]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import itertools
import json
import shutil
import signal
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from metta.testing import check_codec, codec_plan

_SERVER = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "integration"
    / "typescript_space"
    / "space_server.js"
)
_NODE = shutil.which("node")

# Measured 2026-08-20 against the shipped bundle, on the corpus's first
# contact with an implementation that is not ours. Two causes:
#
#   isWireAtom validates the g tag with `case "g": return true`, so a number
#   and a whole JSON object are both stored under a tag CODEC.md says
#   carries text and both metta-side codecs refuse.
#
#   JSON.stringify(1.0) writes 1, JavaScript having one number type, so an
#   integral float comes back an integer. !(== 1.0 1) answers False, so that
#   is a different atom, the same failure as rounding a wide integer.
#
# The server is a reference implementation under extensions/python/examples/ rather
# than one of the two shipped codecs, so these are recorded here rather than
# patched. Shrink this list, never grow it.
KNOWN_DIVERGENCES = {
    "refuse-string-payload-number",
    "refuse-string-payload-object",
    "float-integral",
    "float-large-exponent",
}


class TypeScriptStore:
    """The reference server as a codec driver, over its own HTTP protocol.

    A store neither reads MeTTa source nor prints an atom, so those two legs
    are absent rather than failing; roundtrip and transport are one HTTP
    exchange, because the JSON parse and the wire validation both happen
    inside the request that carries the atom.
    """

    name = "typescript"
    tags = frozenset({"s", "v", "n", "g", "e"})
    frames = frozenset()
    printer = None
    reads_text = False
    exact_integers = False
    non_finite = False
    resolves_anonymous = False
    runs_programs = False

    def __init__(self, base: str):  # noqa: D107  -- the test double construction contract is local to its containing scenario
        self._base = base
        self._spaces = itertools.count()

    def _post(self, operation: str, payload: dict) -> dict:
        # json.dumps rather than the engine's codec, because this is the
        # client's own serialisation and a naive client is what a server has
        # to be safe against: allow_nan writes Infinity, which is not JSON.
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            f"{self._base}/{operation}", data=body, headers={"content-type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as answer:
                return json.loads(answer.read())
        except urllib.error.HTTPError as exc:
            raise ValueError(json.loads(exc.read())["error"]) from None

    def roundtrip(self, wire):
        """Store the atom in a space of its own and read it back."""
        space = f"&codec-kit-{next(self._spaces)}"
        self._post("add", {"space": space, "atom": wire})
        held = self._post("atoms", {"space": space})["atoms"]
        if len(held) != 1:
            msg = f"{space} holds {len(held)} atoms after one add"
            raise ValueError(msg)
        return held[0]

    transport = roundtrip

    def host_value(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        msg = "a core-profile store declares no o tag"
        raise AssertionError(msg)


@pytest.fixture
def typescript_store():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    if _NODE is None:
        pytest.skip("node is not installed, so the independent implementation cannot run")
    # A fixed argv, no shell.
    process = subprocess.Popen(
        [_NODE, str(_SERVER), "--port", "0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    try:
        ready = json.loads(process.stdout.readline())
        yield TypeScriptStore(f"http://127.0.0.1:{ready['listening']['port']}")
    finally:
        process.send_signal(signal.SIGTERM)
        process.wait(timeout=10)


def test_a_second_implementation_passes_the_same_corpus(typescript_store):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    complaints = check_codec(typescript_store)
    diverged = {
        case_id
        for case_id in KNOWN_DIVERGENCES
        if any(f"/{case_id}:" in complaint for complaint in complaints)
    }
    unexpected = [
        complaint
        for complaint in complaints
        if not any(f"/{case_id}:" in complaint for case_id in KNOWN_DIVERGENCES)
    ]
    assert unexpected == []
    assert diverged == KNOWN_DIVERGENCES, (
        "a pinned divergence stopped diverging; delete it from "
        "KNOWN_DIVERGENCES rather than leaving the list stale"
    )


def test_the_store_runs_the_wire_legs_and_says_which_it_does_not(typescript_store):
    """A store has no reader and no printer, and the plan says so rather
    than the kit quietly checking two legs instead of four.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    plan = codec_plan(typescript_store)
    assert plan["legs"] == ["roundtrip", "transport"]
    left_out = dict(plan["out_of_profile"])
    assert left_out["boolean-true"] == "tags ['b']"
    assert left_out["host-reference"] == "tags ['o']"
    assert left_out["integer-beyond-double"] == "needs exact_integers"
    assert left_out["undefined-truth"] == "frame u"
    assert left_out["arithmetic"] == "runs no programs"
