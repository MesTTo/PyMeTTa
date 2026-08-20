"""Purpose: hold the Node binding to the codec, twice over, so the seam has a
second consumer rather than one.

The golden corpus at tests/codec/corpus.json is the grammar's authority, and
the binding is driven through the kit's own CodecDriver. Beside it,
bindings/node/kit/corpus.json records cases and never answers, because the
shipped Python host supplies those here in the same moment: that half compares
two LIVE hosts, where the kit compares one host against a written-down
grammar, and a codec can satisfy the grammar while disagreeing with the engine
beside it.

Assumes:
  - node and bindings/node/node_modules/swipl-wasm are present, the same
    optional-toolchain shape test_typescript_space.py already has
Guarantees:
  - the Node binding answers the golden corpus with no complaints, over
    every leg a whole binding has
    [tested test_a_second_language_binding_passes_the_same_conformance_kit]
  - the two live hosts answer the same programs the same way
    [tested test_the_node_binding_and_the_python_host_answer_the_same_programs]
  - both hosts carry the signed-i64 Number/BigInt boundary as exact integers
    [tested test_a_second_language_binding_passes_the_same_conformance_kit,
    test_the_node_binding_and_the_python_host_answer_the_same_programs]
  - the Node binding computes exactly the answers it is asked for, proven on
    an unbounded generator with a witness space
    [tested test_the_node_binding_leaves_the_third_answer_uncomputed]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import math
import re
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

import pytest

import petta
from petta.atoms import atom_from_wire

_BINDING = Path(__file__).resolve().parents[3] / "bindings" / "node"
_CORPUS = json.loads((_BINDING / "kit" / "corpus.json").read_text(encoding="utf-8"))

# What the WebAssembly build refuses at boot, as bindings/node/index.mjs names
# it. Restated here so the two have to agree: a refusal that appears in one
# and not the other is a capability that moved without anyone saying so.
_EXPECTED_REFUSALS = [
    ("engine/metta.pl", "library(thread)"),
    ("engine/metta.pl", "library(time)"),
    ("engine/metta.pl", "library(process)"),
    ("lib/lib_gitimport.pl", "library(process)"),
]

# Where the two hosts render the SAME atom differently. It is a pinned
# inventory rather than a filter: a divergence that is not listed fails the
# comparison, and one that is listed carries why. It is EMPTY because
# Gnd.__str__ implements the same float layout law the engine's swrite/2
# does, so the one entry it held (repr's 1e+20 against the engine's
# spelling) resolved when the Python surface stopped being a second number
# writer; the mechanism stays for the next real divergence.
_KNOWN_TEXT_DIVERGENCES: set[tuple[str, str]] = set()

# A fresh variable is printed under the name the writer numbered it, which is
# a counter and not part of the atom, so the two hosts number the same answer
# differently. The wire comparison drops the name for that reason and the text
# comparison drops it for the same one.
_VARIABLE_NAME = re.compile(r"\$_\d+")


def _named_apart(text: str) -> str:
    return _VARIABLE_NAME.sub("$_", text)


def _float_bits(value: float) -> str:
    return struct.pack(">d", value).hex()


def _comparable(wire: list) -> list:
    """The form both hosts compare in.

    A number carries its kind because JavaScript splits integers and floats
    across BigInt and number while Python splits them across int and float,
    and a float carries its bits because that is exact for every double. A
    variable compares by tag alone: its wire name is what the writer numbered
    it and changes between runs.
    """
    tag = wire[0]
    if tag == "v":
        return ["v"]
    if tag == "n":
        value = wire[1]
        if isinstance(value, int) and not isinstance(value, bool):
            return ["n", "i", str(value)]
        return ["n", "f", _float_bits(float(value))]
    if tag == "b":
        return ["b", "true" if wire[1] in (True, "true") else "false"]
    if tag == "e":
        return ["e", [_comparable(item) for item in wire[1]]]
    return [tag, wire[1]]


def _number_from_text(text: str) -> int | float:
    """The corpus writes a number as canonical Prolog text; this is Python's
    half of reading it, the mirror of numberFromText in index.mjs.
    """
    if text.lstrip("-").isdigit():
        return int(text)
    if text.endswith("Inf"):
        return float("-inf") if text.startswith("-") else float("inf")
    if text.endswith("NaN"):
        return float("nan")
    return float(text)


def _atom_from_transport(transport: list):
    tag = transport[0]
    if tag == "n":
        return atom_from_wire(["n", _number_from_text(transport[1])])
    if tag == "e":
        return atom_from_wire(["e", [_wire_from_transport(item) for item in transport[1]]])
    return atom_from_wire(transport)


def _wire_from_transport(transport: Any) -> Any:
    if not isinstance(transport, list) or len(transport) != 2:
        return transport
    if transport[0] == "n":
        return ["n", _number_from_text(transport[1])]
    if transport[0] == "e":
        return ["e", [_wire_from_transport(item) for item in transport[1]]]
    return transport


def _comparable_transport(transport: list) -> list:
    """A transport atom in the comparison form, so two spellings of one number
    compare as the number. The engine writes 1.0e+20 and JavaScript writes
    100000000000000000000.0 for the same double, and the reader takes both:
    the transport carries a value, and only the engine's own writer is
    canonical about how it spells.
    """
    return _comparable(_wire_from_transport(transport))


# --------------------------------------------------------------- the kit driver
#
# The codec kit drives an implementation through one object each, the same
# way bindings/python/tests/test_codec_typescript.py drives the reference store. This
# is that object for the Node binding, and it runs every leg rather than the
# store's two: a whole binding reads MeTTa source, prints through the engine's
# own writer, and runs programs.


def _number_to_text(value: Any) -> Any:
    """A number in the spelling SWI's ~q writes and its reader takes back,
    which is what bridge.pl's transport carries. The mirror of numberToText in
    index.mjs, and it exists because JSON has one number kind while the wire
    must preserve both integer width and the integer/float distinction.

    A payload that is not a number at all goes through untouched, so the
    corpus's malformed cases are refused by the codec under test rather than
    by this converter.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    if isinstance(value, int):
        return str(value)
    if math.isnan(value):
        return "1.5NaN"
    if value == math.inf:
        return "1.0Inf"
    if value == -math.inf:
        return "-1.0Inf"
    text = repr(value)
    if "." in text:
        return text
    exponent = text.find("e")
    if exponent >= 0:
        return f"{text[:exponent]}.0{text[exponent:]}"
    return f"{text}.0"


