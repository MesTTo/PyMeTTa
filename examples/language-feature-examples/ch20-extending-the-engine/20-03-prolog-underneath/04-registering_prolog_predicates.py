"""examples/ch20-extending-the-engine/20-03-prolog-underneath/04-registering_prolog_predicates.metta in Python: the two operations a registration is.

`check_prolog_function_names` asks whether a list of names MAY be registered
from a source, before that source loads, and `import_prolog_functions`
registers every name or none. Both keep their underscores, so both come
through the exact subscript door.

A name list is HELD, and the reason is not decoration: a name the engine
already holds a function for would be CALLED if the list were evaluated, so
`fn.noeval(...)` is what the original writes and what this builds.

Every fixture predicate keeps its Prolog underscore, so every one of them is
written `S["rung_double"]` and not `S.rung_double`, which the host-convention
map would read as `rung-double` -- a name no predicate answers to.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from pathlib import Path

from metta import G, S, V, arrow, fn, lib, typed
from metta.errors import MettaError

_REPO = Path(__file__).resolve().parents[6]
FUNCTIONS = _REPO / Path(
    "examples/ch20-extending-the-engine/20-03-prolog-underneath/_fixtures/rung_functions.pl"
)
FIXTURES = _REPO / Path(
    "examples/ch20-extending-the-engine/20-03-prolog-underneath/_fixtures"
)


def refused(call, *arguments):
    """The error one refused registration raises, or None where it held."""
    try:
        list(call(*arguments))
    except MettaError as failure:
        return failure
    return None


def twin(m):
    """Ask, then register; assert and retract; then register a directory."""
    m += lib["lib_import"]
    # The declaration the original writes, so both spaces hold it.
    m += typed(S.Predicate, arrow(S.Expression, S["%Undefined%"]))
    check = m.fn["check_prolog_function_names"]
    register = m.fn["import_prolog_functions"]

    # Asking is all this does, and it touches nothing.
    assert check(fn.noeval((S["rung_fresh_one"], S["rung_fresh_two"])), G("example.pl")) == [
        True
    ]

    # Asking FIRST is not politeness, it is the only order that can work:
    # consulting a file that defines a builtin's name has already replaced
    # the engine's predicate by the time a per-name refusal could fire.
    reserved = refused(check, fn.noeval((S.car_atom,)), G("example.pl"))
    assert "car-atom is a builtin" in str(reserved)
    assert "would replace the engine's own for every space" in str(reserved)

    # It is all-or-nothing about the LIST too, so a bad name anywhere in it
    # refuses the whole list.
    mixed = refused(check, fn.noeval((S["rung_fresh_one"], S.car_atom)), G("example.pl"))
    assert "car-atom is a builtin" in str(mixed)

    # The other half refuses a name with no predicate behind it, because
    # registering one compiles every call into a partial application.
    absent = refused(register, fn.noeval((S["rung_absent_predicate"],)))
    assert "would compile every call to it into a partial application" in str(absent)

    # With the predicates there, the same call registers them and they are
    # MeTTa functions from then on.
    # Consulted through the ordinary import door, whose name list is kept
    # literal by the translator, and then registered by the operation this
    # file is about.
    assert m.fn["import_prolog_functions_from_file"](G(str(FUNCTIONS)), ()) == [True]
    assert register(fn.noeval((S["rung_double"], S["rung_greeting"]))) == [True]
    assert m.fn["rung_double"](21) == [42]
    assert m.fn["rung_greeting"]() == [S.world]

    # The Prolog database from MeTTa: assert at the END of the clause list,
    # retract the first clause that unifies. Both answer a Bool, and
    # retracting something that is not there answers False.
    assert_last, assert_first = m.fn.assertzPredicate, m.fn.assertaPredicate
    retract, call_it = m.fn.retractPredicate, m.fn.callPredicate
    fact = S.Predicate(S["rung_fact"](S.a))
    assert assert_last(fact) == [True]
    assert assert_last(S.Predicate(S["rung_fact"](S.b))) == [True]
    solutions = S.let(  # rung: let as a binder over a predicate's own solutions
        V.verdict, S.callPredicate(S.Predicate(S["rung_fact"](V.x))), V.x
    )
    assert m.answers(solutions) == [
        S.a,
        S.b,
    ]  # rung: let as a binder over a predicate's own solutions
    assert retract(fact) == [True]
    assert retract(S.Predicate(S["rung_fact"](S.zzz))) == [False]

    # `assertaPredicate` asserts at the FRONT, which is the difference
    # between the two and the reason both exist: clause order is answer order.
    assert assert_first(S.Predicate(S["rung_fact"](S.earliest))) == [True]
    solutions = S.let(  # rung: let as a binder over a predicate's own solutions
        V.verdict, S.callPredicate(S.Predicate(S["rung_fact"](V.x))), V.x
    )
    assert m.answers(solutions) == [
        S.earliest,
        S.b,
    ]  # rung: let as a binder over a predicate's own solutions
    assert call_it(S.Predicate(S["rung_fact"](S.b))) == [True]

    # `register_metta_library_path` puts a directory under an alias, so a
    # package can point MeTTa at files it ships beside itself. It is
    # idempotent, and a directory that is not there is refused where the
    # caller can still act on it.
    alias = m.fn["register_metta_library_path"]
    assert alias(S.rung_alias, G(str(FIXTURES))) == [True]
    assert alias(S.rung_alias, G(str(FIXTURES))) == [True]
    m.fn["import!"](m, S.library(S.rung_alias, S["rung_library.metta"])).one()
    assert m.fn["rung-aliased"](5) == [105]
    missing = refused(alias, S.rung_nowhere, G("/no/such/directory"))
    assert "a library path must be a directory that exists" in str(missing)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 42186 inferences, 0.9902x the example's 42605; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 42186
