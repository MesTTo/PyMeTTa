"""The Python twin of examples/performance/matespacefast.metta: 1.5M atoms.

Both definitions stay at the container door for the same reason: their bodies
WRITE with `add-atom`, and a compiled body names a function by exactly its MeTTa
spelling, which `add-atom` is not a Python identifier for. `mate-space-demo`
also matches against `&self` inside a `let*` whose bindings are the writes. Both
are residue entries against P14.4.

The arithmetic and the equality TERM are Python's own: `V.n.eq(0)` is
`(== $n 0)` and `V.n - 1` is `(- $n 1)`, and the `let*` binding list is a tuple
of pairs, which is what MeTTa's `(($v $e) ...)` is.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: HELD 2026-08-22 at 34349629 across the term-door rewrite: `equation(...).to(...)`,
#: `.eq` and `-` build the same atoms the hand-nested `expr` calls built, which
#: the atom-level differential confirms byte-for-byte. Prior: ADDED 2026-08-22 at
#: 34349629 by the wave-3 twin baseline.
BUDGET = 34349629


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (rewriteK $t $n)
    #    (if (== $n 0)
    #        done
    #        (let* (($_1 (add-atom &self (num (M $t))))
    #               ($_2 (add-atom &self (num (W $t))))
    #               ($_3 (add-atom &self (num (C $t)))))
    #              ((rewriteK (M $t) (- $n 1))
    #               (rewriteK (W $t) (- $n 1))))))
    m += equation(S.rewriteK(V.t, V.n)).to(S["if"](V.n.eq(0),
            S.done,
            S["let*"](((V._1, S["add-atom"](S["&self"], S.num(S.M(V.t)))),
                    (V._2, S["add-atom"](S["&self"], S.num(S.W(V.t)))),
                    (V._3, S["add-atom"](S["&self"], S.num(S.C(V.t))))),
                (S.rewriteK(S.M(V.t), V.n - 1),
                    S.rewriteK(S.W(V.t), V.n - 1)))))

    # (= (mate-space-demo $K)
    #    (let* (($s (add-atom &self (num Z)))
    #           ($g (rewriteK Z $K)))
    #           (match &self (num $1) (num $1))))
    m += equation(S["mate-space-demo"](V.K)).to(
        S["let*"](((V.s, S["add-atom"](S["&self"], S.num(S.Z))),
                (V.g, S.rewriteK(S.Z, V.K))),
            S.match(S["&self"], S.num(V["1"]), S.num(V["1"]))))

    # !(test (length (collapse (mate-space-demo 19))) 1572862)
    yield m.eval(
        S.test(S.length(S.collapse(S["mate-space-demo"](19))),
            1572862)
    )
