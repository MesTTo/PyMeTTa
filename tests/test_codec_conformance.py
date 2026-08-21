"""Purpose: run the shared golden corpus against both shipped codecs, and
prove the kit still discriminates.

The two codecs are not two names for one implementation. The janus tagged
form encodes and decodes in Prolog (petta_py_encode_named/3,
petta_py_decode_shared/3) and carries its terms through janus's own term
conversion. The remote JSON wire encodes and decodes in Python
(Atom.to_wire, atom_from_wire) and carries them as JSON bytes through the
engine's library(json), which is what petta.remote puts on a socket. So a
disagreement between them is a real disagreement between two
implementations in two languages, which is what the corpus is for.

Guarantees:
  - a renderer refusal is licensed only where the corpus marks the spelling
    as non-invertible [tested:
    test_a_renderer_may_refuse_only_a_non_round_trip_text; commit=53686aed41e7ff02de69052198afdb537536cbdb]
  - undefined truth has one value-and-delay frame without a residual-program
    variant [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=affc981bd744563f65f595259b8a3564b9d84ba9]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import sys

import pytest

from petta import _json, testing
from petta.atoms import atom_from_wire, parse
from petta.testing import check_codec, codec_corpus, codec_plan

CORE = frozenset({"s", "v", "n", "g", "e"})
FULL = CORE | {"b", "o", "h"}


class JanusCodec:
    """The in-process tagged form: Prolog encodes and decodes, janus carries.

    frames is {"a"} rather than every frame because the frames are
    directional. The engine WRITES the u frame and the host reads it, so
    there is no Prolog reader for one; the engine READS the a frame, which
    petta_py_answer_form/5 is.
    """

    name = "janus"
    tags = FULL
    frames = frozenset({"a"})
    printer = "engine"
    reads_text = True
    exact_integers = True
    non_finite = True
    resolves_anonymous = True
    runs_programs = True

    def __init__(self, metta):  # noqa: D107  -- the test double construction contract is local to its containing scenario
        self._metta = metta
        self._rt = metta.runtime

    def read(self, text):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return self._rt.must(
            "sread_with_names(T, _X, _M), petta_py_encode_named(_X, _M, W)", T=text
        )["W"]

    def roundtrip(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return self._rt.must(
            "petta_py_decode_shared(W, _T, _B), petta_py_encode_named(_T, _B, W2)", W=wire
        )["W2"]

    def render(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return self._rt.must("petta_py_decode_shared(W, _T, _B), swrite(_T, S)", W=wire)["S"]

    def transport(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        # janus's own term conversion, in and out, which is this codec's
        # concrete encoding exactly as the JSON bytes are the other one's.
        return self._rt.must("W2 = W", W=wire)["W2"]

    def frame(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        row = self._rt.must(
            "petta_py_answer_form(W, Theta, _R0, K, _V0), "
            "( _R0 == '@'(true) -> Residue = '@'(none) ; Residue = _R0 ), "
            "( _V0 = value(_V1) -> Value = _V1 ; Value = '@'(none) )",
            W=wire,
        )
        return {
            "theta": row["Theta"],
            "residue": row["Residue"],
            "k": row["K"],
            "value": row["Value"],
        }

    def host_value(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return object()

    def transcript(self, program):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        # A fresh space per program, so a transcript that defines an
        # equation does not leave it where the next run of the corpus, or
        # the other codec's run of the same program, would see it twice.
        with self._metta.new_space() as scratch:
            return self._rt.must(
                "petta_py_run(S, Sp, G)", S=program, Sp=scratch.space_name
            )["G"]


class JsonWireCodec:
    """The remote wire: Python encodes and decodes, JSON bytes carry.

    Its profile is the core five. b, o and h are outside it for three
    different reasons and all three are visible in the plan: a JSON number
    cannot be a host reference or a native handle at all, and the boolean
    tag is one the reference server refuses, so a term carrying it is not
    portable over this wire.
    """

    name = "json"
    tags = CORE
    frames = frozenset({"u"})
    printer = "python"
    reads_text = True
    exact_integers = True
    non_finite = False
    resolves_anonymous = False
    runs_programs = True

    def __init__(self, metta):  # noqa: D107  -- the test double construction contract is local to its containing scenario
        self._metta = metta

    def read(self, text):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return parse(text).to_wire()

    def roundtrip(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return atom_from_wire(wire).to_wire()

    def render(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return str(atom_from_wire(wire))

    def transport(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return _json.loads(_json.dumps(wire))

    def frame(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        # The u frame is not an atom, so it is read below atom_from_wire.
        from petta._atom_wire import from_wire

        undefined = from_wire(wire)
        return {
            "value": undefined.value.to_wire(),
            "why": undefined.why,
        }

    def host_value(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        msg = "the JSON wire declares no o tag, so no case asks for one"
        raise AssertionError(msg)

    def transcript(self, program):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        with self._metta.new_space() as scratch:
            return [[atom.to_wire() for atom in group] for group in scratch.run(program)]


@pytest.fixture(scope="module")
def codecs(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    return [JanusCodec(metta), JsonWireCodec(metta)]


def test_both_shipped_codecs_pass_the_shared_golden_corpus(codecs):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    complaints = {codec.name: check_codec(codec) for codec in codecs}
    assert complaints == {"janus": [], "json": []}


def test_every_corpus_case_runs_for_at_least_one_shipped_codec(codecs):
    """A case no codec runs is not coverage, it is decoration."""
    corpus = codec_corpus()
    covered = {name for codec in codecs for name in codec_plan(codec, corpus=corpus)["run"]}
    written = {
        case["id"]
        for section in ("cases", "refusals", "frames", "transcripts")
        for case in corpus[section]
    }
    assert written - covered == set()


def test_the_plan_names_what_each_codec_leaves_out(codecs):
    """The JSON wire's exclusions are declared, not discovered at run time."""
    janus, wire = codecs
    assert codec_plan(janus)["out_of_profile"] == [("undefined-truth", "frame u")]
    left_out = dict(codec_plan(wire)["out_of_profile"])
    assert left_out == {
        "boolean-true": "tags ['b']",
        "boolean-false": "tags ['b']",
        "boolean-lowercase-source": "tags ['b']",
        "expression-every-tag": "tags ['b']",
        "host-reference": "tags ['o']",
        "float-infinity": "needs non_finite",
        "float-negative-infinity": "needs non_finite",
        "float-nan": "needs non_finite",
        "answer-bindings": "frame a",
        "answer-empty-theta": "frame a",
        "answer-with-value": "frame a",
        "answer-with-residue": "frame a",
    }


