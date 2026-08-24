"""examples/libraries/memo_per_arity.metta in Python: memoizing one arity of a name.

`add` carries two arities, and `memoize add 2` caches only the two-argument
one. The two clauses are STACKED decorations of one MeTTa name, which the
define door dispatches by arity; the second Python name states the MeTTa name
exactly, because its own underscore map would reach a different head.

Both arities are CALLED by their Python names. A decorated definition answers
a callable, so `add(3, 4)` is the call the example writes and no namespace sits
between the two.

The one name here that cannot take the attribute door is the memoize argument.
`add` is one of the operator words, so `S.add` is the symbol `+`; the example
caches the function it just defined, which is the head literally named `add`,
and rung 5's bracket is the exact door for it.

`x + y + z` in the compiled body is Python's own left-associating addition, so
it builds `(+ (+ $x $y) $z)` without a word about it.
"""

from metta import S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Two arities of one name, one of them cached."""
    m.fn["import!"](m, S.library(S["lib_memo"]))

    @m.define
    def add(x, y):
        # (= (add $x $y) (+ $x $y))
        return x + y

    @m.define(name="add")
    def add_3(x, y, z):
        # (= (add $x $y $z) (+ (+ $x $y) $z))
        return x + y + z

    m.eval(S.memoize(S["add"], 2))

    assert add(3, 4) == [7]
    assert add(3, 4) == [7]

    # The three-argument arity is untouched by the declaration above.
    assert add_3(1, 2, 3) == [6]

    assert add(5, 6) == [11]
    assert add(5, 6) == [11]
