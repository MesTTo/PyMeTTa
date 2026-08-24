"""examples/data/holfunctions_intrinsicop.metta in Python: a builtin, half applied.

`mymap` is written out rather than borrowed: an empty expression answers an
empty expression and a cons cell rebuilds itself around the applied function.
Both clauses select on the SHAPE of the second argument, which is Python's
`match` statement lowering to MeTTa's own case tower.

The recursive clause names the applied head and mapped tail before rebuilding
the cons cell. Plain assignments in a compiled body are the Python spelling of
the example's nested `let` sequence.
[source: examples/data/holfunctions_intrinsicop.metta:9; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]

The claim is that a builtin and a defined function behave the same when either
is handed to `mymap` half applied. `(== 1)` is equality with one argument, and
`eq` is a function whose whole body is that same equality written as Python's
own operator, so the two calls differ in nothing but which of them the engine
had to compile. Applying a half-applied head is the one place a tuple beats a
call, because the head is a value here rather than a name.

The two half applications sit either side of the operator word table. `fn.eq`
is `==`, the builtin, because the word table maps every operator to its
`operator`-module name at the attribute door; the DEFINED function is the
symbol literally spelled `eq`, so it takes the bracket, which is the exact
door by the same ruling. Naming both on one line is what makes the claim
readable.
"""

from metta import Expression, S, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=77e8bdc3dd822df05a2a6a9ec357c87fe1c3ac32].
BUDGET = 1


def twin(m):
    """Map a half-applied builtin and its defined twin over one list."""

    @m.define
    def mymap(f, items):                    # (= (mymap $f ()) ())
        match items:                        # (= (mymap $f (cons $x $xs))
            case ():                        #    (cons ($f $x) (mymap $f $xs)))
                return ()
            case (S.cons, x, rest):
                head = f(x)
                tail = mymap(f, rest)
                return S.cons(head, tail)

    @m.define
    def eq(a, b):                           # (= (eq $a $b) (== $a $b))
        return a == b

    numbers = Expression((1, 2, 3))
    defined = S["eq"](1)  # rung: the word table owns S.eq, which is ==, so the symbol named eq takes rung 5's exact door
    assert mymap(fn.eq(1), numbers) == mymap(defined, numbers)   # [(True False False)]
