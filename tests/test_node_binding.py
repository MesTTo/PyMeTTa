"""Purpose: hold the Node binding to the same conformance corpus the shipped
Python host answers, so the seam has a second consumer rather than one.

The corpus is bindings/node/kit/corpus.json and it records cases, never
answers: the Python host supplies those here, in the same process and at the
same moment, so the two hosts are compared against each other rather than
against a copy of one of them that could go stale.

Assumes:
  - node and bindings/node/node_modules/swipl-wasm are present, the same
    optional-toolchain shape test_typescript_space.py already has
Guarantees:
  - every corpus atom crosses both codecs to the same wire form
    [tested test_a_second_language_binding_passes_the_same_conformance_kit]
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
import re
import shutil
import struct
import subprocess
from pathlib import Path

import pytest

import petta
from petta.atoms import atom_from_wire

_BINDING = Path(__file__).resolve().parents[2] / "bindings" / "node"
_CORPUS = json.loads((_BINDING / "kit" / "corpus.json").read_text(encoding="utf-8"))

# What the WebAssembly build refuses at boot, as bindings/node/index.mjs names
# it. Restated here so the two have to agree: a refusal that appears in one
# and not the other is a capability that moved without anyone saying so.
_EXPECTED_REFUSALS = [
    ("src/metta.pl", "library(thread)"),
    ("src/metta.pl", "library(time)"),
    ("src/metta.pl", "library(process)"),
    ("lib/lib_gitimport.pl", "library(process)"),
]

# Where the two hosts render the SAME atom differently, measured 2026-08-20.
# It is a pinned inventory rather than a filter: a divergence that is not
# listed fails the comparison, and one that is listed carries why.
#
# petta.atoms.Gnd.__str__ renders a number with Python's own repr, so a float
# that needs an exponent is spelled by Python and not by the engine's swrite/2,
# which is the published writer and what the Node binding reports. Both denote
# the same double; only the spelling differs. This is the Python surface's own
# second writer and it predates this binding.
_KNOWN_TEXT_DIVERGENCES = {
    ("1.0e+20", "1e+20"),
}

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
    half of reading it, the mirror of numberFromText in index.mjs."""
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


def _wire_from_transport(transport: list) -> list:
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
    canonical about how it spells."""
    return _comparable(_wire_from_transport(transport))


@pytest.fixture(scope="module")
def node_report() -> dict:
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    if not (_BINDING / "node_modules" / "swipl-wasm").is_dir():
        pytest.skip("run npm ci in bindings/node to fetch swipl-wasm")
    finished = subprocess.run(
        ["node", str(_BINDING / "kit" / "run.mjs")],
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-4000:]
    return json.loads(finished.stdout)


def test_a_second_language_binding_passes_the_same_conformance_kit(node_report: dict) -> None:
    """Every corpus case, answered by both hosts, agreeing on the wire."""
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
