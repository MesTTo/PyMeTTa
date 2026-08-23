"""Purpose: examples/spaces/spaces3.metta in Python: what a pattern's SHAPE selects.

Two atoms go into a space, `(wu)` and `(wu 42)`. Four queries over them differ
only in the pattern: `($x)` is a one-element expression and selects only the
one-element atom, while a bare `$x` selects everything, which is what
enumerating the space already gives you. The example's template argument has no
counterpart here: a query answers BINDINGS, and building a term out of a
binding is ordinary Python.

`sorted(atoms)` is `msort`, because atoms carry the engine's own elementwise
order, so the two claims the original sorts read the same way here.

Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import petta
from petta import Expression, S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
#: INTERIM PIN 2026-08-23, min-of-3 on the wave-merged tree (359 against the example's 8573): this file gates the pytest lane, so it is priced ahead of the corpus-wide pass that follows the library fixes, the guide update, and the marked-site sweep, and it is re-priced there with everything else.
BUDGET = 359


def twin(m):  # noqa: ARG001  -- the twin works in its own named space; the default handle stays untouched
    """Write two atoms, then ask four questions about them."""
    wuspace = petta.space("&wuspace")
    wuspace += S.wu()
    wuspace += (S.wu, 42)

    # `($x)` is an expression of one element, so only `(wu)` matches it, and
    # $x binds to that element rather than to the whole atom.
    #
    # GAP: the subscript door cannot say this pattern. Python cannot tell
    # `space[(a, b)]` from `space[a, b]`, so the subscript reads every tuple as
    # a CONJUNCTION while query reads the same tuple as an expression:
    # `m[(V.x,)]` answers two rows binding x to whole atoms and
    # `m.query((V.x,))` answers one row binding x to the single child
    # [measured 2026-08-22]. PERFECT: `wuspace[(V.x,)]`. Residue P14.4; until
    # it lands the one-element expression is spelled at the ( ) door and asked
    # through query, which agree.
    one = wuspace.query(Expression((V.x,)))
    # GAP: the ask door answers `Rows`, which projects only through a
    # STRING key, `one["x"]`, the spelling the surface's own anti-pattern
    # table retires; the call door answers `Answers`, which projects by
    # attribute. PERFECT: `one.x == [S.wu]`, the same projection at both
    # doors. `Rows` is a mutable list besides, where answers are immutable
    # [measured 2026-08-23: Rows has append/clear/pop/sort and no attribute
    # projection; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
    assert [row.x for row in one] == [S.wu]
    assert [Expression((row.x,)) for row in one] == [S.wu()]
    assert [S.hu(row.x) for row in one] == [S.hu(S.wu)]

    # A bare variable matches every atom, which is what iterating a space is.
    every = [row.x for row in wuspace.query(V.x)]
    assert sorted(every) == sorted(wuspace)
    assert sorted(S.wu(child) for child in every) == [S.wu(S.wu()), S.wu(S.wu(42))]
