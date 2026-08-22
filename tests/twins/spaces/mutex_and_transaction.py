"""The Python twin of examples/spaces/mutex_and_transaction.metta: a mutex and a rollback.

Read-modify-write on `(cnt $x)` is a data race unless the readers and writers
share a mutex, and a transaction undoes the removal when the branch inside it
fails, so the count is unchanged after the rollback.

All three equations are written at the container door, and the reason is the same
one three times over: a compiled body resolves a free name against the engine's
function registry, and `with_mutex`, `transaction`, `add-atom` and `remove-atom`
are out of reach there, the first two because they are not registry functions and
the last two because Python cannot spell a hyphen (residue, P14.4). The shared
increment body is built ONCE as a Python value and reused, which is composition
by naming rather than by copying.

Three forms are declined: the hyperpose race and the two assertions that observe
its result have no point inference budget, which the residue records against
P14.14 with the measurements that decided it.
"""

from petta import S, V, equation, expr

#: The answer group a write form contributes. `add-atom` answers the unit,
#: which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5311 to 5044, -267 (-5.0%), by the P14 twin-style
#: rewrite, and the whole delta is the one live write: `!(add-atom &temp
#: (cnt 37))` now goes through the container door, `temp += (S.cnt, 37)`,
#: inside the 239-to-311 band this folder measures for a plain-atom write.
#: The three
#: equations still enter at the container door and measure identically; naming
#: the shared increment body once stores the same three atoms.
#: Prior: ADDED 2026-08-22 at 5311 by the wave-3 spaces baseline, which already
#: declined forms 1, 2 and 4 for want of a point budget over a hyperpose race.
BUDGET = 5044


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it. A form the
    twin declines yields None and carries a residue entry.
    """
    temp = m.space("&temp")
    add, remove = S["add-atom"], S["remove-atom"]
    here = S[temp.space_name]

    # !(add-atom &temp (cnt 37))
    temp += (S.cnt, 37)
    yield WROTE

    # The read-modify-write every definition below shares.
    #    (match &temp (cnt $x)
    #           ((remove-atom &temp (cnt $x))
    #            (let $inc (+ $x 1) (add-atom &temp (cnt $inc)))))
    increment = S.match(
        here,
        S.cnt(V.x),
        (
            remove(here, S.cnt(V.x)),
            S.let(V.inc, V.x + 1, add(here, S.cnt(V.inc))),
        ),
    )

    # (= (sloppyinc) <increment>)
    m += equation(S.sloppyinc()).to(increment)

    # (= (mutexinc) (with_mutex testmutex <increment>))
    m += equation(S.mutexinc()).to(S.with_mutex(S.testmutex, increment))

    # The transaction's branch ends in (empty), so it fails and the removal is
    # undone.
    # (= (Transaction_rollback_fail_to_inc) (transaction <increment + (empty)>))
    m += equation(S.Transaction_rollback_fail_to_inc()).to(
        S.transaction(
            S.match(
                here,
                S.cnt(V.x),
                (
                    remove(here, S.cnt(V.x)),
                    S.let(V.inc, V.x + 1, add(here, S.cnt(V.inc))),
                    S.empty(),
                ),
            )
        )
    )

    # !(hyperpose ((mutexinc) (mutexinc) (mutexinc) (mutexinc) (mutexinc)))
    yield None

    # !(test (collapse (get-atoms &temp)) ((cnt 42)))
    yield None

    # !(Transaction_rollback_fail_to_inc)
    yield m.eval(S.Transaction_rollback_fail_to_inc())

    # !(test (collapse (get-atoms &temp)) ((cnt 42)))
    yield None
