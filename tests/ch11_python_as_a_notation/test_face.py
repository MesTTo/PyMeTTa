"""Purpose: the face generator end to end, over a fixture module of every shape.

The fixture carries one of every shape the generator has a rule for: the head
spelling, the call forms a signature reaches, the types, the documentation, the
three `py-call` lowerings, the effect classes, the header that is read back as
the face's input, and the refusals a name the module cannot describe earns.

Assumes:
  - `tests.fixtures.face_source` is importable, which the suite's own root on
    `sys.path` arranges [source: extensions/python/pyproject.toml, pythonpath]
Guarantees:
  - the arities a face writes are the ones a `module_ops` registration
    ANSWERS, asked of a live engine rather than of the shared rule [tested:
    test_a_face_serves_the_call_forms_a_registration_answers; commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - every refusal names the header line that answers it [tested:
    test_a_required_keyword_only_parameter_refuses,
    test_a_name_with_no_signature_anywhere_is_refused,
    test_two_names_reaching_one_head_refuse; commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
  - the sync tool reports a planted signature change and skips a module that
    is not installed [tested: test_a_planted_signature_change_is_reported,
    test_a_face_whose_module_is_absent_is_reported_and_skipped; commit=7229962705d199fb08796b3090ec5a8a3a0ae393]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import re
from pathlib import Path

import pytest

import metta.integrate as pi
import tests.fixtures.face_source as source
from metta._face import Manifest, imports_from, read, render
from metta._name_mapping import attribute_name
from metta.atoms import parse
from metta.errors import EngineError, MettaError

_REPO = Path(__file__).resolve().parents[4]
_PURPOSE = "A module the face tests read"

#: What the fixture module says its version is, which is nothing at all.
_VERSION = str(getattr(source, "__version__", "unversioned"))


def _face(names, **rest) -> str:
    """The fixture module's face over the named callables."""
    return pi.face(source, names, purpose=_PURPOSE, prefix="fx", **rest)


def _equations(text: str, head: str) -> list[str]:
    """Every equation one head carries, in the order the face writes them."""
    return [line for line in text.splitlines() if line.startswith(f"(= ({head}")]


def _arrows(text: str, head: str) -> list[str]:
    """Every declaration one head carries."""
    return [line for line in text.splitlines() if line.startswith(f"(: {head} ")]


def _arities(text: str, head: str) -> set[int]:
    """The arities a head's equations serve, read off the face itself."""
    found = set()
    for line in _equations(text, head):
        call = line[len("(= ") :].partition(")")[0]
        found.add(len(call.split()) - 1)
    return found


