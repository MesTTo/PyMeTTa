"""The Python twin of examples/performance/scale.metta: a million atoms, indexed.

Every definition stays at the container door. `addK` WRITES with `add-atom`, and
the five query shapes and the driver all name each other by hyphenated MeTTa
names (`q-all`, `q-first`, `indexing-demo`); a compiled body names a function by
exactly its MeTTa spelling and reaches nothing else. Both are residue entries
against P14.4.

The arithmetic and the equality TERM are Python's own: `V.K.eq(0)` is
`(== $K 0)`, `V.K % 10` is `(% $K 10)` and `V.K - 1` is `(- $K 1)`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 24314635 across the term-door rewrite: `equation(...).to(...)`,
#: `.eq`, `%` and `-` build the same atoms the hand-nested `expr` calls built,
#: which the atom-level differential confirms byte-for-byte. Prior: ADDED
#: 2026-08-22 at 24314635 by the wave-3 twin baseline.
BUDGET = 24314635


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (addK $K)
    #    (if (== $K 0)
    #        done
    #        (let* (($K10 (% $K 10))
    #               ($t (add-atom &self (r $K $K10))))
    #               (addK (- $K 1)))))
    m += equation(S.addK(V.K)).to(S["if"](V.K.eq(0),
            S.done,
            S["let*"](((V.K10, V.K % 10),
                    (V.t, S["add-atom"](S["&self"], S.r(V.K, V.K10)))),
                S.addK(V.K - 1))))

    # (= (q-all)
    #    (collapse (match &self (r $x $y) (r $x $y))))
    m += equation(S["q-all"]()).to(S.collapse(S.match(S["&self"], S.r(V.x, V.y), S.r(V.x, V.y))))

    # (= (q-first $a)
    #    (collapse (match &self (r $a $y) (r $a $y))))
    m += equation(S["q-first"](V.a)).to(
        S.collapse(S.match(S["&self"], S.r(V.a, V.y), S.r(V.a, V.y)))
    )

    # (= (q-second $b)
    #    (collapse (match &self (r $x $b) (r $x $b))))
    m += equation(S["q-second"](V.b)).to(
        S.collapse(S.match(S["&self"], S.r(V.x, V.b), S.r(V.x, V.b)))
    )

    # (= (q-both $a $b)
    #    (collapse (match &self (r $a $b) (r $a $b))))
    m += equation(S["q-both"](V.a, V.b)).to(
        S.collapse(S.match(S["&self"], S.r(V.a, V.b), S.r(V.a, V.b)))
    )

    # (= (q-rel $r)
    #    (collapse (match &self ($r 643 3) ($r 643 3))))
    m += equation(S["q-rel"](V.r)).to(S.collapse(S.match(S["&self"], (V.r, 643, 3), (V.r, 643, 3))))

    # (= (indexing-demo $K)
    #    (let* (($temp (addK $K))
    #           ($all (q-all))
    #           ($first (q-first 7))
    #           ($second (q-second 3))
    #           ($rel (q-rel r))
    #           ($both (q-both 42 2)))
    #          (all: (length $all) first: (length $first) second: (length $second) rel: (length $rel) both: (length $both))))
    m += equation(S["indexing-demo"](V.K)).to(S["let*"](((V.temp, S.addK(V.K)),
                (V.all, S["q-all"]()),
                (V.first, S["q-first"](7)),
                (V.second, S["q-second"](3)),
                (V.rel, S["q-rel"](S.r)),
                (V.both, S["q-both"](42, 2))),
            S["all:"](S.length(V.all),
                S["first:"],
                S.length(V.first),
                S["second:"],
                S.length(V.second),
                S["rel:"],
                S.length(V.rel),
                S["both:"],
                S.length(V.both))))

    # !(test (indexing-demo 1000000)
    #        (all: 1000000 first: 1 second: 100000 rel: 1 both: 1))
    yield m.eval(
        S.test(S["indexing-demo"](1000000),
            (
                S["all:"], 1000000,
                S["first:"], 1,
                S["second:"], 100000,
                S["rel:"], 1,
                S["both:"], 1,
            ))
    )