def test_the_packaging_map_carries_the_corpus(repo_root):
    """The corpus is data a third party reads out of an installed tree, so
    the packaging map has to carry it; a checkout alone would leave anyone
    certifying their own codec cloning the repository.

    This reads the map. The ARTEFACT is checked where it exists, by the
    wheel job in .github/workflows/checks.yml, which installs the built
    wheel into a fresh venv outside the checkout and loads the corpus from
    it. Read from setup.py's AST rather than imported, because importing it
    runs setup() against pytest's own argv.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    import ast

    tree = ast.parse((repo_root / "setup.py").read_text(encoding="utf-8"))
    mapping = next(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", None) == "RUNTIME_RESOURCES" for t in node.targets)
    )
    shipped = {ast.literal_eval(k): ast.literal_eval(v) for k, v in zip(mapping.keys, mapping.values, strict=True)}
    assert shipped["tests/codec"] == "tests/codec"
    assert (repo_root / "tests" / "codec" / "corpus.json").is_file()


# ------------------------------------------------------- the kit discriminates


class _Broken(JsonWireCodec):
    """A codec that refuses everything, the way a driver with a typo does."""

    name = "broken"

    def read(self, text):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        msg = "no"
        raise RuntimeError(msg)

    def roundtrip(self, wire):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        msg = "no"
        raise RuntimeError(msg)

    def render(self, wire):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        msg = "no"
        raise RuntimeError(msg)

    def transport(self, wire):  # noqa: ARG002  -- the test double preserves the protocol method signature its caller exercises
        msg = "no"
        raise RuntimeError(msg)


def test_a_driver_that_refuses_everything_is_caught(metta):
    """Refusing correctly and refusing everything are the same thing to a
    kit that only checks refusals, which is how one passes vacuously.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    broken = _Broken(metta)
    complaints = check_codec(broken)
    plan = codec_plan(broken)
    corpus = codec_corpus()
    runnable = {case["id"] for case in corpus["cases"]} & set(plan["run"])
    assert {case_id for case_id in runnable if any(case_id in c for c in complaints)} == runnable


