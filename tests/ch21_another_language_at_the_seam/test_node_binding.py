"""Purpose: hold the Node binding to the codec, twice over, so the seam has a
second consumer rather than one.

The golden corpus at tests/codec/corpus.json is the grammar's authority, and
the binding is driven through the kit's own CodecDriver. Beside it,
extensions/node/kit/corpus.json records cases and never answers, because the
shipped Python host supplies those here in the same moment: that half compares
two LIVE hosts, where the kit compares one host against a written-down
grammar, and a codec can satisfy the grammar while disagreeing with the engine
beside it.

Assumes:
  - node and extensions/node/node_modules/swipl-wasm are present, the same
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
  - the Node profile carries p as its JavaScript SpaceHandle species on all
    four codec legs [tested
    test_a_second_language_binding_passes_the_same_conformance_kit,
    test_the_binding_runs_every_leg_and_says_which_cases_it_does_not;
    commit=d0631377c5e01a5d34d1c3437e283f87a0fab86f]
  - the Node binding computes exactly the answers it is asked for, proven on
    an unbounded generator with a witness space
    [tested test_the_node_binding_leaves_the_third_answer_uncomputed]
  - the two seats' codecs answer the golden corpus IDENTICALLY, in process and
    over JSON, which is a different question from each satisfying the page
    [tested test_the_two_seats_answer_the_golden_corpus_identically]
  - a number crosses a live remote exchange unchanged in both directions, for
    every class the n tag has, and a non-finite float is refused at both ends
    because JSON has no literal for one
    [tested test_a_python_client_reads_every_number_class_from_a_node_gateway,
    test_a_node_client_reads_every_number_class_from_a_python_gateway,
    test_both_seats_refuse_a_non_finite_float_on_the_json_wire]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

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

import metta
from metta import convert, parse

_BINDING = Path(__file__).resolve().parents[4] / "extensions" / "node"
_CORPUS = json.loads((_BINDING / "kit" / "corpus.json").read_text(encoding="utf-8"))

# What the WebAssembly build refuses at boot, as extensions/node/src/engine.ts
# names it. Restated here so the two have to agree: a refusal that appears in one
# and not the other is a capability that moved without anyone saying so.
# What the WebAssembly build does without, as the ENGINE names it. This was a
# list of (file, missing library) recovered by regex over SWI's boot stderr,
# with library(process) appearing twice because two files asked for it and only
# the file told them apart. The engine declares its platform capabilities now,
# so the host reads them: one row per capability, named for what a program
# loses rather than for which directive failed, and the two files needing
# subprocess are one capability because the cost is the same.
_EXPECTED_REFUSALS = [
    ("concurrency", "library(thread)"),
    ("crypto", "library(crypto)"),
    ("deadlines", "library(time)"),
    ("redis", "library(redis)"),
    ("subprocess", "library(process)"),
]

# Where the two hosts render the SAME atom differently. It is a pinned
# inventory rather than a filter: a divergence that is not listed fails the
# comparison, and one that is listed carries why. It is EMPTY because
# Grounded.__str__ implements the same float layout law the engine's swrite/2
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


_FLOAT_ESCAPES = {"inf": math.inf, "-inf": -math.inf, "nan": math.nan}


def _materialise(value: Any) -> Any:
    """A document with the corpus's `{"$float": ...}` escape resolved.

    JSON has no literal for a non-finite float, so the corpus writes one as an
    escape and both sides of this pipe resolve it. Everything else on the wire
    is a JSON value already: an integer is bare digits, exact at any width, and
    a float carries a point or an exponent.
    """
    if isinstance(value, list):
        if len(value) == 2 and value[0] == "n" and isinstance(value[1], dict):
            return ["n", _FLOAT_ESCAPES[value[1]["$float"]]]
        return [_materialise(item) for item in value]
    if isinstance(value, dict):
        return {key: _materialise(item) for key, item in value.items()}
    return value


def _escaped(value: Any) -> Any:
    """The inverse: a non-finite float written as the escape JSON can carry."""
    if isinstance(value, list):
        if len(value) == 2 and value[0] == "n" and isinstance(value[1], float):
            if math.isnan(value[1]):
                return ["n", {"$float": "nan"}]
            if math.isinf(value[1]):
                return ["n", {"$float": "inf" if value[1] > 0 else "-inf"}]
            return value
        return [_escaped(item) for item in value]
    if isinstance(value, dict):
        return {key: _escaped(item) for key, item in value.items()}
    return value


# --------------------------------------------------------------- the kit driver
#
# The codec kit drives an implementation through one object each, the same way
# extensions/python/tests/ch21_another_language_at_the_seam/test_codec_typescript.py
# drives the reference store. This is that object for the Node binding, and it
# runs every leg rather than the store's two: a whole binding reads MeTTa
# source, prints through the engine's own writer, and runs programs.


class NodeBinding:
    """The Node binding as one codec driver, over a line of JSON per call.

    Two term tags stay outside its profile and each for its own reason. `o` is a
    live host value and no JavaScript object is ever inside this engine; `h`
    is a native handle, whose whole point is a registry identity this binding
    mints none of; and the three frames belong to the remote wire, which an
    in-process binding does not speak.
    """

    name = "node"
    tags = frozenset({"s", "v", "n", "g", "e", "b", "p"})
    frames: frozenset[str] = frozenset()
    printer = "engine"
    reads_text = True
    exact_integers = True
    non_finite = True
    resolves_anonymous = True
    runs_programs = True

    def __init__(self, process: subprocess.Popen[str]) -> None:  # noqa: D107  -- the test double construction contract is local to its containing scenario
        if process.stdin is None or process.stdout is None:
            msg = "the Node driver was started without its pipes"
            raise RuntimeError(msg)
        self._process = process
        self._stdin = process.stdin
        self._stdout = process.stdout

    def close(self) -> None:
        """Closing the request stream ends the driver's read loop, so it exits
        on its own rather than being signalled.
        """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
        self._stdin.close()
        self._process.wait(timeout=30)

    def _call(self, op: str, **payload: Any) -> Any:
        self._stdin.write(f"{json.dumps({'op': op, **payload})}\n")
        self._stdin.flush()
        line = self._stdout.readline()
        if line == "":
            msg = f"the Node driver ended before answering {op}"
            raise RuntimeError(msg)
        answer = json.loads(line)
        if "error" in answer:
            raise ValueError(answer["error"])
        return answer["ok"]

    def read(self, text: str) -> Any:  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return _materialise(self._call("read", text=text))

    def roundtrip(self, wire: Any) -> Any:  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return _materialise(self._call("roundtrip", transport=_escaped(wire)))

    def transport(self, wire: Any) -> Any:  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return _materialise(self._call("transport", transport=_escaped(wire)))

    def render(self, wire: Any) -> str:  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return str(self._call("render", transport=_escaped(wire)))

    def transcript(self, program: str) -> list:  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        groups = self._call("transcript", program=program)
        return [[_materialise(answer) for answer in group] for group in groups]

    def host_value(self) -> Any:  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        msg = "the Node binding declares no o tag"
        raise AssertionError(msg)

    def frame(self, wire: Any) -> dict:  # noqa: ARG002, D102  -- the test double preserves the protocol method signature its caller exercises; the test double method is documented by its containing scenario and protocol
        msg = "the Node binding declares no frames"
        raise AssertionError(msg)


@pytest.fixture(scope="module")
def node_driver():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _need_node()
    process = subprocess.Popen(
        ["node", str(_BINDING / "build" / "kit" / "driver.js")],
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
        pytest.skip("run npm ci in extensions/node to fetch swipl-wasm")
    if not (_BINDING / "build" / "kit" / "run.js").is_file():
        # The binding is TypeScript, and this lane runs its BUILD rather than
        # its sources: a distro Node may be compiled without type stripping
        # (`node_use_amaro` false), and a lane that only ran on the official
        # build would not run here at all. `npm ci` builds through the package's
        # own prepare script, so this note is the same shape as the one above.
        pytest.skip("run npm ci in extensions/node to build its TypeScript")


@pytest.fixture(scope="module")
def node_report() -> dict:  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    _need_node()
    finished = subprocess.run(
        ["node", str(_BINDING / "build" / "kit" / "run.js")],
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
    held to it. Measured 2026-08-26 against the current corpus: 67 cases in
    scope over all four legs, zero complaints. It caught a real defect on the
    way, which is what a kit is for: the decoder minted a fresh variable per
    occurrence, so (f $x $x) came back as (f $x $y).
    """
    pytest.importorskip(
        "metta._codec_kit",
        reason="the codec kit is not in this tree yet; this runs once it merges",
    )
    from metta.testing import check_codec

    assert check_codec(node_driver) == []


