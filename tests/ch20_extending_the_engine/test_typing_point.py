"""Purpose: a shape rule is a row, and a STRANGER's rule reaches the same point.

The array layer's twenty-one rule kinds used to be a Python dict of head to
word with three functions assembling the equations, so a domain that is not
arrays could not add a rule at all: a dataframe's rows by columns is the same
shape algebra and had nowhere to say so. This file is the proof that it does
now. `column-select` is a fixture library's own rule -- the result of selecting
n columns has n columns -- registered from outside the package, declared on a
head with an argument, evaluated by the engine, and withdrawn.

Guarantees:
  - a rule kind registered from outside the package reaches the point, its
    template is instantiated with the head and the row's arguments, and the
    engine answers the type it derives [tested:
    test_a_strangers_rule_kind_types_its_own_head; commit=WORKTREE]
  - the declaration is a row a program reads and writes as ordinary data, and
    it dies with the space [tested: test_the_declaration_is_a_row,
    test_a_dropped_space_takes_its_typing_rows_with_it; commit=WORKTREE]
  - a kind nobody registered, and a row whose arguments do not fill the
    template's holes, each refuse by name [tested:
    test_an_unregistered_kind_refuses_by_name,
    test_a_row_that_does_not_fill_the_template_refuses; commit=WORKTREE]
  - the inverse withdraws both the row and the equations
    [tested: test_the_inverse_withdraws_the_row_and_its_equations; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import pytest

from metta import Expression, S, V, seam, typing
from metta.errors import MettaError

#: The fixture library's own rule: a projection of n columns has n columns.
#: `$head` is the head it is declared for and `$arg1` the row's own argument,
#: so ONE template serves `(typing pick two-columns 2)` and every other width.
COLUMN_SELECT = S["="](
    S["get-type"](Expression([V.head, V.frame])),
    S.Frame(S.Columns(V.arg1)),
)

#: A second kind with no equations at all, which is the shape nineteen of the
#: array layer's twenty-one have: the runtime transformation answers, and the
#: row exists to say which rule the head follows.
OBSERVED = ()


@pytest.fixture
def fixture_library():
    """Register the stranger's two rule kinds, and take them away after."""
    seam.typing.register(
        "column-select",
        doc="the frame's shape with the selected column count",
        equations=(COLUMN_SELECT,),
    )
    seam.typing.register(
        "row-observation",
        doc="the frame's row count, observed at run time",
        equations=OBSERVED,
    )
    try:
        yield seam.typing.table()
    finally:
        seam.typing.unregister("column-select")
        seam.typing.unregister("row-observation")


def test_a_strangers_rule_kind_types_its_own_head(fixture_library, metta):
    """The point instantiates a stranger's template and the engine answers it."""
    assert "column-select" in fixture_library
    with metta._new_space() as space:
        typing.declare(space, "pick2", "column-select", 2)
        typing.declare(space, "pick7", "column-select", 7)

        assert space.eval(S["get-type"](S.pick2(S.frame))) == [
            S["%Undefined%"],
            S.Frame(S.Columns(2)),
        ]
        # One template, two heads, two widths: what a Python builder per head
        # used to be is now one row each.
        assert space.eval(S["get-type"](S.pick7(S.frame))) == [
            S["%Undefined%"],
            S.Frame(S.Columns(7)),
        ]


def test_the_declaration_is_a_row(fixture_library, metta):
    """`(typing <space> <head> <kind> <arg>...)` is ordinary catalog data."""
    del fixture_library
    with metta._new_space() as space:
        typing.declare(space, "pick3", "column-select", 3)
        rows = {
            str(row.head): (str(row.kind), tuple(row.rest))
            for row in typing.rules(space)
        }
        kind, arguments = rows["pick3"]
        assert kind == "column-select"
        assert [getattr(argument, "value", argument) for argument in arguments] == [3]
        # A kind with no equations still leaves its row, which is the point:
        # the row says which rule the head follows whether or not the rule
        # derives a type.
        typing.declare(space, "count", "row-observation")
        kinds = {str(row.kind) for row in typing.rules(space)}
        assert {"column-select", "row-observation"} <= kinds


def test_the_inverse_withdraws_the_row_and_its_equations(fixture_library, metta):
    """What `declare` answers puts back exactly what `declare` put in."""
    del fixture_library
    with metta._new_space() as space:
        undo = typing.declare(space, "pick4", "column-select", 4)
        assert space.eval(S["get-type"](S.pick4(S.frame)))[-1] == S.Frame(S.Columns(4))
        undo()
        assert typing.rules(space) == ()
        assert space.eval(S["get-type"](S.pick4(S.frame))) == [S["%Undefined%"]]


def test_withdraw_finds_the_equations_from_the_row(fixture_library, metta):
    """An uninstall has only the space and the head, and needs nothing else."""
    del fixture_library
    with metta._new_space() as space:
        typing.declare(space, "pick5", "column-select", 5)
        assert typing.withdraw(space, "pick5") == ("column-select",)
        assert typing.rules(space) == ()
        assert space.eval(S["get-type"](S.pick5(S.frame))) == [S["%Undefined%"]]


def test_an_unregistered_kind_refuses_by_name(fixture_library, metta):
    """A kind nobody registered names the ones that are registered."""
    del fixture_library
    with (
        metta._new_space() as space,
        pytest.raises(MettaError, match=r"no typing rule kind named 'no-such'"),
    ):
        typing.declare(space, "pick", "no-such")


def test_a_row_that_does_not_fill_the_template_refuses(fixture_library, metta):
    """A row whose arguments leave a hole open refuses naming both counts."""
    del fixture_library
    with (
        metta._new_space() as space,
        pytest.raises(MettaError, match=r"takes 1 argument\(s\).*gives 0"),
    ):
        typing.declare(space, "pick", "column-select")


def test_a_dropped_space_takes_its_typing_rows_with_it(fixture_library, metta):
    """`(owned-by-space typing)` puts the row in the retirement walk."""
    del fixture_library
    space = metta._new_space().__enter__()
    named = S[str(space.name)]
    typing.declare(space, "pick6", "column-select", 6)
    assert any(str(row.head) == "pick6" for row in typing.rules(space))
    catalog = metta._at("&metta")
    pattern = Expression([S[typing.ROW_HEAD], named, V.head, V.kind, V.width])
    assert list(catalog.match(pattern))
    space.drop()
    # The row is in `&metta`, which outlives the space, so the retirement walk
    # is what has to have taken it.
    assert not list(catalog.match(pattern))
