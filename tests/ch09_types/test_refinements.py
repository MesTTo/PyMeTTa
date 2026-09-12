"""Purpose: one refinement vocabulary, from a Python annotation to the engine's refusal.

`Annotated[int, Gt(0)]` is the declaration; the engine decides it on the value
and names the constraint and the value when it refuses, at the call, at the
return crossing, and at the cast door.
Guarantees:
  - every annotated_types constraint class encodes to its atom, and the type
    projection carries exactly the vocabulary heads
    [tested: test_each_constraint_class_projects_to_its_atom,
    test_a_refined_signature_declares_the_refined_arrow,
    test_doc_and_timezone_stay_in_the_annotation_claim; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - a defined head refuses a violating argument with
    `(BadArgValue <position> <constraint> <value>)`, one per call, accepts the
    values the constraint admits, and keeps BadArgType for a base mismatch
    [tested: test_a_defined_head_refuses_a_violating_argument_by_name_and_accepts_the_rest;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - a return refinement refuses at the crossing with `(BadReturnValue
    <constraint> <value>)` [tested: test_a_return_refinement_refuses_at_the_crossing;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - MinLen reads a string and an expression, Predicate calls the grounded
    predicate at the seam or runs a defined head, Interval and MultipleOf
    decide numbers, Unit is a declaration
    [tested: test_min_len_reads_a_string_and_an_expression,
    test_a_predicate_refinement_calls_the_grounded_predicate_at_the_seam,
    test_interval_multiple_of_and_unit; commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - the engine and Python's own operators agree on every constraint over a
    value table [tested: test_the_engine_and_python_agree_on_each_constraint;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - cast honours a refinement and names the violated constraint
    [tested: test_cast_honours_a_refinement_and_names_the_violated_constraint;
    commit=19093dd75eda0102eb0329a71460e8a0c7a0c727]
  - length constraints ask a host value for its length without enumerating
    elements [tested: test_host_length_refinements_do_not_read_elements;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from collections.abc import Sequence
from typing import Annotated

import annotated_types as at
import pytest

from metta import Grounded, S, V
from metta._atoms.factories import Expression
from metta._catalog.refinements import holds
from metta._declare.operations import annotation_atom_for, type_atoms_for
from metta._errors.errors import EngineError
from metta.convert import CastError
from metta.vocabularies import Refinement


@pytest.mark.parametrize(
    ("constraint", "atom"),
    [
        (at.Gt(0), "(Gt 0)"),
        (at.Ge(0), "(Ge 0)"),
        (at.Lt(1), "(Lt 1)"),
        (at.Le(1), "(Le 1)"),
        (at.Interval(ge=0, le=1), "(Interval (ge 0) (le 1))"),
        (at.Interval(gt=0), "(Interval (gt 0))"),
        (at.MultipleOf(2), "(MultipleOf 2)"),
        (at.MinLen(2), "(MinLen 2)"),
        (at.MaxLen(3), "(MaxLen 3)"),
        (at.Len(2), "(Len 2)"),
        (at.Len(2, 5), "(Len 2 5)"),
        (at.Unit("m"), '(Unit "m")'),
        (at.Timezone(...), "(Timezone ...)"),
        (at.doc("positive"), '(doc "positive")'),
    ],
)
def test_each_constraint_class_projects_to_its_atom(constraint, atom):
    """Each constraint encodes to the atom whose head is its own name."""
    from metta._atoms.factories import _encode

    assert str(_encode(constraint)) == atom


def test_a_refined_signature_declares_the_refined_arrow():
    """The type projection carries the vocabulary heads and nothing else."""
    annotation = Annotated[int, at.Gt(0), at.doc("positive"), "a plain note"]
    assert [str(atom) for atom in type_atoms_for(annotation)] == ["(Annotated Number (Gt 0))"]
    assert str(annotation_atom_for(annotation)) == (
        '(Annotated Number (Gt 0) (doc "positive") "a plain note")'
    )
    assert [str(atom) for atom in type_atoms_for(Annotated[int | str, at.MinLen(2)])] == [
        "(Annotated Number (MinLen 2))",
        "(Annotated String (MinLen 2))",
    ]
    predicate = type_atoms_for(Annotated[int, at.Predicate(len)])[0]
    assert isinstance(predicate, Expression)
    assert str(predicate.children[2].head) == "Predicate"
    assert sorted(Refinement) == sorted(
        ["Gt", "Ge", "Lt", "Le", "Interval", "MultipleOf", "MinLen", "MaxLen", "Len", "Predicate", "Unit"]
    )


def test_doc_and_timezone_stay_in_the_annotation_claim():
    """Metadata outside the vocabulary never reaches the type."""
    annotation = Annotated[float, at.doc("seconds"), at.Timezone(None)]
    assert type_atoms_for(annotation) == [S.Number]
    claim = str(annotation_atom_for(annotation))
    assert claim.startswith('(Annotated Number (doc "seconds") (Timezone ')
    # An Atom stays a refinement, the rule arrays.Shape relies on.
    assert [str(atom) for atom in type_atoms_for(Annotated[int, S.Unit(V.unit)])] == [
        "(Annotated Number (Unit $unit))"
    ]


def _answers(head, *arguments) -> list[str]:
    return [str(answer) for answer in head(*arguments)]


def test_a_defined_head_refuses_a_violating_argument_by_name_and_accepts_the_rest(m):
    """One Error naming the constraint and the value; the base keeps BadArgType."""

    @m.define
    def positive_double(x: Annotated[int, at.Gt(0)]) -> int:
        return x * 2

    assert _answers(positive_double, 1) == ["2"]
    assert _answers(positive_double, 0) == [
        "(Error (positive-double 0) (BadArgValue 1 (Gt 0) 0))"
    ]
    assert _answers(positive_double, -3) == [
        "(Error (positive-double -3) (BadArgValue 1 (Gt 0) -3))"
    ]
    assert _answers(positive_double, "s") == [
        '(Error (positive-double "s") (BadArgType 1 (Annotated Number (Gt 0)) String))'
    ]
    # Two refined parameters: the first violated position is the one refusal.
    m.run("(: pair-bound (-> (Annotated Number (Gt 0)) (Annotated Number (Lt 10)) Number))")
    m.run("(= (pair-bound $a $b) (+ $a $b))")
    assert [str(a) for a in m.eval("(pair-bound 1 2)")] == ["3"]
    assert [str(a) for a in m.eval("(pair-bound 0 20)")] == [
        "(Error (pair-bound 0 20) (BadArgValue 1 (Gt 0) 0))"
    ]
    assert [str(a) for a in m.eval("(pair-bound 1 20)")] == [
        "(Error (pair-bound 1 20) (BadArgValue 2 (Lt 10) 20))"
    ]


def test_a_return_refinement_refuses_at_the_crossing(m):
    """A produced value outside the declared refinement is the named Error."""

    @m.define
    def decrement(x: int) -> Annotated[int, at.Ge(0)]:
        return x - 1

    assert _answers(decrement, 5) == ["4"]
    assert _answers(decrement, 0) == ["(Error (decrement 0) (BadReturnValue (Ge 0) -1))"]
    # A base mismatch on the result stays the silent branch failure it was.
    m.run("(: as-text (-> Number (Annotated String (MinLen 1))))")
    m.run("(= (as-text $x) $x)")
    assert m.eval("(as-text 4)") == []


def test_min_len_reads_a_string_and_an_expression(m):
    """A length refinement reads a string's length and an expression's children."""

    @m.define
    def initial(s: Annotated[str, at.MinLen(1)]) -> str:
        return s[0]

    assert _answers(initial, "ab") == ['"a"']
    assert _answers(initial, "") == ['(Error (initial "") (BadArgValue 1 (MinLen 1) ""))']
    m.run("(: pair-size (-> (Annotated Expression (MinLen 2)) Number))")
    m.run("(= (pair-size $e) (size-atom $e))")
    assert [str(a) for a in m.eval("(pair-size (a b c))")] == ["3"]
    assert [str(a) for a in m.eval("(pair-size (a))")] == [
        "(Error (pair-size (a)) (BadArgValue 1 (MinLen 2) (a)))"
    ]
    # An untyped symbol has no length, so the constraint decides against it
    # rather than the gradual wildcard waving it through.
    assert [str(a) for a in m.eval("(pair-size abc)")] == [
        "(Error (pair-size abc) (BadArgValue 1 (MinLen 2) abc))"
    ]


@pytest.mark.parametrize("base", [object, Sequence])
@pytest.mark.parametrize("size", [0, 1, 1_000_000])
def test_host_length_refinements_do_not_read_elements(m, base, size):  # noqa: D103 -- pytest discovers this test; its name states the contract
    class Counted(base):
        def __len__(self):
            return size

        def __getitem__(self, index):
            msg = "a length refinement must not read an element"
            raise AssertionError(msg)

        def __iter__(self):
            msg = "a length refinement must not iterate"
            raise AssertionError(msg)

    m.run(
        f"(: sized-host (-> (Annotated %Undefined% (Len {size})) Number))"
        "(= (sized-host $value) 7)"
    )
    assert m.eval(S["sized-host"](Grounded(Counted()))) == [7]
    refused = m.eval(S["sized-host"](Grounded(object())))
    assert len(refused) == 1 and refused[0].head == S.Error
    assert "BadArgValue" in str(refused[0])


def test_a_host_length_failure_preserves_its_exception(m):  # noqa: D103 -- pytest discovers this test; its name states the contract
    class BrokenLength:
        def __len__(self):
            msg = "length query failed"
            raise RuntimeError(msg)

        def __iter__(self):
            msg = "a failed length must not fall back to iteration"
            raise AssertionError(msg)

    m.run(
        "(: sized-host (-> (Annotated %Undefined% (MinLen 1)) Number))"
        "(= (sized-host $value) 7)"
    )
    with pytest.raises(EngineError, match=r"(?s)RuntimeError.*length query failed"):
        m.eval(S["sized-host"](Grounded(BrokenLength())))


def test_a_predicate_refinement_calls_the_grounded_predicate_at_the_seam(m):
    """A Python predicate runs through the seam; a defined head runs its equations."""
    seen = []

    def is_even(value):
        seen.append(value)
        return value % 2 == 0

    @m.define
    def half(x: Annotated[int, at.Predicate(is_even)]) -> int:
        return x // 2

    # An accepted call applies the predicate exactly once, on the way in.
    assert _answers(half, 4) == ["2"]
    assert seen == [4]
    refused = _answers(half, 3)
    assert len(refused) == 1
    assert refused[0].startswith("(Error (half 3) (BadArgValue 1 (Predicate ")
    assert refused[0].endswith(") 3))")
    # A refused call applies it again while its reason is built, the refusal
    # path's own re-walk; the predicate saw 3 and nothing else new.
    assert set(seen) == {4, 3}

    @m.define
    def small(x: int) -> bool:
        return x < 10

    @m.define
    def tiny_double(x: Annotated[int, at.Predicate(small)]) -> int:
        return x * 2

    assert _answers(tiny_double, 4) == ["8"]
    assert _answers(tiny_double, 40) == [
        "(Error (tiny-double 40) (BadArgValue 1 (Predicate small) 40))"
    ]


def test_interval_multiple_of_and_unit(m):
    """Interval decides its written bounds, MultipleOf the remainder, Unit nothing."""
    m.run(
        "(: unit-interval (-> (Annotated Number (Interval (ge 0) (le 1))) Number))"
        "(= (unit-interval $x) $x)"
        "(: even-only (-> (Annotated Number (MultipleOf 2)) Number))"
        "(= (even-only $x) $x)"
        '(: metres (-> (Annotated Number (Unit "m")) Number))'
        "(= (metres $x) $x)"
    )
    assert [str(a) for a in m.eval("(unit-interval 1)")] == ["1"]
    assert [str(a) for a in m.eval("(unit-interval 0.5)")] == ["0.5"]
    assert [str(a) for a in m.eval("(unit-interval 2)")] == [
        "(Error (unit-interval 2) (BadArgValue 1 (Interval (ge 0) (le 1)) 2))"
    ]
    assert [str(a) for a in m.eval("(even-only 4)")] == ["4"]
    assert [str(a) for a in m.eval("(even-only 3)")] == [
        "(Error (even-only 3) (BadArgValue 1 (MultipleOf 2) 3))"
    ]
    assert [str(a) for a in m.eval("(metres 3)")] == ["3"]


@pytest.mark.parametrize(
    ("constraint", "admitted", "refused"),
    [
        (at.Gt(0), (1, 0.5), (0, -1)),
        (at.Ge(0), (0, 7), (-1,)),
        (at.Lt(1), (0, -5), (1, 2)),
        (at.Le(1), (1, 0), (2,)),
        (at.Interval(gt=0, lt=10), (1, 9), (0, 10)),
        (at.MultipleOf(3), (0, 9, -6), (1, 10)),
    ],
)
def test_the_engine_and_python_agree_on_each_constraint(m, constraint, admitted, refused):
    """The engine's rule and the constraint's Python reading decide alike."""
    target = Annotated[int, constraint]
    for value in admitted:
        assert m.cast(value, target) == value
    for value in refused:
        with pytest.raises(CastError, match="violates"):
            m.cast(value, target)


@pytest.mark.parametrize(
    ("constraint", "verdicts"),
    [
        (at.Gt(0), {1: True, 0: False, "s": False}),
        (at.Ge(0), {0: True, -1: False}),
        (at.Lt(1), {0: True, 1: False}),
        (at.Le(1), {1: True, 2: False}),
        (at.MultipleOf(2), {4: True, 3: False, "ab": False}),
        (at.MinLen(2), {"ab": True, "a": False, (1, 2): True, 7: False}),
        (at.MaxLen(2), {"ab": True, "abc": False}),
        (at.Predicate(str.islower), {"ab": True, "Ab": False}),
        (at.Unit("m"), {5: None}),
        (at.Timezone(None), {5: None}),
    ],
)
def test_holds_decides_each_constraint_the_way_the_engine_does(constraint, verdicts):
    """Python's reading of a constraint: True, False, or None for a value it says nothing about."""
    for value, verdict in verdicts.items():
        assert holds(constraint, value) is verdict, (constraint, value)
    grouped = at.Interval(ge=0, le=1)
    assert [holds(part, 2) for part in grouped] == [True, False]


def test_cast_honours_a_refinement_and_names_the_violated_constraint(m):
    """The typed acceptance door reads the same vocabulary as a call."""
    assert m.cast(1, Annotated[int, at.Gt(0)]) == 1
    assert m.cast("ab", Annotated[str, at.MinLen(2)]) == "ab"
    with pytest.raises(CastError, match=r"0 violates \(Gt 0\), the refinement \(Annotated Number \(Gt 0\)\) declares"):
        m.cast(0, Annotated[int, at.Gt(0)])
    with pytest.raises(CastError, match="does not admit type"):
        m.cast("s", Annotated[int, at.Gt(0)])
    # The MeTTa spelling is the same declaration.
    assert m.cast(5, "(Annotated Number (Gt 0))") == 5
    with pytest.raises(CastError, match="violates"):
        m.cast(5, "(Annotated Number (Lt 0))")


@pytest.fixture
def m(metta):
    """One fresh anonymous space per test."""
    return metta._new_space()
