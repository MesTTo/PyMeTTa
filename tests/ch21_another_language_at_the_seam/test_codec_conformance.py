"""Purpose: run the shared golden corpus against both shipped codecs, and
prove the kit still discriminates.

The two codecs are not two names for one implementation. The janus tagged
form encodes and decodes in Prolog (metta_py_encode_named/3,
metta_py_decode_shared/3) and carries its terms through janus's own term
conversion. The remote JSON wire encodes and decodes in Python
(Atom.to_wire, atom_from_wire) and carries them as JSON bytes through the
engine's library(json), which is what metta.remote puts on a socket. So a
disagreement between them is a real disagreement between two
implementations in two languages, which is what the corpus is for.

Guarantees:
  - a renderer refusal is licensed only where the corpus marks the spelling
    as non-invertible [tested:
    test_a_renderer_may_refuse_only_a_non_round_trip_text; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - undefined truth has one value-and-delay frame without a residual-program
    variant [tested:
    test_a_not_reducible_answer_is_the_unreduced_term_with_no_flag;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - both Python codecs preserve a p-tagged executable space reference
    [tested: test_both_shipped_codecs_pass_the_shared_golden_corpus;
    commit=4e2398075da67bb2cbcc123a9fc1e078ecac6fbf]
  - every codec tag has a corpus case or a corpus-owned reason, and the
    irregular h case round-trips a live native value by resolved identity
    [tested: test_the_tag_inventory_covers_what_the_cases_and_the_codecs_use,
    test_an_unexercised_tag_requires_a_stated_corpus_exemption,
    test_both_shipped_codecs_pass_the_shared_golden_corpus; commit=WORKTREE]

Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from typing import Any

import pytest

from metta import _json, parse, testing, wire
from metta.testing import check_codec, codec_corpus, codec_plan

CORE = frozenset({"s", "v", "n", "g", "e"})
FULL = CORE | {"b", "o", "h", "p"}


class JanusCodec:
    """The in-process tagged form: Prolog encodes and decodes, janus carries.

    frames is {"a"} rather than every frame because the frames are
    directional. The engine WRITES the u frame and the host reads it, so
    there is no Prolog reader for one; the engine READS the a frame, which
    metta_py_answer_form/5 is.
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
        self._native_fixture_ids: set[int] | None = None
        self._native_host_atoms: list[Any] | None = None

    def read(self, text):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return self._rt.must(
            "sread_with_names(T, _X, _M), metta_py_encode_named(_X, _M, W)", T=text
        )["W"]

    def roundtrip(self, payload):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        if payload[:1] == ["h"]:
            host_atom = wire.atom_from_wire(payload)
            host_back = host_atom.to_wire()
            if host_back != payload:
                msg = f"the Python host changed native handle {payload!r} into {host_back!r}"
                raise ValueError(msg)
            assert self._native_host_atoms is not None
            self._native_host_atoms.append(host_atom)
        back = self._rt.must(
            "metta_py_decode_shared(W, _T, _B), metta_py_encode_named(_T, _B, W2)",
            W=payload,
        )["W2"]
        if self._native_fixture_ids is not None and back[:1] == ["h"]:
            self._native_fixture_ids.add(back[1])
        return back

    def render(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return self._rt.must("metta_py_decode_shared(W, _T, _B), swrite(_T, S)", W=wire)["S"]

    def transport(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        # janus's own term conversion, in and out, which is this codec's
        # concrete encoding exactly as the JSON bytes are the other one's.
        return self._rt.must("W2 = W", W=wire)["W2"]

    def frame(self, wire):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        row = self._rt.must(
            "metta_py_answer_form(W, Theta, _R0, K, _V0), "
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

    @contextmanager
    def native_handle(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        wire = self._rt.must(
            "current_output(_Handle), metta_py_encode_named(_Handle, [], W)"
        )["W"]
        issued = {wire[1]}
        self._native_fixture_ids = issued
        host_atoms: list[Any] = []
        self._native_host_atoms = host_atoms
        try:
            yield wire
        finally:
            for atom in host_atoms:
                atom.release()
            for ident in issued:
                self._rt.do("metta_py_handle_release", ident)
            self._native_fixture_ids = None
            self._native_host_atoms = None

    def same_native_handle(self, left, right):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        row = self._rt.must(
            "metta_py_decode_shared(A, _X, _), "
            "metta_py_decode_shared(B, _Y, _), "
            "(_X == _Y -> Same = true ; Same = false)",
            A=left,
            B=right,
        )
        return row["Same"] == "true"

    def transcript(self, program):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        # A fresh space per program, so a transcript that defines an
        # equation does not leave it where the next run of the corpus, or
        # the other codec's run of the same program, would see it twice.
        with self._metta._new_space() as scratch:
            return self._rt.must(
                "metta_py_run(S, Sp, G)", S=program, Sp=scratch.name
            )["G"]


class JsonWireCodec:
    """The remote wire: Python encodes and decodes, JSON bytes carry.

    It carries the core five plus portable space references. b, o and h are
    outside it for three different reasons and all three are visible in the
    plan: JSON cannot be a host reference or a native handle at all, and the
    boolean tag is one the reference server refuses, so a term carrying it
    is not portable over this wire.
    """

    name = "json"
    tags = CORE | {"p"}
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

    def roundtrip(self, payload):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return wire.atom_from_wire(payload).to_wire()

    def render(self, payload):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return str(wire.atom_from_wire(payload))

    def transport(self, payload):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        return _json.loads(_json.dumps(payload))

    def frame(self, payload):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        # The u frame is not an atom, so it is read below atom_from_wire.
        undefined = wire.from_wire(payload)
        return {
            "value": undefined.value.to_wire(),
            "why": undefined.why,
        }

    def host_value(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        msg = "the JSON wire declares no o tag, so no case asks for one"
        raise AssertionError(msg)

    def native_handle(self):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        msg = "the JSON wire declares no h tag, so no case asks for one"
        raise AssertionError(msg)

    def same_native_handle(self, left, right):  # noqa: ARG002,D102  -- outside this driver's declared profile
        msg = "the JSON wire declares no h tag, so no case asks for one"
        raise AssertionError(msg)

    def transcript(self, program):  # noqa: D102  -- the test double method is documented by its containing scenario and protocol
        with self._metta._new_space() as scratch:
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
        "native-handle": "tags ['h']",
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
    from metta._codec_kit import alpha_equal

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


def _tag_inventory_findings(corpus):
    """Return every unexercised, unexplained, or stale tag declaration."""
    inventory = set(corpus["tags"])
    used = {tag for case in corpus["cases"] for tag in case.get("tags", ())}
    used |= {case["frame"] for case in corpus["frames"]}
    exemptions = corpus.get("coverage_exemptions", {})
    findings = [
        f"exercised tag {tag!r} is absent from the inventory"
        for tag in sorted(used - inventory)
    ]
    findings.extend(
        f"inventory tag {tag!r} has no case or stated exemption"
        for tag in sorted(inventory - used - set(exemptions))
    )
    findings.extend(
        f"exemption tag {tag!r} is absent from the inventory"
        for tag in sorted(set(exemptions) - inventory)
    )
    findings.extend(
        f"exemption tag {tag!r} is stale because a case exercises it"
        for tag in sorted(set(exemptions) & used)
    )
    for tag, reason in exemptions.items():
        if not isinstance(reason, str) or not reason.strip():
            findings.append(f"exemption tag {tag!r} gives no reason")
    return findings


def test_the_tag_inventory_covers_what_the_cases_and_the_codecs_use(codecs):
    """The tag table is data, so both coverage directions are enforced."""
    corpus = codec_corpus()
    assert _tag_inventory_findings(corpus) == []
    for codec in codecs:
        assert codec.tags <= set(corpus["tags"])
        assert codec.frames <= set(corpus["tags"])
    terms = {tag for tag, entry in corpus["tags"].items() if entry["class"] == "term"}
    assert terms == set(corpus["profiles"]["full"]["tags"])


def test_an_unexercised_tag_requires_a_stated_corpus_exemption():
    """A future inventory addition cannot repeat h's silent omission."""
    corpus = codec_corpus()
    corpus["tags"]["q"] = {
        "class": "frame",
        "payload": "test-only",
        "means": "a planted tag with no case",
    }
    assert _tag_inventory_findings(corpus) == [
        "inventory tag 'q' has no case or stated exemption"
    ]

    corpus["coverage_exemptions"]["q"] = "A planted directional tag for this control."
    assert _tag_inventory_findings(corpus) == []


# ------------------------------------------------------ the document is generated


def test_the_grammar_document_is_generated(repo_root):
    """CODEC.md's tables and the corpus are one authority, so the checked-in
    document has to equal what the corpus produces.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    sys.path.insert(0, str(repo_root / "extensions" / "python" / "tools"))
    try:
        import codecdoc
    finally:
        sys.path.pop(0)
    assert codecdoc.main([]) == 0


def test_an_unknown_fence_is_refused(repo_root):
    """A table that grows a fence nobody builds, or loses the fence it had,
    would show as an empty section rather than as a failure.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    sys.path.insert(0, str(repo_root / "extensions" / "python" / "tools"))
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