def _transport_from_wire(wire: Any) -> Any:
    if not isinstance(wire, list) or len(wire) != 2:
        return wire
    if wire[0] == "n":
        return ["n", _number_to_text(wire[1])]
    if wire[0] == "e" and isinstance(wire[1], list):
        return ["e", [_transport_from_wire(item) for item in wire[1]]]
    return wire


class NodeBinding:
    """The Node binding as one codec driver, over a line of JSON per call.

    Three tags stay outside its profile and each for its own reason. `o` is a
    live host value and no JavaScript object is ever inside this engine; `h`
    is a native handle, whose whole point is a registry identity this binding
    mints none of; and the three frames belong to the remote wire, which an
    in-process binding does not speak.
    """

    name = "node"
    tags = frozenset({"s", "v", "n", "g", "e", "b"})
    frames: frozenset[str] = frozenset()
    printer = "engine"
    reads_text = True
    exact_integers = True
    non_finite = True
    resolves_anonymous = True
    runs_programs = True

    def __init__(self, process: subprocess.Popen[str]) -> None:
        if process.stdin is None or process.stdout is None:
            raise RuntimeError("the Node driver was started without its pipes")
        self._process = process
        self._stdin = process.stdin
        self._stdout = process.stdout

    def close(self) -> None:
        """Closing the request stream ends the driver's read loop, so it exits
        on its own rather than being signalled.
        """
        self._stdin.close()
        self._process.wait(timeout=30)

    def _call(self, op: str, **payload: Any) -> Any:
        self._stdin.write(f"{json.dumps({'op': op, **payload})}\n")
        self._stdin.flush()
        line = self._stdout.readline()
        if line == "":
            raise RuntimeError(f"the Node driver ended before answering {op}")
        answer = json.loads(line)
        if "error" in answer:
            raise ValueError(answer["error"])
        return answer["ok"]

    def read(self, text: str) -> Any:
        return _wire_from_transport(self._call("read", text=text))

    def roundtrip(self, wire: Any) -> Any:
        return _wire_from_transport(self._call("roundtrip", transport=_transport_from_wire(wire)))

    def transport(self, wire: Any) -> Any:
        return _wire_from_transport(self._call("transport", transport=_transport_from_wire(wire)))

    def render(self, wire: Any) -> str:
        return str(self._call("render", transport=_transport_from_wire(wire)))

    def transcript(self, program: str) -> list:
        groups = self._call("transcript", program=program)
        return [[_wire_from_transport(answer) for answer in group] for group in groups]

    def host_value(self) -> Any:
        raise AssertionError("the Node binding declares no o tag")

    def frame(self, wire: Any) -> dict:
        raise AssertionError("the Node binding declares no frames")


