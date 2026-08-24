"""Purpose: examples/spaces/mutex_and_transaction.metta in Python: a counter five threads share.

Read-modify-write on a shared count is a race unless the readers and the
writers agree on a lock, so the example writes the increment three ways: the
sloppy one that would race, the mutex-protected one that does not, and one
wrapped in a transaction whose branch fails, which rolls the removal back.
Five protected increments run at once and 37 becomes 42.

`m.hyperpose(*targets)` is the parallel door under the language's own name, so
running the five branches is one Python call, and reading the aftermath is the
container door, `list(space)`.

All three definitions are one body under three wrappers, which is why they are
one Python builder and three writes. The outer two name `with_mutex` and
`transaction`, translator forms rather than registry functions, so `is_function`
answers False and a compiled body naming either is refused (residue, P14.4)
[measured 2026-08-24: `fn.with_mutex` and `fn.transaction` inside a compiled
body are both refused with "names no target function in this space's catalog";
commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. PERFECT: `with_mutex` and `transaction` join the function
registry, so a `@m.define`d body names them like any other callee. `sloppyinc`
alone would compile now, because a compiled body carries a handle the way a
term does; it stays here so that the body the three share is written once.

The exact equation keeps its inner `S.let(...)` at the built-term boundary.
A walrus there is refused with a named `CompileError` because its value would
depend on `$x`, which is bound only by the surrounding match template. The two
translator wrappers remain equation terms because they are not registry
functions.
"""

import metta
from metta import S, V, equation, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships. This file is also the one in its folder whose counter is not
#: point-deterministic, because hyperpose schedules five OS threads; the
#: re-pin pass owns that decision too [assumed 2026-08-24: the number is a
#: placeholder, not a measurement; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1


def twin(m):
    """Increment a shared counter five times at once, then roll one back."""
    temp = metta.space(S.temp)
    temp += (S.cnt, 37)

    def increment(*tail):
        """The read-modify-write all three definitions share.

        `(match &temp (cnt $x) ((remove-atom &temp (cnt $x))
                                (let $inc (+ $x 1) (add-atom &temp (cnt $inc)))))`,
        with anything in `tail` appended to the template.
        """
        take = fn.remove_atom(temp, S.cnt(V.x))
        put = S.let(V.inc, V.x + 1, fn.add_atom(temp, S.cnt(V.inc)))  # rung: the two translator wrappers remain stored equation terms
        return S.match(temp, S.cnt(V.x), (take, put, *tail))  # rung: an equation body is one term, where the container doors are Python statements

    # This only works predictably single-threaded, else there is a data race.
    m += equation(S.sloppyinc()).to(increment())
    # The mutex is what makes concurrent increments safe: every place that
    # modifies (cnt $n) takes the same one.
    m += equation(S.mutexinc()).to(S["with_mutex"](S.testmutex, increment()))
    # A transaction undoes the removal when the branch inside it fails.
    rollback = S["Transaction_rollback_fail_to_inc"]
    m += equation(rollback()).to(S.transaction(increment(S.empty())))

    m.hyperpose(*(S.mutexinc() for _ in range(5)))
    assert list(temp) == [S.cnt(42)]

    m.eval(rollback())
    assert list(temp) == [S.cnt(42)]
