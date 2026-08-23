"""examples/libraries/test_memo_per_arity.metta in Python: memoizing one arity of a name.

`add` carries two arities, and `memoize add 2` caches only the two-argument
one. Both equations come through `@rules`, which is what two clauses under one
name need: a second `@m.define` for the same name is a redefinition rather than
an alternative, and for a second ARITY it raises outright, which the residue
table already records.

`x + y + z` in the rules body is Python's own left-associating addition, so it
builds `(+ (+ $x $y) $z)` without a word about it.
"""

from petta import S, equation, rules

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Two arities of one name, one of them cached."""
    m.eval(S["import!"](m, S.library(S["lib_memo"])))

    @rules
    def add(x, y, z):
        yield equation(S.add(x, y)).to(x + y)
        yield equation(S.add(x, y, z)).to(x + y + z)

    m += add
    m.eval(S.memoize(S.add, 2))

    sum_ = m.fn.add
    assert sum_(3, 4) == [7]
    assert sum_(3, 4) == [7]

    # The three-argument arity is untouched by the declaration above.
    assert sum_(1, 2, 3) == [6]

    assert sum_(5, 6) == [11]
    assert sum_(5, 6) == [11]