@pytest.fixture(scope="module")
def node_driver():
    _need_node()
    process = subprocess.Popen(
        ["node", str(_BINDING / "kit" / "driver.mjs")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    driver = NodeBinding(process)
    try:
        yield driver
    finally:
        driver.close()


def _need_node() -> None:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    if not (_BINDING / "node_modules" / "swipl-wasm").is_dir():
        pytest.skip("run npm ci in bindings/node to fetch swipl-wasm")


@pytest.fixture(scope="module")
def node_report() -> dict:
    _need_node()
    finished = subprocess.run(
        ["node", str(_BINDING / "kit" / "run.mjs")],
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-4000:]
    return json.loads(finished.stdout)


def test_a_second_language_binding_passes_the_same_conformance_kit(node_driver) -> None:
    """The golden corpus, run against the Node binding.

    The kit is the authority on the grammar and this is the second language
    held to it. Measured 2026-08-20 against the corpus on the branch that
    writes it, before either merged: 67 cases in scope over all four legs, zero
    complaints. It caught a real defect on the way, which is what a kit is
    for: the decoder minted a fresh variable per occurrence, so (f $x $x)
    came back as (f $x $y).
    """
    pytest.importorskip(
        "petta._codec_kit",
        reason="the codec kit is not in this tree yet; this runs once it merges",
    )
    from petta.testing import check_codec

    assert check_codec(node_driver) == []


def test_the_binding_runs_every_leg_and_says_which_cases_it_does_not(node_driver) -> None:
    """A binding is not a store: it reads source and prints atoms too, so all
    four legs run rather than the two a wire-carrying provider has.

    What stays out is declared rather than dropped, and what is pinned here is
    the REASON rather than the case list: a case added to the corpus is not
    this binding changing, but a case falling out because a capability was
    given up would be.
    """
    pytest.importorskip(
        "petta._codec_kit",
        reason="the codec kit is not in this tree yet; this runs once it merges",
    )
    from petta.testing import codec_plan

    plan = codec_plan(node_driver)
    assert plan["legs"] == ["read", "render", "roundtrip", "transport"]
    assert plan["run"], "the plan put every case out of scope"
    for case, why in plan["out_of_profile"]:
        # A capability reason would mean this binding claimed less than it
        # carries, which is the way a kit passes on a small profile.
        assert why.startswith(("tags [", "frame ")), f"{case} is out of profile: {why}"
        if why.startswith("tags ["):
            assert why == "tags ['o']", f"{case} needs a tag beyond o: {why}"


def test_the_node_binding_and_the_python_host_answer_the_same_programs(node_report: dict) -> None:
    """Every case of this binding's own corpus, answered by both hosts.

    Independent of the kit above and kept beside it: this compares two LIVE
    hosts on the same programs in the same moment, where the kit compares one
    host against a written-down grammar. A codec can satisfy the grammar and
    still disagree with the engine that ships beside it.
    """
    engine = petta.MeTTa()

    reported = [(entry["file"], entry["missing"]) for entry in node_report["refusals"]]
    assert reported == _EXPECTED_REFUSALS

    assert len(node_report["programs"]) == len(_CORPUS["programs"])
    divergences: set[tuple[str, str]] = set()
    for case, ran in zip(_CORPUS["programs"], node_report["programs"], strict=True):
        source = case["source"]
        assert ran["source"] == source
        assert "error" not in ran, ran.get("error")
        expected = engine.run(source)
        assert [len(group) for group in expected] == [len(group) for group in ran["groups"]], source
        for here, there in zip(expected, ran["groups"], strict=True):
            for atom, answer in zip(here, there, strict=True):
                assert _comparable(atom.to_wire()) == answer["wire"], f"{source}: {atom!r}"
                if _named_apart(str(atom)) != _named_apart(answer["text"]):
                    divergences.add((answer["text"], str(atom)))

    assert len(node_report["atoms"]) == len(_CORPUS["atoms"])
    for case, crossed in zip(_CORPUS["atoms"], node_report["atoms"], strict=True):
        transport = case["transport"]
        assert crossed["transport"] == transport
        assert "error" not in crossed, crossed.get("error")
        atom = _atom_from_transport(transport)
        expected = _comparable(atom.to_wire())
        assert crossed["wire"] == expected, transport
        assert crossed["roundTrip"] == expected, f"{transport} did not survive the engine"
        assert _comparable_transport(crossed["backToTransport"]) == expected, transport
        if _named_apart(str(atom)) != _named_apart(crossed["text"]):
            divergences.add((crossed["text"], str(atom)))

    assert len(node_report["refused"]) == len(_CORPUS["refused"])
    for case, refusal in zip(_CORPUS["refused"], node_report["refused"], strict=True):
        assert refusal["refused"] is True, f"{case['transport']} was accepted: {case['why']}"
        assert refusal["message"], case["transport"]

    assert divergences == _KNOWN_TEXT_DIVERGENCES


def test_the_node_binding_leaves_the_third_answer_uncomputed(node_report: dict) -> None:
    """Two answers pulled from an unbounded generator, and exactly two
    produced.

    The generator recurses through superpose and never ends, so a binding that
    computed the group before handing any of it over could not reach the
    assertion at all. The witness space holds one atom per answer the engine
    actually produced, which is what says the third was never computed rather
    than only that two were read.
    """
    streaming = node_report["streaming"]
    assert streaming["pulled"] == ["1", "2"]
    assert streaming["produced"] == ["((produced 1) (produced 2))"]
