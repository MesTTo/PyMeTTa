"""Purpose: a namespace refusal feeds the interpreter's own did-you-mean.

CPython renders "Did you mean" from ``AttributeError.name`` and
``AttributeError.obj``, and it FILLS both itself for anything raised out of
``__getattr__`` on every Python this package supports [measured 2026-09-06 on
CPython 3.14.4: a bare ``AttributeError(name)`` from a class and from a module
``__getattr__`` both arrive with the two fields set; discussed at
https://discuss.python.org/t/64942, "not as early as 3.10 ... but 3.12 does
this"]. So the fields alone were never the gap. Two things were:

  - a BRACKET or METHOD door is not attribute access, so nothing fills them
    there and ``fn["car-atmo"]`` and ``answers.column("wha")`` rendered no
    suggestion at all;
  - a suggestion is computed from ``dir(obj)``, so a projection whose
    attributes are its columns has to answer them from ``__dir__`` or the
    interpreter suggests a tuple method where the library names a column.

The fields are therefore set at every refusal rather than at the ones that
need them: which door a refusal came through is not the raise site's business,
and the auto-fill is an interpreter internal rather than a documented
guarantee. A private-name guard is the exception, staying bare because it
answers protocol probes from ``copy``, ``pickle`` and ``inspect`` where the
round trip costs 296 ns against 462 ns and nobody reads the traceback
[measured 2026-09-06: minimum of nine timeit rounds of 200,000 on CPython
3.14.4, recorded in
docs/journal/2026-09-06-a-head-knows-where-it-came-from.md].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import traceback

import pytest

import metta
from metta import S, V


@pytest.fixture()
def m(metta):
    """An isolated space, so a definition made here is one this test made."""
    with metta._new_space() as space:
        yield space


def _rendered(action) -> tuple[AttributeError, str]:
    """The refusal and the traceback text the interpreter would print."""
    with pytest.raises(AttributeError) as caught:
        action()
    error = caught.value
    return error, "".join(traceback.format_exception(error))


def test_the_generated_namespace_refusal_carries_both_fields():
    """Offer the same name the library's own difflib suggestion offers.

    `S`, `V` and `fn` mint from a generated catalog, and a near miss in one
    is the case that suggestion was written for; the interpreter now draws
    from the same roster.
    """
    error, text = _rendered(lambda: metta.fn.car_atmo)
    assert error.name == "car_atmo"
    assert error.obj is not None
    assert "generated catalog" in str(error), "the library's own sentence stays"
    assert "Did you mean: 'car_atom'?" in text


def test_the_live_function_namespace_refusal_suggests_a_defined_head(m):
    """Suggest a head that exists in THIS space.

    The live namespace knows what the space defines, so the suggestion is a
    definition rather than a name from a shipped roster.
    """
    m.run("(= (dbl $x) (* 2 $x))")
    error, text = _rendered(lambda: m.fn.dbll)
    assert error.name == "dbll"
    assert "define it with @space.define" in str(error)
    assert "Did you mean: 'dbl'?" in text


def test_the_package_module_refusal_suggests_an_exported_name():
    """Draw a module's suggestion from the module's own directory.

    A module `__getattr__` names the module as its object, and the package's
    `__dir__` is the roster the suggestion comes from.
    """
    error, text = _rendered(lambda: metta.spacs)
    assert error.name == "spacs"
    assert error.obj is metta
    assert "Did you mean: 'space'?" in text


def test_a_row_offers_its_own_columns(m):
    """Suggest a column where the library names a column.

    A `Row` is a tuple subclass whose attributes are the query's variables,
    so its `__dir__` has to answer them. Without it the interpreter would
    offer a tuple method, and the two would disagree about one mistake.
    """
    m.add("(likes Ada coffee)")
    rows = m.match(S.likes(V.who, V.what))._eager_rows()

    error, text = _rendered(lambda: rows[0].wha)
    assert error.name == "wha"
    assert "no column 'wha'" in str(error)
    assert "Did you mean: 'what'?" in text

    error, text = _rendered(lambda: rows.wha)
    assert "Did you mean: 'what'?" in text, "and the table agrees with its row"


def test_a_context_door_that_belongs_to_the_space_still_names_the_remedy():
    """Keep the remedy the refusal already explains.

    `is_function` is a Space door and MeTTa is not a Space; the two fields
    ride beside that sentence rather than replacing it.
    """
    error, _text = _rendered(lambda: metta.engine().is_function)
    assert error.name == "is_function"
    assert "Write `m.self.is_function`" in str(error)


def test_a_bracket_door_suggests_where_the_interpreter_fills_nothing(m):
    """The exact-name doors are the ones that needed this.

    `fn[...]` and `column(...)` are not attribute access, so the
    interpreter's own fill never runs on them: before the raise sites
    carried the two fields these refusals rendered no suggestion at all.
    """
    m.run("(= (dbl $x) (* 2 $x))")

    error, text = _rendered(lambda: metta.fn["car-atmo"])
    assert (error.name, error.obj is not None) == ("car-atmo", True)
    assert "Did you mean:" in text

    error, text = _rendered(lambda: m.fn["dbll"])
    assert error.name == "dbll"
    assert "Did you mean: 'dbl'?" in text

    m.add("(likes Ada coffee)")
    answers = m.match(S.likes(V.who, V.what))
    error, text = _rendered(lambda: answers.column("wha"))
    assert error.name == "wha"
    assert "Did you mean: 'what'?" in text


def test_a_solution_row_offers_its_own_variables(m):
    """Suggest a solution variable from the row that carries it.

    `solve` answers its own row type, whose attributes are the winning
    pattern's variables, and it inherits the table's directory.
    """
    solved = m.solve(S.dym_solved(V.score), S.dym_solved(42))

    error, text = _rendered(lambda: solved.scoree)
    assert error.name == "scoree"
    assert "no solution variable 'scoree'" in str(error)
    assert "Did you mean: 'score'?" in text


def test_the_testing_module_names_both_suites_without_importing_them():
    """Answer a lazily imported name before anything imports it.

    A module's `__dir__` is its suggestion pool, and both suite names live
    behind PEP 562 until first use.
    """
    # Imported HERE and not at module scope: the assertion is that a
    # module's directory does not resolve either compliance import.
    import sys

    import metta.testing

    assert {"SpaceComplianceSuite", "GatewayComplianceSuite"} <= set(dir(metta.testing))
    assert "metta._compliance" not in sys.modules, "dir() resolved an import"

    error, text = _rendered(lambda: metta.testing.SpaceComplianceSuit)
    assert error.name == "SpaceComplianceSuit"
    assert "Did you mean: 'SpaceComplianceSuite'?" in text


def test_a_projection_answers_its_columns_from_dir(m):
    """The suggestion pool is `dir(obj)`, so a column has to be in it.

    A `Row` is a tuple subclass with empty slots and its columns on the
    per-query class, and an `Event`'s bindings live in a mapping; neither
    appears in the default directory, so both name them.
    """
    m.add("(likes Ada coffee)")
    rows = m.match(S.likes(V.who, V.what))._eager_rows()
    assert {"who", "what"} <= set(dir(rows[0]))
    assert {"who", "what"} <= set(dir(rows))

    from metta.events import Event

    event = Event("add", "&self", S.likes(S.Ada, S.coffee), {"who": S.Ada})
    assert "who" in dir(event)
    error, text = _rendered(lambda: event.wh)
    assert error.name == "wh"
    assert "Did you mean: 'who'?" in text
