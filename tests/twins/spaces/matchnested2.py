"""The Python twin of examples/spaces/matchnested2.metta: the conjunction does the nesting.

Same walk as matchnested, written as one conjunctive match instead of two nested
ones: `(, (friend $a $b) (friend $b $c))` joins on the shared variable, and the
template writes the transitive fact and removes both links.

The four facts go in through the container protocol, where MeTTa needs an
expression of `add-atom` calls and a wrapper to swallow their answers. The
conjunctive form stays a TERM because its writes happen inside a match template
the engine evaluates, and no Python door reaches there.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4670 to 5148, +478 (+10.2%), by the P14 twin-style
#: rewrite, whose two causes move this file by exactly what they move
#: matchnested by, which is the check that the split is real: the four opening
#: writes moved to `m += fact` statements, -1151, and `(= (hide $1) (empty))`
#: moved to @m.define, +1629 for the first decorated function in a process.
#: Prior: ADDED 2026-08-22 at 4670 by the wave-3 spaces baseline.
BUDGET = 5148


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    add, remove, here = S["add-atom"], S["remove-atom"], S[m.space_name]

    # (= (hide $1) (empty))
    @m.define
    def hide(_x):
        return empty()  # noqa: F821  -- `empty` is one of the compiled subset's magic names; MeTTa's "no answer" has no Python value to bind

    # !(hide ((add-atom &self (friend tim tom))
    #         (add-atom &self (friend tom tam))
    #         (add-atom &self (friend sim som))
    #         (add-atom &self (friend som sam))))
    m += (S.friend, S.tim, S.tom)
    m += (S.friend, S.tom, S.tam)
    m += (S.friend, S.sim, S.som)
    m += (S.friend, S.som, S.sam)
    yield []

    # !(hide (match &self (, (friend $1 $2) (friend $2 $3))
    #                     ((add-atom &self (transitive $1 $2 $3))
    #                      (remove-atom &self (friend $1 $2))
    #                      (remove-atom &self (friend $2 $3)))))
    yield m.eval(
        S.hide(
            S.match(
                here,
                S[","](S.friend(V.a, V.b), S.friend(V.b, V.c)),
                (
                    add(here, S.transitive(V.a, V.b, V.c)),
                    remove(here, S.friend(V.a, V.b)),
                    remove(here, S.friend(V.b, V.c)),
                ),
            )
        )
    )

    # !(test (msort (collapse (match &self (transitive $1 $2 $3) (transitive $1 $2 $3))))
    #        ((transitive sim som sam) (transitive tim tom tam)))
    yield m.eval(
        S.test(
            S.msort(
                S.collapse(
                    S.match(
                        here,
                        S.transitive(V.a, V.b, V.c),
                        S.transitive(V.a, V.b, V.c),
                    )
                )
            ),
            (
                S.transitive(S.sim, S.som, S.sam),
                S.transitive(S.tim, S.tom, S.tam),
            ),
        )
    )
