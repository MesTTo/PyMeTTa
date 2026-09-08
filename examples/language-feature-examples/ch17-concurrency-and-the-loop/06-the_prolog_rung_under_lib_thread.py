"""examples/ch17-concurrency-and-the-loop/06-the_prolog_rung_under_lib_thread.metta in Python: lib_thread's own lower rung.

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
BUDGET = 405148
#: The count VARIES, because this twin starts threads, pools and timers and
#: the engine charges what the scheduler actually ran. Three single-round
#: measurements on this branch gave 257426, 257768 and 257409, a spread of
#: 359, so the band is the midpoint plus a round 1,500 either side rather
#: than the tree's deterministic 4
#: [measured 2026-09-07: python extensions/python/tools/twin_coverage.py
#: --measure --rounds 1, three times; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
ALLOWANCE = 1500
