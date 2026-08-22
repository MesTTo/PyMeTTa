"""The Python twin of examples/libraries/thread_linda.metta.

Linda's two blocking binds over a MeTTa space: `peek-atom` waits for a matching
atom and LEAVES it (Linda's rd), `take-atom` waits and REMOVES exactly one
(Linda's in). The difference is the coordination model itself, one-to-n against
one-of-n, and both are event-driven through the engine's own write hooks.

`inc` is authored as the Python function it is. Everything else is a term over a
space name, which is what a coordination primitive takes.
"""

from petta import S, V

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 157993 to 159619, +1626 (+1.03%), by the P14
#: twin-style rewrite: inc's equation is now compiled from Python syntax by
#: @m.define instead of added as an already-built atom, and the compile costs
#: 1,626 inferences once. Prior: ADDED 2026-08-22 at 157993 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 159619


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_thread))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_thread)))

    @m.define
    def inc(x):
        # (= (inc $x) (+ $x 1))
        return x + 1

    # A peek leaves the atom, so two peeks answer the same job.
    # !(add-atom &jobs (job 7))
    yield m.eval(S["add-atom"](S["&jobs"], S.job(7)))
    # !(test (peek-atom &jobs (job $n)) (job 7))
    yield m.eval(S.test(S["peek-atom"](S["&jobs"], S.job(V.n)), S.job(7)))
    # !(test (peek-atom &jobs (job $n)) (job 7))
    yield m.eval(S.test(S["peek-atom"](S["&jobs"], S.job(V.n)), S.job(7)))

    # await-atom is the older name for the same thing and stays as sugar.
    # !(test (await-atom &jobs (job $n)) (job 7))
    yield m.eval(S.test(S["await-atom"](S["&jobs"], S.job(V.n)), S.job(7)))

    # A take removes the one it answers, so the second one finds nothing and
    # gives up on its deadline instead of answering the same job twice.
    # !(test (take-atom &jobs (job $n)) (job 7))
    yield m.eval(S.test(S["take-atom"](S["&jobs"], S.job(V.n)), S.job(7)))
    # !(test (collapse (take-atom &jobs (job $n) 0.05)) ())
    yield m.eval(
        S.test(S.collapse(S["take-atom"](S["&jobs"], S.job(V.n), 0.05)), ())
    )
    # !(test (collapse (get-atoms &jobs)) ())
    yield m.eval(S.test(S.collapse(S["get-atoms"](S["&jobs"])), ()))

    # A worker is the point: take a job, do it, take the next. Each take
    # consumes its own job, so two takes drain two.
    # !(add-atom &work (job 1))
    yield m.eval(S["add-atom"](S["&work"], S.job(1)))
    # !(add-atom &work (job 2))
    yield m.eval(S["add-atom"](S["&work"], S.job(2)))
    # !(test (let $x (take-atom &work (job $a) 1)
    #          (let $y (take-atom &work (job $b) 1)
    #            (+ $a $b)))
    #        3)
    yield m.eval(
        S.test(
            S.let(
                V.x,
                S["take-atom"](S["&work"], S.job(V.a), 1),
                S.let(
                    V.y,
                    S["take-atom"](S["&work"], S.job(V.b), 1),
                    V.a + V.b,
                ),
            ),
            3,
        )
    )
    # !(test (collapse (get-atoms &work)) ())
    yield m.eval(S.test(S.collapse(S["get-atoms"](S["&work"])), ()))

    # Blocking means blocking: the take below starts before the atom exists and
    # another thread writes it, which is the rendezvous a channel would
    # otherwise be needed for.
    # !(test (let $w (spawn (add-atom &inbox (msg hello)))
    #          (let $seen (take-atom &inbox (msg $what) 10)
    #            (let $_ (await $w) $seen)))
    #        (msg hello))
    yield m.eval(
        S.test(
            S.let(
                V.w,
                S.spawn(S["add-atom"](S["&inbox"], S.msg(S.hello))),
                S.let(
                    V.seen,
                    S["take-atom"](S["&inbox"], S.msg(V.what), 10),
                    S.let(V._, S["await"](V.w), V.seen),
                ),
            ),
            S.msg(S.hello),
        )
    )
    # !(test (collapse (get-atoms &inbox)) ())
    yield m.eval(S.test(S.collapse(S["get-atoms"](S["&inbox"])), ()))
