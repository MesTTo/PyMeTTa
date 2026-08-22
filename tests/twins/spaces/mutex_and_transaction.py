"""examples/spaces/mutex_and_transaction.metta in Python: a counter five threads share.

Read-modify-write on a shared count is a race unless the readers and the
writers agree on a lock, so the example writes the increment three ways: the
sloppy one that would race, the mutex-protected one that does not, and one
wrapped in a transaction whose branch fails, which rolls the removal back.
Five protected increments run at once and 37 becomes 42.

`m.hyperpose(*targets)` is the parallel door under the language's own name, so
running the five branches is one Python call. The three definitions are terms:
each body reads with `match`, writes with hyphenated heads, and the outer two
name `with_mutex` and `transaction`, which are translator forms rather than
registry functions (residue, P14.4). Reading the aftermath is the container
door, `list(space)`.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 5044 to 15511, +10467 (+207.5%), and the whole
#: increase is WORK THAT NOW HAPPENS: the previous twin declined the hyperpose
#: form and both claims after it, so it never ran the five mutex-protected
#: increments at all, and this one does. What moved the other way is small by
#: comparison, two `(test (collapse (get-atoms &temp)) ...)` terms becoming two
#: `assert`s over `list(space)`. Against the example's 28092 the ratio is
#: 0.5521, so performing the declined forms still costs about half of what the
#: original costs.
#: THE ONLY FILE IN THIS FOLDER WHOSE COUNTER IS NOT POINT-DETERMINISTIC:
#: hyperpose schedules five OS threads, so seven fresh processes measured
#: 15510, 15511, 15512 and 15513, a spread of 3 against the lane's own
#: allowance of 4, and the example itself spread 2 over five runs
#: (28092-28094). So the pin is the MIDDLE of the observed range rather than
#: the min, which keeps every observed value inside the allowance from either
#: side [measured 2026-08-22].
#: Prior: 5044, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 15511


def increment(at_temp, *tail):
    """The read-modify-write all three definitions share.

    `(match &temp (cnt $x) ((remove-atom &temp (cnt $x))
                            (let $inc (+ $x 1) (add-atom &temp (cnt $inc)))))`,
    with anything in `tail` appended to the template.
    """
    take = S["remove-atom"](at_temp, S.cnt(V.x))  # rung: an equation body is one term, where the container doors are Python statements
    put = S.let(V.inc, V.x + 1, S["add-atom"](at_temp, S.cnt(V.inc)))  # rung: as above
    return S.match(at_temp, S.cnt(V.x), (take, put, *tail))  # rung: as above


def twin(m):
    """Increment a shared counter five times at once, then roll one back."""
    temp = m.space("&temp")
    at_temp = S[temp.space_name]
    temp += (S.cnt, 37)

    # This only works predictably single-threaded, else there is a data race.
    m += equation(S.sloppyinc()).to(increment(at_temp))
    # The mutex is what makes concurrent increments safe: every place that
    # modifies (cnt $n) takes the same one.
    m += equation(S.mutexinc()).to(S.with_mutex(S.testmutex, increment(at_temp)))
    # A transaction undoes the removal when the branch inside it fails.
    m += equation(S.Transaction_rollback_fail_to_inc()).to(
        S.transaction(increment(at_temp, S.empty()))
    )

    m.hyperpose(*(S.mutexinc() for _ in range(5)))
    assert list(temp) == [S.cnt(42)]

    m.eval(S.Transaction_rollback_fail_to_inc())
    assert list(temp) == [S.cnt(42)]