def test_the_binding_runs_every_leg_and_says_which_cases_it_does_not(node_driver) -> None:
    """A binding is not a store: it reads source and prints atoms too, so all
    four legs run rather than the two a wire-carrying provider has.

    What stays out is declared rather than dropped, and what is pinned here is
    the REASON rather than the case list: a case added to the corpus is not
    this binding changing, but a case falling out because a capability was
    given up would be.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    pytest.importorskip(
        "metta._codec_kit",
        reason="the codec kit is not in this tree yet; this runs once it merges",
    )
    from metta.testing import codec_plan

    plan = codec_plan(node_driver)
    assert plan["legs"] == ["read", "render", "roundtrip", "transport"]
    # 69, up from 67: the codec's species-tag landing added symbol-ampersand
    # and space-in-expression to the shared corpus, and this binding runs both.
    assert len(plan["run"]) == 69
    assert "space-handle" in plan["run"]
    for case, why in plan["out_of_profile"]:
        # A capability reason would mean this binding claimed less than it
        # carries, which is the way a kit passes on a small profile.
        assert why.startswith(("tags [", "frame ")), f"{case} is out of profile: {why}"
        if why.startswith("tags ["):
            # o is a host object and h an engine-native registry identity;
            # neither exists inside this wasm host.
            assert why in {"tags ['o']", "tags ['h']"}, (
                f"{case} needs a tag beyond o or h: {why}"
            )


def test_the_node_binding_and_the_python_host_answer_the_same_programs(node_report: dict) -> None:
    """Every case of this binding's own corpus, answered by both hosts.

    Independent of the kit above and kept beside it: this compares two LIVE
    hosts on the same programs in the same moment, where the kit compares one
    host against a written-down grammar. A codec can satisfy the grammar and
    still disagree with the engine that ships beside it.
    """
    engine = metta.MeTTa().self

    reported = sorted(
        (entry["capability"], entry["requires"]) for entry in node_report["refusals"]
    )
    assert reported == sorted(_EXPECTED_REFUSALS)

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
                # Both sides through ONE notation: the seat answers MeTTa
                # text and `str(atom)` is the Python surface's own spelling,
                # and a boolean is `true` there and `True` here. Reading the
                # seat's text back into an atom compares the VALUES.
                if _named_apart(str(atom)) != _named_apart(str(parse(answer["text"]))):
                    divergences.add((answer["text"], str(atom)))

    assert len(node_report["atoms"]) == len(_CORPUS["atoms"])
    for case, crossed in zip(_CORPUS["atoms"], node_report["atoms"], strict=True):
        transport = case["transport"]
        assert crossed["transport"] == transport
        assert "error" not in crossed, crossed.get("error")
        atom = convert.atom_from_wire(_materialise(transport))
        expected = _comparable(atom.to_wire())
        assert crossed["wire"] == expected, transport
        assert crossed["roundTrip"] == expected, f"{transport} did not survive the engine"
        assert _comparable(_materialise(crossed["backToTransport"])) == expected, transport
        if _named_apart(str(atom)) != _named_apart(str(parse(crossed["text"]))):
            divergences.add((crossed["text"], str(atom)))

    assert len(node_report["refused"]) == len(_CORPUS["refused"])
    for case, refusal in zip(_CORPUS["refused"], node_report["refused"], strict=True):
        assert refusal["refused"] is True, f"{case['transport']} was accepted: {case['why']}"
        assert refusal["message"], case["transport"]

    assert divergences == _KNOWN_TEXT_DIVERGENCES


def test_the_two_seats_answer_the_golden_corpus_identically(node_driver, metta) -> None:  # noqa: ARG001  -- the engine fixture is what supplies metta._json and Atom.to_wire a runtime; the body reaches them by import rather than through the argument
    """Every case of tests/codec/corpus.json, through both seats, both ways.

    `check_codec` above holds the Node binding to the WRITTEN grammar. This
    holds it to the other IMPLEMENTATION on the same cases, which is a
    different question: two codecs can each satisfy the page and still hand a
    peer something the other refuses, and that is exactly what the `n` tag did
    while this seat carried a number as text and the Python seat carried the
    value.

    Two legs, because the seats have two encodings each. `roundtrip` is the
    in-process one, decode to an atom and encode back, and it carries
    everything including the booleans and the non-finite floats. `transport`
    is the JSON one, and it is compared over what JSON can carry: the Python
    half is `metta._json`, the engine's own codec, which is what the remote
    wire reads and writes.
    """
    from metta import _json
    from metta.testing import codec_corpus, codec_plan

    corpus = codec_corpus()
    running = set(codec_plan(node_driver, corpus=corpus)["run"])
    json_tags = set(corpus["profiles"]["core"]["tags"]) | {"p"}

    round_trips: list[tuple[str, Any, Any]] = []
    transports: list[tuple[str, Any, Any]] = []
    compared = {"roundtrip": 0, "transport": 0}
    for case in corpus["cases"]:
        if case["id"] not in running or "wire" not in case:
            continue
        here = _materialise_corpus(case["wire"])
        compared["roundtrip"] += 1
        node_round = _comparable(node_driver.roundtrip(here))
        python_round = _comparable(convert.atom_from_wire(here).to_wire())
        if node_round != python_round:
            round_trips.append((case["id"], python_round, node_round))
        if set(case.get("tags", ())) - json_tags or case.get("requires") == "non_finite":
            continue
        compared["transport"] += 1
        node_carried = _comparable(node_driver.transport(here))
        python_carried = _comparable(_json.loads(_json.dumps(here)))
        if node_carried != python_carried:
            transports.append((case["id"], python_carried, node_carried))

    assert round_trips == [], "the two seats' in-process codecs disagree"
    assert transports == [], "the two seats' JSON codecs disagree"
    # Pinned, so a corpus that stopped REACHING these legs is visible rather
    # than passing as agreement about nothing. The transport leg runs fewer
    # because the JSON wire carries neither a boolean nor a non-finite float.
    assert compared == {"roundtrip": 39, "transport": 32}


def _materialise_corpus(value: Any) -> Any:
    """The corpus's `$float` escape resolved; `$host` never reaches this seat."""
    return _materialise(value)


