"""Purpose: pin Python object identity and numeric dispatch at every engine door.

Guarantees:
  - exact bool, int, float and str values cross by value, while every other
    Python object crosses by reference through storage, operations and answers
    [tested: bindings/python/tests/test_identity_wire.py; commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
  - Python numeric objects are admitted once and evaluated by their own
    operator protocol, retaining NumPy scalar result classes
    [tested: bindings/python/tests/test_identity_wire.py; commit=a0f1cc5f15a15e5ca6958fe02a20be8832c7237f]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from collections.abc import Callable
from enum import IntEnum
from itertools import count
from typing import Any

import pytest

from metta import Expression, Grounded, S, V, ground

np = pytest.importorskip("numpy")


class Level(IntEnum):
    """An integer subclass whose member identity must survive the wire."""

    LOW = 7


class FloatChild(float):
    """A user numeric subclass with a result-preserving addition method."""

    def __add__(self, other: Any) -> FloatChild:
        """Return this subclass after Python's float addition."""
        return type(self)(super().__add__(other))


_NAMES = count()


def _operation_name(stem: str) -> str:
    return f"identity-wire-{stem}-{next(_NAMES)}"


_OBJECT_FACTORIES: tuple[tuple[str, Callable[[], object]], ...] = (
    ("numpy-float", lambda: np.float64(7.25)),
    ("numpy-string", lambda: np.str_("held")),
    ("int-enum", lambda: Level.LOW),
    ("float-subclass", lambda: FloatChild(4.5)),
)


@pytest.mark.parametrize(
    "_kind,factory", _OBJECT_FACTORIES, ids=[name for name, _ in _OBJECT_FACTORIES]
)
def test_store_and_match_preserve_python_object_identity(metta, _kind, factory):
    """Space storage returns the exact object supplied at construction."""
    value = factory()
    with metta._new_space() as stored:
        stored.add(S.holds(ground(value)))
        rows = stored.match(S.holds(V.x))
        assert len(rows) == 1
        assert rows[0].x.value is value


@pytest.mark.parametrize("transport", ["encoded", "raw"])
@pytest.mark.parametrize(
    "_kind,factory", _OBJECT_FACTORIES, ids=[name for name, _ in _OBJECT_FACTORIES]
)
def test_operation_arguments_preserve_python_object_identity(
    metta, _kind, factory, transport
):
    """Both operation argument transports deliver the exact object."""
    value = factory()
    seen: list[object] = []
    name = _operation_name(f"argument-{transport}")
    options = {} if transport == "encoded" else {"transport": "raw"}

    @metta.op(name=name, effect="writesState", **options)
    def receive(argument):
        seen.append(argument)
        return True

    try:
        assert metta.eval(Expression(S[name], ground(value))) == [
            Grounded(True)  # noqa: FBT003 -- this is returned atom data
        ]
        assert len(seen) == 1
        assert seen[0] is value
    finally:
        metta.unregister_op(name)


@pytest.mark.parametrize("transport", ["encoded", "raw"])
@pytest.mark.parametrize(
    "_kind,factory", _OBJECT_FACTORIES, ids=[name for name, _ in _OBJECT_FACTORIES]
)
def test_operation_results_preserve_python_object_identity(
    metta, _kind, factory, transport
):
    """Both operation result transports return the exact object."""
    value = factory()
    name = _operation_name(f"result-{transport}")
    options = {} if transport == "encoded" else {"transport": "raw"}

    @metta.op(name=name, effect="readOnlyLookup", **options)
    def return_value():
        return value

    try:
        answers = metta.eval(Expression(S[name]))
        assert len(answers) == 1
        assert answers[0].value is value
    finally:
        metta.unregister_op(name)


@pytest.mark.parametrize(
    "_kind,factory", _OBJECT_FACTORIES, ids=[name for name, _ in _OBJECT_FACTORIES]
)
def test_bridge_answers_preserve_python_object_identity(metta, _kind, factory):
    """A bridge result decodes to the exact object supplied to its call."""
    value = factory()
    with metta.bind(held=ground(value)):
        answers = metta.run('!((py-atom "lambda x: x") held)')[0]
    assert len(answers) == 1
    assert answers[0].value is value


def test_numpy_tutorial_arithmetic_has_one_typed_answer(metta):
    """The two tutorial additions each return one NumPy scalar."""
    float_answers = metta.run(
        "!(+ ((py-atom numpy.absolute) -5.5) 1)"
    )[0]
    assert len(float_answers) == 1
    assert type(float_answers[0].value) is np.float64
    assert float_answers[0].value == np.float64(6.5)

    integer_answers = metta.run(
        "!(+ ((py-atom numpy.absolute) -5) 10)"
    )[0]
    assert len(integer_answers) == 1
    assert type(integer_answers[0].value) is np.int64
    assert integer_answers[0].value == np.int64(15)


