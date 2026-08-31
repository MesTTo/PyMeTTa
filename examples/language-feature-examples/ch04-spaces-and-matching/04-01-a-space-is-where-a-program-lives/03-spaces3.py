"""Purpose: examples/ch04-spaces-and-matching/04-01-a-space-is-where-a-program-lives/03-spaces3.metta in Python: what a pattern's SHAPE selects.

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


#: Inferences this twin spends, its own tripwire. INTERIM PIN 2026-08-24,
#: identity.py's own precedent: this file gates the pytest lane, so it is
#: priced ahead of the corpus-wide pass and re-priced there with everything
#: else. Min-of-3 on the integration merge of the Stage C branch, three
#: identical readings [measured 2026-08-24 through the end-to-end twin test
#: on the merged tree at 5a5054ca].
#:
#: RE-PINNED 2026-08-27, 234 to 252 (+18, and +14 against the 238 the old pin
#: actually read), for the wire codec's species question: metta_py_encode/2
#: asks metta_space_operand/1 of every atom it encodes now, where it used to
#: compare against two hardcoded names, so this twin's space handles and
#: symbols each pay one indexed lookup. Six identical readings, three before
#: and three after [measured 2026-08-27 through the end-to-end twin test,
#: 238 on the unchanged tree at 5d8769c7 and 252 here].
#: RE-PINNED 2026-08-28, 252 to 242 (-10), metta_space_operand/1's ampersand
#: guard. metta_py_encode/2 asks it of every atom it encodes, the entry above
#: records that as the +18 this pin last took, and it reads the prefix before
#: probing either space registry now, so an ordinary symbol costs 3 inferences
#: there instead of 8. The whole move is this change: three identical serial
#: min-of-three rounds read 252 on the unchanged tree, which is exactly this
#: pin, and 242 here, and the pytest lane's own end-to-end run reads the same
#: 242 through xdist. Both sides confirmed current_predicate(mork/3) first,
#: because a round taken while this worktree's MORK link was dangling read 240
#: and 234 instead and would have pinned a configuration the gate does not run
#: [measured 2026-08-28: min-of-3 serial fresh processes; command=python
#: bindings/python/tools/twin_coverage.py --repin; commit=0289cbd162aeb0380fbbe502129bca3b976b32c7].
#: RE-PINNED 2026-08-31, 242 to 252 (+10), the lazy cursor pulls a doubling
#: chunk per janus crossing now, and the chunk's Prolog-side collection loop
#: retires about three inferences per answer where the per-answer crossing
#: retired its own wrapper; drains halve, a tiny stream pays a few inferences
#: more [measured 2026-08-31: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=505aec3433047045a96abdf00cecf4477b9a702b].
BUDGET = 252
