"""examples/ch17-concurrency-and-the-loop/05-channels_pools_and_the_machine.metta in Python: the rest of lib_thread's MeTTa surface.

`try-recv` answers NOTHING on an empty channel rather than blocking, so an
empty answer list is "nothing was there" and a one-element one is the
message: the same distinction Python already draws between `[]` and `[x]`.

A closed channel is GONE rather than emptied, and the refusal carries the
channel's own number, so the claims read the error's KIND out of it rather
than the number.

`.one()` is what PULLS an effectful call: a `fn` call answers a lazy view, so
a send nobody observes sends nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib
from metta.errors import MettaError


def raised(call, *arguments):
    """The error one call raises, or None where it answered."""
    try:
        list(call(*arguments))
    except MettaError as failure:
        return failure
    return None


def twin(m):
    """Non-blocking receive, closing, pool reports, and the machine."""
    m += lib.thread

    @m.define
    def inc(x: int) -> int:
        # (= (inc $x) (+ $x 1))
        return x + 1

    channel, send = m.fn.channel, m.fn.send
    try_recv, close = m.fn["try-recv"], m.fn["channel-close"]

    # `try-recv` is `recv` without the wait.
    assert try_recv(channel()[0]) == []
    ready = channel()[0]
    send(ready, S.hello).one()
    assert try_recv(ready) == [S.hello]

    # Which makes draining a channel a loop that terminates.
    two = channel()[0]
    send(two, S.one).one()
    send(two, S.two).one()
    assert (try_recv(two), try_recv(two), try_recv(two)) == ([S.one], [S.two], [])

    # `channel-close` closes it, and the channel is GONE.
    assert close(channel()[0]) == [True]
    closed = channel()[0]
    close(closed).one()
    assert "metta_channel" in str(raised(close, closed))
    assert "does not exist" in str(raised(try_recv, closed))

    # `pool-stats` is what a bounded pool reports about itself.
    pool, stats = m.fn.pool, m.fn["pool-stats"]
    pool(S.reporting_pool, 2).one()
    idle = (S.size(2), S.running(0), S.backlog(0), S.free(2))
    assert stats(S.reporting_pool) == [idle]

    # The four are a description of the same two numbers, so running plus
    # free is the size whatever the pool is doing.
    report = stats(S.reporting_pool)[0]
    assert report[1][1].value + report[3][1].value == 2

    # A submitted job answers through the same handle `await` takes, and the
    # pool is idle again once it has been awaited.
    assert m.fn["await"](m.fn.submit(S.reporting_pool, S.inc(9))[0]) == [10]
    assert stats(S.reporting_pool) == [idle]

    # `pool-destroy` frees the workers, and the name is available again.
    assert m.fn["pool-destroy"](S.reporting_pool) == [True]
    pool(S.reporting_pool, 1).one()
    assert stats(S.reporting_pool) == [(S.size(1), S.running(0), S.backlog(0), S.free(1))]
    assert m.fn["pool-destroy"](S.reporting_pool) == [True]

    # `every` is `after`'s repeating twin, and the same `cancel` stops either.
    repeating = m.fn.every(0.05, S.inc(41))[0]
    m.fn.sleep(0.2).one()
    assert m.fn.cancel(repeating) == [True]
    pending = m.fn.every(30, S.inc(41))[0]
    assert m.fn["settled?"](pending) == [False]
    m.fn.cancel(pending).one()

    # The two numbers a pool size is chosen from.
    assert m.fn["cpu-count"]()[0].value > 0
    assert m.fn["thread-count"]()[0].value > 0

    # A thread of the program's own raises the second while it is alive,
    # which is the only claim about it that does not depend on the box.
    before = m.fn["thread-count"]()[0].value
    running = m.fn.spawn(S.sleep(0.2))[0]
    during = m.fn["thread-count"]()[0].value
    m.fn["await"](running).one()
    assert during > before


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 230223..231001 inferences, about 0.965x the example's 238680; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 230630 to 244987 (+14357), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 244987 to 248203 (+3216), the module boundary merged
#: with trunk's later packages (refactor/engine-and-libraries-as-modules at
#: b64291369): every space now resolves through one more chain link, prelude ->
#: metta_engine -> user, the engine's measured export list is imported into the
#: host tier at boot, the closed-sets watch point costs one inference per
#: &metta write, and a cursor opened by a host pays one transaction check at
#: its door; the branch pinned its budgets on its cut, trunk re-pinned the same
#: twins for the packages that landed after that cut, and only the merged tree
#: carries both, so this entry is where the two chains meet [measured
#: 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-PINNED 2026-09-08, 230630 to 232646 (+2016), The typed host door catalog
#: is published before user code. Its declarations change catalog lookup
#: indexes; generated public names bind directly to their existing bodies
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
BUDGET = 232646
#: The count VARIES, because this twin starts threads and timers and the
#: engine charges what the scheduler actually ran. Three single-round
#: measurements on this branch gave 230223, 231001 and 230880, a spread of
#: 778, so the band is the midpoint plus a round 1,500 either side rather
#: than the tree's deterministic 4
#: [measured 2026-09-07: python extensions/python/tools/twin_coverage.py
#: --measure --rounds 1, three times; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
ALLOWANCE = 1500