def test_user_numeric_subclass_uses_its_own_operator(metta):
    """Host dispatch invokes a user subclass's arithmetic method."""
    value = FloatChild(4.5)
    answers = metta.eval(Expression(S["+"], ground(value), Grounded(1)))
    assert len(answers) == 1
    assert type(answers[0].value) is FloatChild
    assert answers[0].value == FloatChild(5.5)


_NUMPY_NUMERIC_FAMILY = (
    ("+", (np.float64(4), 2), np.float64),
    ("-", (np.float64(4), 2), np.float64),
    ("*", (np.float64(4), 2), np.float64),
    ("/", (np.float64(4), 2), np.float64),
    ("%", (np.float64(5), 2), np.float64),
    ("<", (np.float64(1), 2), np.bool_),
    ("<=", (np.float64(2), 2), np.bool_),
    (">", (np.float64(3), 2), np.bool_),
    (">=", (np.float64(2), 2), np.bool_),
    ("min", (np.float64(2), 4), np.float64),
    ("max", (np.float64(4), 2), np.float64),
    ("pow-math", (np.float64(4), 2), np.float64),
    ("sqrt-math", (np.float64(4),), np.float64),
    ("abs-math", (np.float64(-4),), np.float64),
    ("log-math", (np.float64(2), np.float64(8)), np.float64),
    ("trunc-math", (np.float64(1.5),), np.float64),
    ("ceil-math", (np.float64(1.5),), np.float64),
    ("floor-math", (np.float64(1.5),), np.float64),
    ("round-math", (np.float64(1.5),), np.float64),
    ("sin-math", (np.float64(0.5),), np.float64),
    ("asin-math", (np.float64(0.5),), np.float64),
    ("cos-math", (np.float64(0.5),), np.float64),
    ("acos-math", (np.float64(0.5),), np.float64),
    ("tan-math", (np.float64(0.5),), np.float64),
    ("atan-math", (np.float64(0.5),), np.float64),
    ("exp", (np.float64(1),), np.float64),
    ("exp-math", (np.float64(1),), np.float64),
    ("isnan-math", (np.float64(np.nan),), np.bool_),
    ("isinf-math", (np.float64(np.inf),), np.bool_),
)


@pytest.mark.parametrize(
    "name,values,result_type",
    _NUMPY_NUMERIC_FAMILY,
    ids=[name for name, _, _ in _NUMPY_NUMERIC_FAMILY],
)
def test_numpy_numeric_family_keeps_python_result_types(
    metta, name, values, result_type
):
    """Every declared numeric builtin keeps NumPy's result class."""
    answers = metta.eval(Expression(S[name], *(ground(value) for value in values)))
    assert len(answers) == 1
    assert type(answers[0].value) is result_type


@pytest.mark.parametrize("name,selected", [("min-atom", 0), ("max-atom", 1)])
def test_numeric_expression_reductions_preserve_the_selected_object(
    metta, name, selected
):
    """List reductions return the selected input object by identity."""
    values = (np.float64(2), np.float64(4))
    answers = metta.eval(
        Expression(S[name], Expression(*(ground(value) for value in values)))
    )
    assert len(answers) == 1
    assert answers[0].value is values[selected]


def test_nonnumeric_objects_keep_refusal_multiplicity_and_wording(metta):
    """Host admission leaves the arbiter-pinned refusal rows unchanged."""
    class RefusalBase:
        pass

    class RefusalLeaf(RefusalBase):
        pass

    answers = metta.eval(Expression(S["+"], ground(RefusalLeaf()), Grounded(1)))
    assert [str(answer) for answer in answers] == [
        "(Error (+ <RefusalLeaf> 1) (BadArgType 1 Number RefusalLeaf))",
        "(Error (+ <RefusalLeaf> 1) (BadArgType 1 Number RefusalBase))",
    ]


def test_numeric_objects_are_number_arguments_even_when_a_sibling_refuses(metta):
    """A later invalid argument cannot make a host number look invalid."""
    answers = metta.eval(
        Expression(S["+"], ground(np.float64(1)), Grounded("bad"))
    )
    assert [str(answer) for answer in answers] == [
        '(Error (+ np.float64(1.0) "bad") (BadArgType 2 Number String))'
    ]


def test_python_numeric_dispatch_waits_for_every_operand(metta):
    """A free operand remains a MeTTa term rather than entering Janus."""
    answers = metta.run('!(+ ((py-atom numpy.float64) 1.0) $x)')[0]
    assert [str(answer) for answer in answers] == ["(+ np.float64(1.0) $x)"]
