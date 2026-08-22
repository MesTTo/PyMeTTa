"""The Python twin of examples/spaces/matchnested.metta: writes from inside a match template.

Two nested matches walk the friend chain, and the inner template writes: it adds
the transitive fact and removes the two links it consumed. `hide` is the file's
device for swallowing the answers, so both write forms answer nothing at all.

The four facts go in through the container protocol, which is where the ceremony
disappears: MeTTa needs an expression of `add-atom` calls and a wrapper to
swallow its answers, while four `m += fact` statements have no answers to
swallow. The nested form below stays a TERM because its writes happen inside a
match template the engine evaluates, and no Python door reaches there.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4672 to 5150, +478 (+10.2%), by the P14 twin-style
#: rewrite, whose two causes pull opposite ways and were split by re-measuring
#: this file with only the decorator change reverted: 3,521, twice.
#: The four opening writes moved from an evaluated expression of (add-atom ...)
#: calls to four `m += fact` statements, worth -1151, which is four writes at
#: the ~265 this folder measures elsewhere plus the wrapper call they no longer
#: need. `(= (hide $1) (empty))` moved to @m.define, worth +1629, the same
#: figure selfprog and spaces2 measure for the first decorated function in a
#: process. Prior: ADDED 2026-08-22 at 4672 by the wave-3 spaces baseline.
BUDGET = 5150


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

    # !(hide (match &self (friend $1 $2)
    #               (match &self (friend $2 $3)
    #                      ((add-atom &self (transitive $1 $2 $3))
    #                       (remove-atom &self (friend $1 $2))
    #                       (remove-atom &self (friend $2 $3))))))
    yield m.eval(
        S.hide(
            S.match(
                here,
                S.friend(V.a, V.b),
                S.match(
                    here,
                    S.friend(V.b, V.c),
                    (
                        add(here, S.transitive(V.a, V.b, V.c)),
                        remove(here, S.friend(V.a, V.b)),
                        remove(here, S.friend(V.b, V.c)),
                    ),
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
