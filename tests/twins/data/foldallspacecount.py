"""examples/data/foldallspacecount.metta in Python: counting by folding ones.

`countitem` answers 1 once per atom the match finds, and folding those ones
with `merge` counts them, so three `foo` facts make 3. The counting is done by
the fold rather than by a length, which is the point: the generator answers
once per row and the aggregator never sees a row at all.

All three definitions are compiled. `countitem` binds the row and does not use
it, which is what the original's `let` does too, and a bound-then-unused name
is Python's own `_row`; the match reads the handle it was given, so no space is
ever named as a symbol. `spacecount`'s parameter is `_`, MeTTa's own anonymous
variable, because the original ignores it as well.
"""

from metta import S, V, match

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Put three facts in the space, then count them by folding ones."""
    m += [(S.foo, n) for n in (1, 2, 3)]         # (foo 1) (foo 2) (foo 3)

    @m.define
    def countitem():                             # (= (countitem)
        _row = match(m, S.foo(V.n), S.foo(V.n))  #    (let $x (match &self (foo $1) (foo $1))
        return 1                                 #         1))

    @m.define
    def merge(a, b):                             # (= (merge $a $b) (+ $a $b))
        return a + b

    @m.define
    def spacecount(_):                           # (= (spacecount $x)
        return S.foldall(merge, countitem(), 0)  #    (foldall merge (countitem) 0))

    assert m.fn.foldall(S.merge, S.countitem(), 0).one() == 3   # [3]
