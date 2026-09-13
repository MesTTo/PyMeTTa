"""Purpose: exercise patterned references through Python's ordinary space API.

Guarantees: lazy aliases retain their source, shared bodies, type declarations
and variable bindings [tested: test_patterned_references_load_lazily_and_report_their_source,
test_a_patterned_alias_follows_its_providers_equations;
commit=WORKTREE].
Owns resources: the space context managers release their native definitions.
"""

from collections import Counter

import pytest

from metta import Expression, Grounded, S, V, parse
from metta._errors.errors import EngineError


@pytest.mark.parametrize("self_reference", [False, True])
def test_patterned_references_load_lazily_and_report_their_source(metta, self_reference):
    """A selected lazy body keeps its arrow, origin and fresh receiver fields."""
    with metta._new_space() as home, metta._new_space() as peer:
        target = home if self_reference else peer
        home.run("!(pragma! load lazy)")
        home.run("""
            (: patterned-body (-> Atom Number Number))
            (= (patterned-body (Pair $x $y) $n) (+ (+ $x $y) $n))
        """)
        mapping = parse("(rename ((patterned-body (patterned-call (Pair $x $y) $n))))")
        target.from_(home, mapping)
        for x, y, n in ((3, 4, 5), (-2, 8, 7), (0, 0, 0)):
            assert target.eval(S.patterned_call(S.Pair(x, y), n)) == [x + y + n]
        assert parse("(: patterned-call (-> Atom Number Number))") in target
        assert target.fn["patterned-call"].origin == home.fn["patterned-body"].origin
        origins = [row.args[0] for row in target.get_property("patterned-call")
                   if row.head == S.origin]
        assert origins and all(str(origin) == home.name for origin in origins)


def test_a_patterned_alias_follows_its_providers_equations(metta):
    """Source mutations and withdrawal affect the existing alias immediately."""
    with metta._new_space() as home, metta._new_space() as target:
        first = parse("(= (patterned-source $a $b) (quote (answer $a $b)))")
        second = parse("(= (patterned-source $a $b) (quote (later $a $b)))")
        home.add(first)
        mapping = parse("(rename ((patterned-source (patterned-equal $x $x))))")
        target.from_(home, mapping)
        assert target.eval(S.patterned_equal(3, 3)) == [S.answer(3, 3)]
        home.add(second)
        assert Counter(target.eval(S.patterned_equal(4, 4))) == Counter([
            S.answer(4, 4), S.later(4, 4),
        ])
        home.remove(first)
        assert target.eval(S.patterned_equal(5, 5)) == [S.later(5, 5)]
        assert S.answer(3, 4) not in target.eval(S.patterned_equal(3, 4))
        target.remove(Expression(S["from"], home, mapping))
        assert S.later(6, 6) not in target.eval(S.patterned_equal(6, 6))


@pytest.mark.parametrize("result", [42, Expression(), Expression(7, S.x), Expression(V.head, S.x)])
def test_a_bad_pattern_mapper_leaves_no_reference_row(metta, result):
    """Invalid targets abort declaration before a reference row survives."""
    with metta._new_space() as home, metta._new_space() as target:
        home.run("(= (pattern-map-source) 1)")
        mapping = Grounded(lambda _head: result)
        with pytest.raises(EngineError, match="each answer must be a symbol or a finite call pattern"):
            target.from_(home, mapping)
        assert not any(isinstance(row, Expression) and row.head == S["from"] for row in target)


def test_an_argument_pattern_cannot_export_an_internal_definition(metta):
    """Argument selection grants no additional visibility."""
    with metta._new_space() as home, metta._new_space() as target:
        home.run("(internal pattern-hidden)\n(= (pattern-hidden $x) $x)")
        with pytest.raises(EngineError, match="pattern-hidden is internal"):
            target.from_(home, parse("(rename ((pattern-hidden (pattern-visible $x))))"))
