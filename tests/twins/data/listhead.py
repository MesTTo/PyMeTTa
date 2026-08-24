"""examples/data/listhead.metta in Python: list structure, twice over.

`(cons $Head $Tail)` is how MeTTa takes an expression apart, and `head, *tail =
e` is how Python does, at no engine cost at all: the first claim is that
unpacking, written directly.

The recursive `len` is the other half. Its clauses select on `()` and on a cons
cell, which is Python's `match` statement lowering to MeTTa's own case tower,
and its MeTTa name is `len`, which Python already means something by. So the
head is named explicitly and the def carries its own Python name: an explicit
`name=` is exact, which leaves Python's builtin free to answer the third claim,
where the engine's clause-by-clause walk and Python's own count agree.
"""

from metta import Expression, S

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
BUDGET = 1


def twin(m):
    """Unpack an expression, then count one the long way and the short way."""

    @m.define(name="len")
    def length(e):                             # (= (len ()) 0)
        match e:                               # (= (len (cons $Head $Tail))
            case ():                           #    (let $N0 (len $Tail)
                return 0                       #         (+ $N0 1)))
            case (S.cons, _, tail):
                return length(tail) + 1

    head, *tail = Expression((1, 2, 3, 4, 5, 6))   # (let (cons $Head $Tail) ...)
    assert (head, tail) == (1, [2, 3, 4, 5, 6])

    counted = Expression((1, 2, 3))
    assert length(counted).one() == len(counted) == 3   # [3], and Python's own 3
    assert m.fn.cons(42, ()).one() == Expression((42,))   # [(42)]
