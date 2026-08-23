"""Purpose: examples/spaces/mutex_and_transaction.metta in Python: a counter five threads share.

Read-modify-write on a shared count is a race unless the readers and the
writers agree on a lock, so the example writes the increment three ways: the
sloppy one that would race, the mutex-protected one that does not, and one
wrapped in a transaction whose branch fails, which rolls the removal back.
Five protected increments run at once and 37 becomes 42.

`m.hyperpose(*targets)` is the parallel door under the language's own name, so
running the five branches is one Python call. All three definitions are terms,
and the shared body says why in one place: the outer two name `with_mutex` and
`transaction`, which are translator forms rather than registry functions, so
`is_function` answers False and a compiled body naming either is refused
(residue, P14.4). PERFECT: `with_mutex` and `transaction` join the function
registry, so a `@m.define`d body names them like any other callee.

`sloppyinc` alone would compile, and it stays beside its siblings for a second
gap worth stating. A compiled body refuses a host value, "closing over a host
value would pin it to this process", so the only space spellings inside one are
`fn.context_space()` for the ambient space, a PARAMETER, and `S["&temp"]` as a
symbol; a nullary definition writing into a NAMED space has to take that last
one, which is the spelling the space family rules out. PERFECT: a compiled body
carries a handle the way a term does, since a handle is already a grounded atom.
Until then the three equations read as one body, with one space, at one door.

Reading the aftermath is the container door, `list(space)`.
"""

import metta
from metta import S, V, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships. This file is also the one in its folder whose counter is not
#: point-deterministic, because hyperpose schedules five OS threads; the
#: re-pin pass owns that decision too [assumed 2026-08-23: the number is a
#: placeholder, not a measurement; commit=133aaa81396e8587d496a1e31b78c38741dbd2f4].
BUDGET = 1


def increment(temp, *tail):
    """The read-modify-write all three definitions share.

    `(match &temp (cnt $x) ((remove-atom &temp (cnt $x))
                            (let $inc (+ $x 1) (add-atom &temp (cnt $inc)))))`,
    with anything in `tail` appended to the template.
    """
    take = S["remove-atom"](temp, S.cnt(V.x))  # rung: an equation body is one term, where the container doors are Python statements
    put = S.let(V.inc, V.x + 1, S["add-atom"](temp, S.cnt(V.inc)))  # rung: as above
    return S.match(temp, S.cnt(V.x), (take, put, *tail))  # rung: as above


def twin(m):
    """Increment a shared counter five times at once, then roll one back."""
    temp = metta.space("&temp")
    temp += (S.cnt, 37)

    # This only works predictably single-threaded, else there is a data race.
    m += equation(S.sloppyinc()).to(increment(temp))
    # The mutex is what makes concurrent increments safe: every place that
    # modifies (cnt $n) takes the same one.
    m += equation(S.mutexinc()).to(S["with_mutex"](S.testmutex, increment(temp)))
    # A transaction undoes the removal when the branch inside it fails.
    rollback = S["Transaction_rollback_fail_to_inc"]
    m += equation(rollback()).to(S.transaction(increment(temp, S.empty())))

    m.hyperpose(*(S.mutexinc() for _ in range(5)))
    assert list(temp) == [S.cnt(42)]

    m.eval(rollback())
    assert list(temp) == [S.cnt(42)]
