"""Purpose: examples/ch17-concurrency-and-the-loop/06-the_prolog_rung_under_lib_thread.metta in Python: lib_thread's own lower rung.

Every operation the two files before this one use is one equation over a
Prolog predicate imported by name, and these underscore spellings are those
predicates. Every one keeps its underscore, so every one comes through the
exact subscript door.

Two of them have no MeTTa-named wrapper at all, `space_await_where` and
`space_take_where`, and the reason is in the argument list: a guard and a
seconds deadline would both sit third.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, V, lib


def twin(m):
    """The five maps, the futures, channels, pools, timers, locks and Linda."""
    m += lib.thread
    f = m.fn

    @m.define
    def inc(x: int) -> int:
        # (= (inc $x) (+ $x 1))
        return x + 1

    @m.define(name="big?")
    def big(x: int) -> bool:
        # (= (big? $x) (> $x 2))
        return x > 2

    # The five parallel maps over a list.
    assert f["par_map"](S.inc, (1, 2, 3)) == [(2, 3, 4)]
    assert f["par_filter"](S["big?"], (1, 2, 3, 4)) == [(3, 4)]
    assert f["par_forall"](S["big?"], (3, 4)) == [True]
    assert f["par_forall"](S["big?"], (1, 4)) == [False]
    assert f["par_any"](S["big?"], (1, 9)) == [True]
    assert f["par_any"](S["big?"], (1, 2)) == [False]
    assert f["par_map"](S.inc, (1, 2, 3)) == f["par-map"](S.inc, (1, 2, 3))

    # `par_race` HOLDS its argument, so the branches are started rather than
    # computed and handed over.
    assert f["par_race"]((S.inc(41), S.inc(41))) == [42]

    # Futures.
    assert f["thread_await"](f["thread_spawn"](S.inc(41))[0]) == [42]
    settled = f["thread_spawn"](S.inc(41))[0]
    f["thread_await"](settled).one()
    assert f["thread_settled"](settled) == [True]
    slow = f["thread_spawn"](S.sleep(30))[0]
    # PULLED before the cancel, not after: a `fn` call answers a lazy view,
    # so comparing it later would ask about a thread that has already been
    # stopped and answer True.
    running = f["thread_settled"](slow).one()
    f["thread_cancel"](slow).one()
    assert running is False

    # Channels.
    mailbox = f["channel_new"]()[0]
    f["channel_send"](mailbox, S.hi).one()
    assert f["channel_recv"](mailbox) == [S.hi]
    sized = f["channel_new"]()[0]
    f["channel_send"](sized, S.hi).one()
    assert f["channel_size"](sized) == [1]
    assert f["channel_try_recv"](f["channel_new"]()[0]) == []
    waiting = f["channel_new"]()[0]
    f["channel_send"](waiting, S.hi).one()
    assert f["channel_try_recv"](waiting) == [S.hi]
    assert f["channel_close"](f["channel_new"]()[0]) == [True]

    # Pools.
    f["pool_create"](S.rung_pool, 2).one()
    assert f["thread_await"](f["pool_submit"](S.rung_pool, S.inc(9))[0]) == [10]
    assert f["pool_stats"](S.rung_pool) == [
        (S.size(2), S.running(0), S.backlog(0), S.free(2))
    ]
    assert f["pool_destroy"](S.rung_pool) == [True]

    # Timers are futures that start later, so the same await and cancel serve
    # them.
    assert f["thread_await"](f["timer_after"](0.05, S.inc(41))[0]) == [42]
    repeating = f["timer_every"](0.05, S.inc(41))[0]
    f.sleep(0.2).one()
    assert f["thread_cancel"](repeating) == [True]

    # `with_lock` keeps EVERY answer where SWI's own with_mutex is once/1.
    assert f["with_lock"](S.rung_lock, S.superpose((1, 2, 3))) == [1, 2, 3]

    # The Linda pair: one waits and LEAVES, the other waits and removes.
    jobs = m.metta.space(S.rung_jobs)
    jobs += S.job(7)
    assert f["space_await"](jobs, S.job(V.n)) == [S.job(7)]
    assert f["space_await"](jobs, S.job(V.n)) == [S.job(7)]
    assert f["space_take"](jobs, S.job(V.n)) == [S.job(7)]
    assert not jobs[V.any]

    # The same two with match's where-guard, evaluated once a candidate binds
    # the pattern's variables.
    work = m.metta.space(S.rung_work)
    work += [S.job(2), S.job(9)]
    above_five = S[">"](V.n, 5)
    assert f["space_await_where"](work, S.job(V.n), above_five) == [S.job(9)]
    assert f["space_take_where"](work, S.job(V.n), above_five) == [S.job(9)]
    assert [row.n for row in work[S.job(V.n)]] == [2]

    # A guard that rejects everything waits out its deadline and answers
    # nothing, and the candidates it rejected are still there.
    above_hundred = S[">"](V.n, 100)
    assert f["space_take_where"](work, S.job(V.n), above_hundred, 0.05) == []
    assert [row.n for row in work[S.job(V.n)]] == [2]

    # The two machine numbers, and the MeTTa names over them.
    assert f["cpu_count"]()[0].value > 0
    assert f["thread_count"]()[0].value > 0
    assert f["cpu_count"]() == f["cpu-count"]()
    assert f["thread_count"]() == f["thread-count"]()


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 257409..257768 inferences, about 0.983x the example's 262,000; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 257600 to 272705 (+15105), The engine and library
#: predicates now resolve through their owning modules and the explicit engine
#: facade; compiled program lookup crosses the added metta_engine tier
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=ede2ac57e213a0d4502c6bbbca6227f97015b720].
#: RE-PINNED 2026-09-08, 272705 to 276317 (+3612), the module boundary merged
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
#: RE-PINNED 2026-09-08, 257600 to 260711 (+3111), The typed host door catalog
#: is published before user code. Its declarations change catalog lookup
#: indexes; generated public names bind directly to their existing bodies
#: extensions/python/tools/twin_coverage.py --repin; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-PINNED 2026-09-09, 260711 to 276286 (+15575), the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved, which shifts a twin count by tens; measured
#: on the merged tree [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: RE-PINNED 2026-09-09, 276286 to 405148 (+128862), structured concurrency
#: landed (feat/structured-concurrency merged at f80cc416d): every space mint
#: records its allocation in the library's lifetime rows, every write and run
#: pays the ownership hook and every drop asks the library whether a scope owns
#: the name, measured on a pristine control as 32 per mint, 2 per write and 44
#: per drop with none per read; measured on the merged tree [measured
#: 2026-09-09: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=0f53926c2fd9f28e188814c84253ad82e13258f7].
#: RE-PINNED 2026-09-08, 276317 to 278452 (+2135), Trailing occurrence
#: arguments, token allocation in native writes, exact source withdrawal and
#: transaction-safe shared-table guards change the engine work priced by this
#: twin; answer bags retain the upstream law [measured 2026-09-08: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=7f00ac7932fefa6f380fc8d14ec583ea0c58eff4].
#: RE-PINNED 2026-09-09, 278452 to 409097 (+130645), tokens as storage landed
#: (feat/tokens-as-storage merged): every native occurrence carries a (t actor
#: generation) token as the trailing argument of its storage clause, minted
#: through flag/3 at the write funnel, and every clause read decodes it,
#: measured on a pristine control of trunk cbf7a958d as 8 more inferences per
#: add, 31 more per remove, 4 more per atom saved and 54 more per atom loaded
#: from a fast image, none per match, plus the merged tree's own lib_thread
#: repairs; measured on the merged tree [measured 2026-09-09: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=50e34286f66c938d89d5d367c6370ad44164c97f].
#: RE-PINNED 2026-09-09, 409097 to 122527 (-286570), a library's Prolog half
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
#: and 4 plain lane runs read 121278..123532 (spread 2254) over 24
#: observations, replacing the earlier envelope of the tree before this one.
#: Its count is the scheduler's, it drives lib_thread's pools from the Prolog
#: rung, so the envelope is exact extrema and a run outside it is a re-
#: observation under --observe, not a re-pin [measured 2026-09-09: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, twice,
#: beside the plain lane runs ai-tmp records; fixture=full-lane/277/workers=32;
#: commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: POOLED 2026-09-09: published 121278..123532 over 24
#: observations, receipt pass 123486..125063 over 10, and
#: final pass 124058..125026 over 10. Exact extrema and counts
#: retain the existing empirical protocol; no point budget becomes an envelope.
#: [measured: two complete ten-round passes; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: RE-OBSERVED 2026-09-10 after setting the file-search cache lifetime
#: before engine creation. This complete ten-round population uses
#: 123491..125050 over 10 observations. Earlier protocol
#: samples remain above as history and do not enter this envelope.
#: [measured: all 277 pairs, this twin succeeds in every round; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: POOLED 2026-09-10: the earlier before-boot population has 123491..125050
#: over ten samples; the receipt-frame repair's complete population has
#: 123910..124910 over ten. The full lanes at 17bec75f1 and e70deddaa add
#: 124207 and 124767. Their exact pooled extrema are 123491..125050 over 22
#: observations under the same cache-normalised protocol. Earlier runtime
#: samples remain identified separately; the receipt watcher now transfers
#: ownership at live completion. No point becomes an envelope. The final gate
#: is an independent validation sample [measured 2026-09-10: two complete ten-
#: round populations and two full lane checks; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: the retained 22 observations have 123491..125050. The
#: full lane at 71535ae17 adds 124748; a further complete ten-round population
#: at db8640733 adds 123976..124801. All 2770 new samples succeed. Exact pooled
#: extrema are 123491..125050 over 33 observations under the same before-boot
#: cache protocol. No point becomes an envelope [measured 2026-09-10: three
#: complete ten-round populations and three full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: retain the previous33 observations and both full-gate
#: samples (3fb950149: 124120; 503e21f8a: 123450), then append the complete
#: ten-round populations (2f1be07e9: 124068..125719; e93f2028d:
#: 123911..125001). Both populations have2770 successful samples, no failures
#: and no point movements or excursions. The e93f2028d population measures the
#: repaired concurrent join; the2f1be07e9 observation retains its own version.
#: Exact pooled extrema are123450..125719 over55 samples, without padding.
#: Cancelled worker work explains the thread_lib and rung schedule spread;
#: instrumented line and worker controls never enter the population. No point
#: becomes an envelope. [measured 2026-09-10: five complete ten-round
#: populations and five full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-11: keep all 55 previous observations, append the two
#: complete gate readings (895878bbe=124056, 4d4fa2c55=125412), then all ten
#: qualified 4d4fa2c55 rounds (124068..124738). The resulting 67 observations
#: have exact extrema 123450..125719. The prior scheduling mechanisms remain;
#: this complete lane also measures the explicit pending-definition provider.
#: No targeted or instrumented reading enters an envelope. The end-of-wave
#: battery re-observes and re-pins the whole lane on the merged tree under this
#: protocol, pooling every empirical extension with its count and mechanism.
#: [measured 2026-09-11: six complete ten-round populations and seven full-lane
#: readings; command=python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10 and sh check.sh twins; fixture=full-lane/277/workers=32/file-
#: search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
BUDGET = {
    "minimum": 123450,
    "maximum": 125719,
    "observations": 67,
    "protocol": "full-lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
#: The count VARIES, because this twin starts threads, pools and timers and
#: the engine charges what the scheduler actually ran. Three single-round
#: measurements on this branch gave 257426, 257768 and 257409, a spread of
#: 359, so the band is the midpoint plus a round 1,500 either side rather
#: than the tree's deterministic 4
#: [measured 2026-09-07: python extensions/python/tools/twin_coverage.py
#: --measure --rounds 1, three times; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
ALLOWANCE = 1500