# The numbers a remote exchange has to carry without changing, one per class
# the `n` tag has: an integer, a float, a float whose value is whole, a
# negative fraction, and an integer past every JavaScript number.
_EXCHANGED: list = [
    ["e", [["s", "row"], ["n", 42], ["s", "int"]]],
    ["e", [["s", "row"], ["n", 1.5], ["s", "float"]]],
    ["e", [["s", "row"], ["n", 1.0], ["s", "integral-float"]]],
    ["e", [["s", "row"], ["n", -0.25], ["s", "negative-fraction"]]],
    ["e", [["s", "row"], ["n", 9007199254740993], ["s", "beyond-double"]]],
    ["e", [["s", "row"], ["n", 1208925819614629174706176], ["s", "beyond-i64"]]],
]


def _node_gateway(atoms: list):
    """A Node `serve()` holding these atoms, and the URL it listens on."""
    process = subprocess.Popen(
        ["node", str(_BINDING / "build" / "kit" / "remote.js"), "serve"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(f"{json.dumps({'atoms': atoms})}\n")
    process.stdin.close()
    ready = json.loads(process.stdout.readline())
    return process, f"http://127.0.0.1:{ready['listening']['port']}"


def test_a_python_client_reads_every_number_class_from_a_node_gateway() -> None:
    """The Python seat's own RemoteSpace, against this seat's own serve().

    The interoperability `src/remote.ts` claims in its header, run. It did not
    hold while this seat put a number on the wire as TEXT: the Python client
    refused every one of these with "wire number payload must be numeric".
    """
    _need_node()
    if not (_BINDING / "build" / "kit" / "remote.js").is_file():
        pytest.skip("run npm ci in extensions/node to build its TypeScript")
    from metta import remote

    process, url = _node_gateway(_EXCHANGED)
    try:
        space = remote.RemoteSpace(remote.connect(url), space="&served")
        read = sorted(
            (_comparable(atom.to_wire()) for atom in space.atoms()),
            key=repr,
        )
    finally:
        process.terminate()
        process.wait(timeout=10)
    expected = sorted((_comparable(term) for term in _EXCHANGED), key=repr)
    assert read == expected


def test_a_node_client_reads_every_number_class_from_a_python_gateway(metta) -> None:
    """The same exchange the other way round, this seat's client and the
    Python seat's serve().
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    _need_node()
    if not (_BINDING / "build" / "kit" / "remote.js").is_file():
        pytest.skip("run npm ci in extensions/node to build its TypeScript")
    from metta import remote

    with metta._new_space() as scratch:
        for term in _EXCHANGED:
            scratch.add(convert.atom_from_wire(term))
        server = remote.serve(scratch, spaces=[scratch.name])
        try:
            finished = subprocess.run(
                [
                    "node",
                    str(_BINDING / "build" / "kit" / "remote.js"),
                    "attach",
                    f"http://127.0.0.1:{server.port}",
                    scratch.name,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        finally:
            server.close()
    assert finished.returncode == 0, finished.stderr[-4000:]
    read = sorted(
        (_comparable(term) for term in json.loads(finished.stdout)["atoms"]),
        key=repr,
    )
    expected = sorted((_comparable(term) for term in _EXCHANGED), key=repr)
    assert read == expected


def test_both_seats_refuse_a_non_finite_float_on_the_json_wire() -> None:
    """JSON has no literal for one, so neither end invents a spelling.

    CODEC.md: "JSON has no literal for either, so both ends of the JSON wire
    refuse them rather than inventing one." The two seats now say it in the
    same sentence, which is the engine's own.
    """
    _need_node()
    if not (_BINDING / "build" / "kit" / "remote.js").is_file():
        pytest.skip("run npm ci in extensions/node to build its TypeScript")
    from metta import _json

    finished = subprocess.run(
        ["node", str(_BINDING / "build" / "kit" / "remote.js"), "refuses"],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert finished.returncode == 0, finished.stderr[-4000:]
    node = json.loads(finished.stdout)
    said = "JSON cannot carry the non-finite number"
    for name, value in [("inf", math.inf), ("-inf", -math.inf), ("nan", math.nan)]:
        with pytest.raises(ValueError) as refused:
            _json.dumps({"atom": ["n", value]})
        assert said in str(refused.value), str(refused.value)
        assert node[name].startswith(said), node[name]
    # The sentence is the engine's own and both seats refuse. The VALUE inside
    # it is spelled differently, and that is the engine's own inconsistency
    # rather than this seat's: metta_py_json_rethrow/1 names the culprit with
    # `~w`, which is SWI's `1.0Inf`, where the engine's own writer prints the
    # arbiter's `inf` for the same float. This seat writes what the engine
    # PRINTS. Pinned so the day the engine's message uses its own writer, this
    # says so rather than silently starting to agree.
    assert [node["inf"], node["-inf"], node["nan"]] == [
        f"{said} inf",
        f"{said} -inf",
        f"{said} NaN",
    ]


def test_the_node_binding_leaves_the_third_answer_uncomputed(node_report: dict) -> None:
    """Two answers pulled from an unbounded generator, and exactly two
    produced.

    The generator recurses through superpose and never ends, so a binding that
    computed the group before handing any of it over could not reach the
    assertion at all. The witness space holds one atom per answer the engine
    actually produced, which is what says the third was never computed rather
    than only that two were read.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    streaming = node_report["streaming"]
    assert streaming["pulled"] == ["1", "2"]
    assert streaming["produced"] == ["((produced 1) (produced 2))"]
