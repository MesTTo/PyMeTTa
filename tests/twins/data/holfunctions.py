"""examples/data/holfunctions.metta in Python: the higher-order forms.

`map-atom`, `filter-atom` and `foldl-atom` walk an expression with a TEMPLATE
or with a named function, and the file is that contrast written six times.
Python draws the same line and the compiler emits the same instructions on
either side of it: an inline expression is a comprehension or a lambda, and a
named function is that name written in the same place.

So the `a` half reads as ordinary Python with the work inline, the `b` half
reads as ordinary Python with the work named, and the engine sees the two
instruction shapes the original wrote by hand. `functools.reduce` is the fold
in both halves, taking a lambda in one and a function in the other; the
comprehension is the map and the filter, calling the named function where the
`b` half names one.

The last form folds expressions rather than numbers, with `append` reached at
the function namespace, where rung 4's map turns the underscore back into the
hyphen the engine holds. Every definition here is nullary except that one, so
no stacking question arises anywhere in the file.
"""

import functools

from metta import Expression, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Fold, map and filter, first with the work inline and then with it named."""

    @m.define
    def foldfun(a, b):                    # (= (foldfun $a $b) (+ $a $b))
        return a + b

    @m.define
    def mapfun(a):                        # (= (mapfun $a) (+ $a 1))
        return a + 1

    @m.define
    def filterfun(x):                     # (= (filterfun $x) (> $x 3))
        return x > 3

    @m.define
    def f1a():                            # (= (f1a) (foldl-atom (1 2 3 4) 0
        return functools.reduce(lambda acc, x: acc + x, (1, 2, 3, 4), 0)  # $acc $x (+ $acc $x)))

    @m.define
    def f2a():                            # (= (f2a) (map-atom (1 2 3) $x (+ $x 1)))
        return [x + 1 for x in (1, 2, 3)]

    @m.define
    def f3a():                            # (= (f3a) (filter-atom (1 2 3 4 5) $x (> $x 3)))
        return [x for x in (1, 2, 3, 4, 5) if x > 3]

    @m.define
    def f1b():                            # (= (f1b) (foldl-atom (1 2 3 4) 0 foldfun))
        return functools.reduce(foldfun, (1, 2, 3, 4), 0)

    @m.define
    def f2b():                            # (= (f2b) (map-atom (1 2 3) mapfun))
        return [mapfun(x) for x in (1, 2, 3)]

    @m.define
    def f3b():                            # (= (f3b) (filter-atom (1 2 3 4 5) filterfun))
        return [x for x in (1, 2, 3, 4, 5) if filterfun(x)]

    @m.define
    def foldfun2(a, b):                   # (= (foldfun2 $a $b) (append $a $b))
        return fn.append(a, b)

    @m.define
    def joined(parts):                    # (foldl-atom ((1 2) (3 4) (5 6)) ()
        return functools.reduce(lambda acc, x: fn.append(acc, x), parts, ())  # $acc $x (append $acc $x))

    assert f1a().one() == 10                          # [10]
    assert f2a().one() == Expression((2, 3, 4))       # [(2 3 4)]
    assert f3a().one() == Expression((4, 5))          # [(4 5)]

    assert f1b().one() == 10                          # [10]
    assert f2b().one() == Expression((2, 3, 4))       # [(2 3 4)]
    assert f3b().one() == Expression((4, 5))          # [(4 5)]

    parts = Expression((Expression((1, 2)), Expression((3, 4)), Expression((5, 6))))
    assert joined(parts).one() == Expression((1, 2, 3, 4, 5, 6))   # [(1 2 3 4 5 6)]
