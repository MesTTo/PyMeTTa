"""examples/spaces/spaces3.metta in Python: what a pattern's SHAPE selects.

Two atoms go into a space, `(wu)` and `(wu 42)`. Four queries over them differ
only in the pattern: `($x)` is a one-element expression and selects only the
one-element atom, while a bare `$x` selects everything, which is what
enumerating the space already gives you. The example's template argument has no
counterpart here and needs none: a query answers BINDINGS, and building a term
out of a binding is ordinary Python.
"""

from petta import S, V, expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4090 to 449, -3641 (-89.0%), by the twin contract
#: change: `collapse`, `msort` and the template argument left the engine for
#: `list`, `sorted` and an ordinary comprehension, which on atoms already held
#: in Python are native structure operations with no crossing at all. Against
#: the example's 8581 the ratio is 0.0523, a nineteenfold reduction, and the
#: transliterated twin this replaces cost 4090 for the same claims
#: [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/spaces/spaces3.metta`]. What did NOT move is the matching: two
#: queries still run in the engine, and the five assertions all read them.
BUDGET = 449


def twin(m):
    """Write two atoms, then ask four questions about them."""
    wuspace = m.space("&wuspace")
    wuspace += S.wu()
    wuspace += (S.wu, 42)

    # `($x)` is an expression of one element, so only `(wu)` matches it, and
    # $x binds to that element rather than to the whole atom.
    one = wuspace.query(expr(V.x))
    assert [row.x for row in one] == [S.wu]
    assert [expr(row.x) for row in one] == [S.wu()]
    assert [S.hu(row.x) for row in one] == [S.hu(S.wu)]

    # A bare variable matches every atom, which is what iterating a space is.
    assert sorted(wuspace.query(V.x)["x"], key=str) == sorted(wuspace, key=str)
    assert sorted((S.wu(row.x) for row in wuspace.query(V.x)), key=str) == sorted(
        [S.wu(S.wu()), S.wu(S.wu(42))], key=str
    )