def test_a_renderer_may_refuse_only_a_non_round_trip_text(metta):
    """A strict serializer may reject an unrepresentable term, but that
    license must not turn a general renderer failure into conformance.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    class _Strict(JsonWireCodec):
        name = "strict"
        non_finite = True

        def render(self, wire):
            if wire == ["s", "foo"]:
                msg = "readable symbol refused"
                raise RuntimeError(msg)
            if wire == ["n", float("inf")]:
                msg = "non-invertible float refused"
                raise RuntimeError(msg)
            return super().render(wire)

    complaints = check_codec(_Strict(metta))
    assert not [c for c in complaints if "strict/float-infinity: render refused" in c]
    assert [c for c in complaints if "strict/symbol: render refused" in c]


def test_a_driver_declaring_less_than_the_core_profile_is_refused(metta):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    class _Narrow(JsonWireCodec):
        name = "narrow"
        tags = frozenset({"s"})

    with pytest.raises(ValueError, match="short of the core profile"):
        check_codec(_Narrow(metta))


def test_alpha_comparison_refuses_a_collapsed_variable():
    """The renaming is a bijection, so it accepts the two shipped naming
    schemes and still separates (f $x $x) from (f $x $y).
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    from petta._codec_kit import alpha_equal

    repeated = ["e", [["s", "f"], ["v", "x"], ["v", "x"]]]
    distinct = ["e", [["s", "f"], ["v", "x"], ["v", "y"]]]
    machine = ["e", [["s", "f"], ["v", "_1234"], ["v", "_1234"]]]
    assert alpha_equal(repeated, machine)
    assert not alpha_equal(repeated, distinct)
    assert not alpha_equal(distinct, machine)
    # A renaming touches v payloads and nothing else.
    assert not alpha_equal(["s", "x"], ["s", "y"])
    assert not alpha_equal(["v", "x"], ["s", "x"])
    # An integer and a float are different atoms, so they are different wires.
    assert not alpha_equal(["n", 1], ["n", 1.0])
    assert not alpha_equal(["n", 1], ["b", "true"])


def test_a_wrong_expected_value_is_caught(metta):
    """The corpus is only evidence if a wrong entry in it fails."""
    corpus = codec_corpus()
    for case in corpus["cases"]:
        if case["id"] == "symbol":
            case["wire"] = ["s", "not-foo"]
    complaints = check_codec(JsonWireCodec(metta), corpus=corpus)
    assert [c for c in complaints if "json/symbol" in c]


def test_the_corpus_is_json_a_binding_in_any_language_can_read(repo_root):
    """No comments, no trailing commas, one object: the file a Julia or Rust
    binding parses with its own standard library.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    raw = (repo_root / "tests" / "codec" / "corpus.json").read_text(encoding="utf-8")
    corpus = json.loads(raw)
    assert set(corpus) >= {"version", "grammar", "profiles", "cases", "refusals"}
    assert (repo_root / corpus["grammar"]).is_file()
    identifiers = [
        case["id"]
        for section in ("cases", "refusals", "frames", "transcripts")
        for case in corpus[section]
    ]
    assert len(identifiers) == len(set(identifiers)), "case ids are the corpus's own keys"


def test_the_kit_is_reachable_from_the_documented_name():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert testing.check_codec is check_codec
    assert isinstance(codec_corpus(), dict)
    assert "check_codec" in testing.__all__


def test_the_tag_inventory_covers_what_the_cases_and_the_codecs_use(codecs):
    """The tag table is data, so it is held to the cases rather than trusted."""
    corpus = codec_corpus()
    inventory = set(corpus["tags"])
    used = {tag for case in corpus["cases"] for tag in case.get("tags", ())}
    used |= {case["frame"] for case in corpus["frames"]}
    assert used <= inventory
    for codec in codecs:
        assert codec.tags <= inventory and codec.frames <= inventory
    terms = {tag for tag, entry in corpus["tags"].items() if entry["class"] == "term"}
    assert terms == set(corpus["profiles"]["full"]["tags"])


# ------------------------------------------------------ the document is generated


def test_the_grammar_document_is_generated(repo_root):
    """CODEC.md's tables and the corpus are one authority, so the checked-in
    document has to equal what the corpus produces.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    sys.path.insert(0, str(repo_root / "bindings" / "python" / "tools"))
    try:
        import codecdoc
    finally:
        sys.path.pop(0)
    assert codecdoc.main([]) == 0


def test_an_unknown_fence_is_refused(repo_root):
    """A table that grows a fence nobody builds, or loses the fence it had,
    would show as an empty section rather than as a failure.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    sys.path.insert(0, str(repo_root / "bindings" / "python" / "tools"))
    try:
        import codecdoc
    finally:
        sys.path.pop(0)
    corpus = codec_corpus()
    with pytest.raises(SystemExit, match="does not build"):
        codecdoc.document(
            "<!-- generated: nonsense -->\n<!-- end generated -->\n", corpus
        )
    with pytest.raises(SystemExit, match="no fence"):
        codecdoc.document("nothing generated here\n", corpus)
