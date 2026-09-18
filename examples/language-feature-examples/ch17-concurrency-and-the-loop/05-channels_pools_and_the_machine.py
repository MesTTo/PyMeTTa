"""Purpose: examples/ch17-concurrency-and-the-loop/05-channels_pools_and_the_machine.metta in Python: the rest of lib_thread's MeTTa surface.

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
from metta._errors.errors import MettaError


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

    # `channel-close` closes it, and the channel is GONE. The example reads
    # the engine's existence_error(metta_channel ...) out of a catch; here the
    # channel is a Python handle, and a handle whose space was dropped is
    # dead, so the seat refuses the second close and the receive at the door,
    # before the engine is asked, naming the drop that ended it.
    assert close(channel()[0]) == [True]
    closed = channel()[0]
    close(closed).one()
    assert "is dead: its space was dropped" in str(raised(close, closed))
    assert "is dead: its space was dropped" in str(raised(try_recv, closed))

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
#: RE-PINNED 2026-09-09, 232646 to 248227 (+15581), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 248227 to 378597 (+130370), channel-close refuses a
#: closed channel again (the door checks known_channel_ before releasing the
#: space, as recv and send do), so the channel example and its twin price
#: rather than fail their claim, and a twin closing a channel pays the check;
#: measured on the merged tree [measured 2026-09-09: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=f75df8e1c17a6c700e8d3700e440fe1ee535ea9f].
#: RE-PINNED 2026-09-08, 248203 to 250569 (+2366), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 250569 to 382738 (+132169), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-09, 382738 to 96314 (-286424), a library's Prolog half
#: compiles beside itself on its first import and loads from the artifact after
#: (metta_load_source/2, seam:compiled_source/1): a twin whose example imports
#: a library with a Prolog half pays the artifact load where both sides paid
#: the source consult and its compile-time expansion in every process,
#: lib_thread's import 278,309 to 5,925 inferences; every import now resolves
#: its spec and asks the boot's claim, about 180 inferences an import, and the
#: boot's content moved (the door, the seam and the three library imports the
#: tokens, receipts and seed units gained), which shifts clause layout by tens;
#: measured on this tree with the artifacts warm [measured 2026-09-09: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-OBSERVED 2026-09-09 after a library's Prolog half compiles beside itself
#: on its first import (metta_load_source/2, seam:compiled_source/1), POOLED
#: over every full-lane sample on this tree: two --observe runs of ten rounds
#: and 4 plain lane runs read 96306..96786 (spread 480) over 23 observations,
#: replacing the earlier envelope of the tree before this one. Its count is the
#: scheduler's, it drives lib_thread's pools and channels, so the envelope is
#: exact extrema and a run outside it is a re-observation under --observe, not
#: a re-pin; 1 round of 20 failed its claim with an AssertionError under the
#: same load, an intermittent of its own recorded in the journal and not a cost
#: [measured 2026-09-09: python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10, twice, beside the plain lane runs ai-tmp records;
#: fixture=full-lane/277/workers=32; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: POOLED 2026-09-09: published 96306..96786 over 23
#: observations, receipt pass 98691..98994 over 10, and
#: final pass 98687..99039 over 10. Exact extrema and counts
#: retain the existing empirical protocol; no point budget becomes an envelope.
#: [measured: two complete ten-round passes; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: RE-OBSERVED 2026-09-10 after setting the file-search cache lifetime
#: before engine creation. This complete ten-round population uses
#: 98683..98799 over 10 observations. Earlier protocol
#: samples remain above as history and do not enter this envelope.
#: [measured: all 277 pairs, this twin succeeds in every round; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: POOLED 2026-09-10: the earlier before-boot population has 98683..98799 over
#: ten samples; the receipt-frame repair's complete population has 98679..98732
#: over ten. The full lanes at 17bec75f1 and e70deddaa add 98683 and 98683.
#: Their exact pooled extrema are 98679..98799 over 22 observations under the
#: same cache-normalised protocol. Earlier runtime samples remain identified
#: separately; the receipt watcher now transfers ownership at live completion.
#: No point becomes an envelope. The final gate is an independent validation
#: sample [measured 2026-09-10: two complete ten-round populations and two full
#: lane checks; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and sh check.sh twins; fixture=full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: the retained 22 observations have 98679..98799. The full
#: lane at 71535ae17 adds 99219; a further complete ten-round population at
#: db8640733 adds 98683..98732. All 2770 new samples succeed. Exact pooled
#: extrema are 98679..99219 over 33 observations under the same before-boot
#: cache protocol. For the channels-and-pools twin, line and worker controls
#: attribute a variable cancellation cost to work already performed by the
#: timer worker before the join; those instrumented controls do not enter this
#: population. No point becomes an envelope [measured 2026-09-10: three
#: complete ten-round populations and three full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: retain the previous33 observations and both full-gate
#: samples (3fb950149: 98683; 503e21f8a: 98683), then append the complete ten-
#: round populations (2f1be07e9: 98679..99134; e93f2028d: 98697..98735). Both
#: populations have2770 successful samples, no failures and no point movements
#: or excursions. The e93f2028d population measures the repaired concurrent
#: join; the2f1be07e9 observation retains its own version. Exact pooled extrema
#: are98679..99219 over55 samples, without padding. No point becomes an
#: envelope. [measured 2026-09-10: five complete ten-round populations and five
#: full-lane readings; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and sh check.sh twins; fixture=full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-11: keep all 55 previous observations, append the two
#: complete gate readings (895878bbe=98707, 4d4fa2c55=98696), then all ten
#: qualified 4d4fa2c55 rounds (98696..98882). The resulting 67 observations
#: have exact extrema 98679..99219. The prior scheduling mechanisms remain;
#: this complete lane also measures the explicit pending-definition provider.
#: No targeted or instrumented reading enters an envelope. The end-of-wave
#: battery re-observes and re-pins the whole lane on the merged tree under this
#: protocol, pooling every empirical extension with its count and mechanism.
#: [measured 2026-09-11: six complete ten-round populations and seven full-lane
#: readings; command=python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10 and sh check.sh twins; fixture=full-lane/277/workers=32/file-
#: search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-OBSERVED 2026-09-18 under 'full-lane/293/workers=32', 98679..99219 over
#: 67 under 'full-lane/277/workers=32' to 121854..122463 over 10: the branch's
#: tip f06186a96 after the landings the point re-pin names (the compiled call
#: law, the one codec at the grounded call, the runnable cache's dependency
#: index written by the producer, the host patches of 09-17, the class units)
#: and a corpus of 293 twinned examples under the lane's 32-worker pool, so the
#: scheduler this counter answers to is a new one and the observations are this
#: tree's own rather than pooled with the earlier protocol's [measured
#: 2026-09-18: python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10, wt-battery-6 ai-tmp/ai-observe-f06186a96.log; commit=WORKTREE].
BUDGET = {
    "minimum": 121854,
    "maximum": 122463,
    "observations": 10,
    "protocol": "full-lane/293/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
#: The count VARIES, because this twin starts threads and timers and the
#: engine charges what the scheduler actually ran. Three single-round
#: measurements on this branch gave 230223, 231001 and 230880, a spread of
#: 778, so the band is the midpoint plus a round 1,500 either side rather
#: than the tree's deterministic 4
#: [measured 2026-09-07: python extensions/python/tools/twin_coverage.py
#: --measure --rounds 1, three times; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
ALLOWANCE = 1500
