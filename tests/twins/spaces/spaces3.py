"""Purpose: examples/spaces/spaces3.metta in Python: what a pattern's SHAPE selects.

Two atoms go into a space, `(wu)` and `(wu 42)`. Four queries over them differ
only in the pattern: `($x)` is a one-element expression and selects only the
one-element atom, while a bare `$x` selects everything, which is what
enumerating the space already gives you. The example's template argument has no
counterpart here: a query answers BINDINGS, and building a term out of a
binding is ordinary Python.

Where that stops being true is worth knowing, because it is a SIZE limit and
not a taste one. Counting through the Python door materialises every answer as
a Python atom, so it pays for the answers' SIZE, where the engine's own
`(length (collapse ...))` pays only for their number. Measured 2026-08-22 over
one stored atom whose payload is a Peano term of depth K, at K =
250/500/1000/2000: the Python door costs 2,082 / 8,104 / 20,128 / 44,150
inferences, linear in the depth, while the engine costs 570 / 266 / 272 / 278,
flat. Over N answers of depth K that is N*K against N. Two atoms of depth two
is the shallow end, where the difference is nothing; a corpus twin that counts
1,572,862 answers is the other end, where the Python door exhausts the Prolog
stack before it can finish. Four twins in `reasoning/` and `performance/`
therefore keep the engine's count and say so.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V

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
    one = wuspace.query(Expression((V.x,)))
    assert [row.x for row in one] == [S.wu]
    assert [Expression((row.x,)) for row in one] == [S.wu()]
    assert [S.hu(row.x) for row in one] == [S.hu(S.wu)]

    # A bare variable matches every atom, which is what iterating a space is.
    assert sorted(wuspace.query(V.x)["x"], key=str) == sorted(wuspace, key=str)
    assert sorted((S.wu(row.x) for row in wuspace.query(V.x)), key=str) == sorted(
        [S.wu(S.wu()), S.wu(S.wu(42))], key=str
    )
