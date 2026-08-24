"""Purpose: examples/spaces/spaces3.metta in Python: what a pattern's SHAPE selects.

Two atoms go into a space, `(wu)` and `(wu 42)`. Four queries over them differ
only in the pattern: `($x)` is a one-element expression and selects only the
one-element atom, while a bare `$x` selects everything, which is what
enumerating the space already gives you. The example's template argument has no
counterpart here: a query answers BINDINGS, and building a term out of a
binding is ordinary Python.

Every ask is the subscript now. The one-element expression pattern used to have
no subscript spelling at all, because Python cannot tell `space[(a, b)]` from
`space[a, b]` and the door read every tuple as a conjunction; the one-pattern
law settled it, so `wuspace[(V.x,)]` is the one-element expression `($x)` and a
conjunction is written with the receiver method's varargs
[measured 2026-08-24: `wuspace[(V.x,)]` answers one row binding x to the single
child, agreeing with `wuspace.match(Expression((V.x,)))`; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].

`sorted(atoms)` is `msort`, because atoms carry the engine's own elementwise
order, so the two claims the original sorts read the same way here.

Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import Expression, S, V

#: Inferences this twin spends, its own tripwire. INTERIM PIN 2026-08-24,
#: identity.py's own precedent: this file gates the pytest lane, so it is
#: priced ahead of the corpus-wide pass and re-priced there with everything
#: else. Min-of-3 on the integration merge of the Stage C branch, three
#: identical readings [measured 2026-08-24 through the end-to-end twin test
#: on the merged tree at 5a5054ca].
BUDGET = 234


def twin(m):  # noqa: ARG001  -- the twin works in its own named space; the default handle stays untouched
    """Write two atoms, then ask four questions about them."""
    wuspace = metta.space(S.wuspace)
    wuspace += S.wu()
    wuspace += (S.wu, 42)

    # `($x)` is an expression of one element, so only `(wu)` matches it, and
    # $x binds to that element rather than to the whole atom.
    one = wuspace[(V.x,)]
    # Both answer containers project the same way, so the whole column comes
    # off the ask door by attribute just as it does off a call.
    assert one.x == [S.wu]
    assert [Expression((row.x,)) for row in one] == [S.wu()]
    assert [S.hu(row.x) for row in one] == [S.hu(S.wu)]

    # A bare variable matches every atom, which is what iterating a space is.
    every = [row.x for row in wuspace[V.x]]
    assert sorted(every) == sorted(wuspace)
    assert sorted(S.wu(child) for child in every) == [S.wu(S.wu()), S.wu(S.wu(42))]