def _load_facegen():
    """The sync tool, loaded from the path the gate runs it by."""
    specification = importlib.util.spec_from_file_location(
        "metta_facegen_tool",
        _REPO / "extensions" / "python" / "tools" / "facegen.py",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_a_declared_python_type_admits_one_value_and_refuses_another(metta):
    """Why a face writes `%Undefined%` where a module names its own types.

    One head, one declared result type, two calls: `sorted` under a declared
    `list` result answers a list of symbols and answers NOTHING for a list of
    numbers, because the check runs against the crossed VALUE and an
    expression of numbers carries an element-wise type that the word `list`
    does not fit. A signature says which Python type a function answers and
    cannot say which of its values survive the crossing under that name, so a
    face that wrote the name would refuse calls its own module makes.
    """
    metta.run(
        "(: sorted-listed (-[det,readOnlyLookup]-> %Undefined% list))"
        " (= (sorted-listed $xs) (py-call (sorted $xs)))"
    )
    metta.run(
        "(: sorted-undefined (-[det,readOnlyLookup]-> %Undefined% %Undefined%))"
        " (= (sorted-undefined $xs) (py-call (sorted $xs)))"
    )

    assert metta.run('!(sorted-listed ("b" "a"))') == [[parse("(a b)")]]
    assert metta.run("!(sorted-listed (3 1 2))") == [[]]
    assert metta.run("!(sorted-undefined (3 1 2))") == [[parse("(1 2 3)")]]


def test_a_tuple_crossing_py_call_unifies_with_nothing_until_it_is_listed(metta):
    """Why a face writes `list` around a call whose result is a tuple.

    A Python tuple crossing `py-call` PRINTS as an expression and compares
    equal to nothing, which is what left `torch-shape` answering `(3 2)` and
    failing a test against `(3 2)`. Through `builtins.list` it is an ordinary
    expression and the comparison holds.
    """
    assert metta.run("!(== (py-call (divmod 7 2)) (3 1))") == [[False]]
    assert metta.run("!(== (py-call (list (py-call (divmod 7 2)))) (3 1))") == [[True]]


def test_py_call_reaches_one_dot_and_py_atom_reaches_any(metta):
    """Why a face writes two spellings, one per depth of module path.

    `py-call`'s `mod.fun` spelling splits its spec on every dot and unifies
    the parts with a two-element list, so a module nested deeper than one
    component is not reachable through it at all.
    """
    assert metta.run('!((py-atom os.path.join) "a" "b")') == [["a/b"]]
    with pytest.raises(EngineError, match="No module named 'path'"):
        metta.run('!(py-call (path.join "a" "b"))')


def test_a_head_is_the_prefix_and_the_one_name_map():
    """A head is the import's prefix and the tree's Python-to-MeTTa map."""
    text = pi.face(
        source, ["area"], purpose=_PURPOSE, prefix="fx", rename={"area": "area_of_"}
    )

    assert attribute_name("area_of_") == "area-of"
    assert "(: fx-area-of " in text
    assert ";Import: from tests.fixtures.face_source import area as area_of_" in text


def test_a_face_serves_the_call_forms_a_registration_answers(metta):
    """The written face and `module_ops` answer at exactly the same arities."""
    pi.module_ops(metta, source, ["scale"], effect="pureStructural", prefix="reg-")
    answered = set()
    for arity in range(5):
        call = f"!(reg-scale {' '.join(['2.0'] * arity)})"
        try:
            # An arity the registration does not serve raises rather than
            # answering nothing: "function_input_arities(reg-scale,[1,2])
            # expected, found 3".
            reduced = metta.run(call)
        except EngineError:
            continue
        if reduced == [[4.0]]:
            answered.add(arity)

    assert answered == {1, 2}
    assert _arities(_face(["scale"]), "fx-scale") == answered


def test_a_parameter_the_module_annotates_takes_its_type():
    """An annotation reaches the arrow, and an unannotated parameter is undefined."""
    text = _face(["area", "anything"])

    assert _arrows(text, "fx-area") == [
        "(: fx-area (-[det,readOnlyLookup]-> Number Number Number))"
    ]
    assert _arrows(text, "fx-anything") == [
        "(: fx-anything (-[det,oracleIO]-> %Undefined% %Undefined%))"
    ]


def test_a_keyword_only_parameter_reaches_no_call_form():
    """A defaulted keyword-only parameter is invisible from a MeTTa call site."""
    text = _face(["label", "tally"])

    assert _arities(text, "fx-label") == {1}
    assert _arities(text, "fx-tally") == {0}


def test_a_defaulted_parameter_makes_its_arity_optional():
    """A default makes both call forms reachable, and both are written."""
    text = _face(["scale"])

    assert _equations(text, "fx-scale") == [
        "(= (fx-scale $value) ((py-atom tests.fixtures.face_source.scale) $value))",
        "(= (fx-scale $value $factor) "
        "((py-atom tests.fixtures.face_source.scale) $value $factor))",
    ]


def test_a_variadic_serves_zero_to_four_arguments():
    """`*args` serves the conventional arities, each parameter named for it."""
    text = _face(["total"])

    assert _arities(text, "fx-total") == {0, 1, 2, 3, 4}
    assert "$values1 $values2 $values3 $values4" in text


def test_a_required_keyword_only_parameter_refuses():
    """A parameter no positional call can supply refuses the face by name."""
    with pytest.raises(MettaError, match="unreachable from a positional"):
        _face(["stamped"])


def test_a_docstring_signature_answers_when_the_runtime_refuses():
    """A C-shaped callable's signature is read from its docstring's first line."""
    text = _face(["clipped"])

    assert _arities(text, "fx-clipped") == {2, 3}
    assert _arrows(text, "fx-clipped") == [
        "(: fx-clipped (-[det,readOnlyLookup]-> %Undefined% %Undefined% Number))",
        "(: fx-clipped (-[det,readOnlyLookup]-> %Undefined% %Undefined% %Undefined% Number))",
    ]


def test_a_name_with_no_signature_anywhere_is_refused():
    """A name neither rung answers is refused with the header line that does."""
    with pytest.raises(MettaError, match=r";Signature: opaque\(<parameters>\)"):
        _face(["opaque"])

    declared = _face(["opaque"], signatures=["opaque(value) -> int"])
    assert _arities(declared, "fx-opaque") == {1}


def test_a_face_documents_what_the_docstring_says():
    """The doc atom carries the prose, the parameters and the return."""
    text = _face(["area", "clipped"])

    assert [line for line in text.splitlines() if line.startswith("(@doc fx-area ")] == [
        '(@doc fx-area (@kind function) (@desc "The area of a rectangle.") '
        '(@params ((@param (@type Number) (@desc "how wide the rectangle is.")) '
        '(@param (@type Number) (@desc "how tall the rectangle is.")))) '
        '(@return (@type Number) (@desc "The product of the two.")))'
    ]
    # The docstring's own opening line is the SIGNATURE, never the prose.
    assert "clipped(value, low, high=10)" not in text.partition("(@doc fx-clipped")[2]


def test_each_lowering_matches_what_the_name_is():
    """A module function, a method and an attribute each take their own form."""
    dotted = _face(["area"])
    plain = pi.face("math", ["sqrt"], purpose=_PURPOSE)
    members = pi.face(
        "tests.fixtures.face_source.Box", ["get", "size"], purpose=_PURPOSE, prefix="box"
    )

    assert "((py-atom tests.fixtures.face_source.area) $width $height)" in dotted
    assert "(= (math-sqrt $x) (py-call (math.sqrt $x)))" in plain
    assert "(= (box-get $self) (py-call (.get $self)))" in members
    assert "(= (box-size $self) (py-call (getattr $self size)))" in members


def test_a_tuple_result_crosses_as_metta_data():
    """A tuple crossing py-call unifies with nothing, so a face lists it."""
    text = _face(["bounds", "names"])

    assert _equations(text, "fx-bounds") == [
        "(= (fx-bounds $low $high) (py-call (list "
        "((py-atom tests.fixtures.face_source.bounds) $low $high))))"
    ]
    assert _equations(text, "fx-names") == [
        "(= (fx-names) ((py-atom tests.fixtures.face_source.names)))"
    ]


def test_the_effect_class_follows_the_result_the_signature_declares():
    """Every class the derived rule reaches, one name each."""
    text = _face(["area", "names", "store", "anything", "bounds"])
    declared = {
        head: re.search(r"-\[det,(\w+)\]", _arrows(text, head)[0]).group(1)
        for head in ("fx-area", "fx-names", "fx-store", "fx-anything", "fx-bounds")
    }

    assert declared == {
        "fx-area": "readOnlyLookup",
        "fx-names": "readOnlyLookup",
        "fx-bounds": "readOnlyLookup",
        "fx-store": "writesState",
        "fx-anything": "oracleIO",
    }


def test_an_effect_review_declares_what_a_signature_cannot_show():
    """A review overrides the derived class; a stale or unexplained one refuses."""
    reviewed = _face(
        ["area"], effects=[("area", "oracleIO", "the area is measured, not computed")]
    )
    assert "(: fx-area (-[det,oracleIO]-> Number Number Number))" in reviewed

    with pytest.raises(MettaError, match="which is what the rule derives"):
        _face(["area"], effects=[("area", "readOnlyLookup", "already derived")])
    with pytest.raises(MettaError, match="gives no reason"):
        _face(["area"], effects=[("area", "oracleIO", "")])


def test_two_renders_of_one_face_are_the_same_text():
    """Rendering is deterministic, so a face is a file and not a snapshot."""
    assert _face(["area", "scale", "total"]) == _face(["area", "scale", "total"])


def test_a_faces_header_is_read_back_as_it_was_written():
    """The header is the face's input: reading a face answers its manifest."""
    text = _face(
        ["area", "opaque"],
        signatures=["opaque(value) -> int"],
        effects=[("area", "oracleIO", "the area is measured, not computed")],
    )
    manifest = read(text)

    assert manifest.purpose == _PURPOSE
    assert manifest.declared_signatures("opaque") == ("opaque(value) -> int",)
    assert manifest.declared_effect("area") == (
        "oracleIO",
        "the area is measured, not computed",
    )
    assert render(manifest) == text


def test_every_form_of_a_face_parses_as_the_atom_it_was_written_from():
    """A face is MeTTa source: every form reads back as the form written."""
    text = _face(["area", "clipped", "bounds"])
    forms = [line for line in text.splitlines() if line.startswith("(")]

    assert forms
    for form in forms:
        assert str(parse(form)) == form


def test_a_whole_module_is_taken_by_the_names_it_publishes():
    """`import x` takes the module's own roster, in one order on every box."""
    whole = pi.face("json", purpose="JSON through its own module")

    assert ";Import: import json" in whole
    assert "(= (json-dumps $obj)" in whole
    assert whole.index("(: json-dump ") < whole.index("(: json-dumps ")
    # The roster is module_ops's: a class is a type to declare, not an
    # operation, and a face that wants one names it in its import.
    assert "json-JSONEncoder" not in whole


def test_two_names_reaching_one_head_refuse():
    """One head cannot mean two names, and the remedy is Python's own `as`."""
    doubled = Manifest(
        purpose=_PURPOSE,
        imports=imports_from(
            "from tests.fixtures.face_source import area as one, names as one"
        ),
    )

    with pytest.raises(MettaError, match="both reach the MeTTa head"):
        render(doubled)


def test_a_signature_the_module_answers_refuses_a_declared_one():
    """A declaration for a name the module describes is stale and says so."""
    with pytest.raises(MettaError, match="the module answers for it"):
        _face(["area"], signatures=["area(width, height) -> float"])


def test_an_import_that_is_not_pythons_own_refuses():
    """The selection is a Python import statement, refused as Python refuses it."""
    with pytest.raises(MettaError, match="not a Python import statement"):
        imports_from("from torch import")
    with pytest.raises(MettaError, match="not a Python import statement"):
        imports_from("x = 1")
    with pytest.raises(MettaError, match="imports relatively"):
        imports_from("from . import area")


def test_a_face_is_only_a_file_whose_header_carries_an_import():
    """A hand-written library is not a face and the tool leaves it alone."""
    assert read("; Purpose: a hand-written library\n(= (f $x) $x)\n") is None


def test_the_arities_of_a_declared_overload_family_are_its_union():
    """Several declared signatures are one head's overloads, arities unioned."""
    text = _face(
        ["opaque"],
        signatures=["opaque(value) -> int", "opaque(value, other) -> int"],
    )

    assert _arities(text, "fx-opaque") == {1, 2}
    assert len(_arrows(text, "fx-opaque")) == 2


def test_the_torch_face_is_generated():
    """The checked-in face equals what torch's own signatures produce."""
    pytest.importorskip("torch")
    facegen = _load_facegen()

    assert facegen.main([]) == 0


def test_a_planted_signature_change_is_reported(tmp_path, monkeypatch):
    """A module whose signature moves is a finding naming the lines that moved."""
    facegen = _load_facegen()
    face = tmp_path / "lib_planted.metta"
    face.write_text(_face(["scale"]), encoding="utf-8")
    assert facegen.review([face], rewrite=False) == ([], [])

    def scale(value: float, factor: float, offset: float = 0.0) -> float:
        return value * factor + offset

    monkeypatch.setattr(source, "scale", scale)
    findings, notes = facegen.review([face], rewrite=False)

    assert notes == []
    assert len(findings) == 1
    assert "no longer matches the signatures its module publishes" in findings[0]
    assert "$value $factor $offset" in findings[0]

    facegen.review([face], rewrite=True)
    assert facegen.review([face], rewrite=False) == ([], [])


def test_a_face_whose_module_is_absent_is_reported_and_skipped(tmp_path):
    """A library this box has not got is named as unchecked, not as drift."""
    facegen = _load_facegen()
    face = tmp_path / "lib_absent.metta"
    face.write_text(
        ";Purpose: a face over a module nobody has\n"
        ";Import: from a_library_nobody_has import anything\n",
        encoding="utf-8",
    )

    findings, notes = facegen.review([face], rewrite=False)

    assert findings == []
    assert notes == [
        "lib_absent.metta: a_library_nobody_has is not installed here, so "
        "this face was not checked against it"
    ]


def test_a_version_bump_alone_is_a_note_rather_than_drift(tmp_path):
    """The header pins the version it was READ from, so a bump is not drift."""
    facegen = _load_facegen()
    face = tmp_path / "lib_pinned.metta"
    face.write_text(
        _face(["area"]).replace(
            f";Read from: tests.fixtures.face_source {_VERSION}",
            ";Read from: tests.fixtures.face_source 0.0.1",
        ),
        encoding="utf-8",
    )

    findings, notes = facegen.review([face], rewrite=False)

    assert findings == []
    assert notes == [
        "lib_pinned.metta: read from tests.fixtures.face_source 0.0.1, and "
        f"{_VERSION} is installed here; `--write` moves the pin"
    ]


def test_a_faces_manifest_survives_a_rewrite(tmp_path):
    """`--write` keeps every header field and re-pins only the version."""
    facegen = _load_facegen()
    face = tmp_path / "lib_kept.metta"
    face.write_text(
        _face(["area"], effects=[("area", "oracleIO", "measured, not computed")]),
        encoding="utf-8",
    )
    before = read(face.read_text(encoding="utf-8"))

    facegen.review([face], rewrite=True)

    after = read(face.read_text(encoding="utf-8"))
    assert dataclasses.replace(after, versions=()) == dataclasses.replace(
        before, versions=()
    )
    assert after.purpose == _PURPOSE
