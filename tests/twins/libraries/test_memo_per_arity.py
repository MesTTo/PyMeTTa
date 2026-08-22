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

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 131896 to 125272, -6624 (-5.02%), by the idiomatic
#: rewrite: five `test` wrappers left the engine for `assert`, and the two
#: arities now arrive through one `@rules` write where the source wrote two
#: equations. Measured min-of-three with the MORK backend linked into this
#: worktree, which the earlier figure may not have been. Prior: 131896 was
#: the last figure for the generator twin that yielded `m.eval(S.test(...))`
#: once per runnable form.
BUDGET = 125272


def twin(m):
    """Two arities of one name, one of them cached."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_memo)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @rules
    def add(x, y, z):
        yield equation(S.add(x, y)).to(x + y)
        yield equation(S.add(x, y, z)).to(x + y + z)

    m.add(*add)
    m.eval(S.memoize(S.add, 2))

    sum_ = m.fn("add")
    assert sum_(3, 4) == 7
    assert sum_(3, 4) == 7

    # The three-argument arity is untouched by the declaration above.
    assert sum_(1, 2, 3) == 6

    assert sum_(5, 6) == 11
    assert sum_(5, 6) == 11
