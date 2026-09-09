"""Purpose: examples/ch17-concurrency-and-the-loop/01-thread_lib.metta in Python: concurrency through lib_thread.

Twenty-seven claims across parallel collections, races, futures, timers,
channels, bounded pools, locks and time bounds. Four of those cells have a
package function and take it, `par_map`, `race`, `spawn` and `channel`, and a
spawned future carries `wait`, `settled` and `cancel` as methods, so
`spawn(S.inc(41)).wait()` is the example's `(await (spawn ...))`.

The rest of lib_thread has no Python door yet and descends one rung to the
function namespace, which is where the ladder is visible in this file: the
`par_filter`/`par_forall`/`par_any` siblings of `par_map`, the one-shot timer
`after` and the `await`/`cancel`/`settled?` verbs its bare handle needs (the
package's timer is `every`, which repeats and is a different program), the
bounded `pool`, the two locks and lib_thread's own `timeout`. That last one is
not `m.limits(timeout=)`: the with-block bounds the engine's own call, while
`(timeout 10 X)` runs X under a wall clock and KEEPS every answer, which is
the claim beside `with_mutex` here.

All four MeTTa definitions are compiled. `spin` answers the lowercase symbol
`done`, which the `S` factory says inside a body, and `slow` discards a call
before returning, which an assignment to `_` says: both are exactly what
`(let $_ ... $x)` means.

`with_mutex` keeps the bracket at the function namespace, because that MeTTa
name really has an underscore and the attribute door maps every underscore to
a hyphen; `with-lock` beside it is the ordinary hyphenated name and takes the
attribute.

The rendezvous at the end waits with the handle's own verb, `m.peek(...)`,
Linda's rd: it answers the ONE atom it waited for rather than a binding row.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import time

from metta import Expression, S, V, channel, lib, race, spawn


def twin(m):
    """Run parallel collections, futures, timers, channels, pools, and locks."""
    m += lib.thread

    @m.define
    def inc(x: int) -> int:
        # (= (inc $x) (+ $x 1))
        return x + 1

    @m.define(name="big?")
    def big(x: int) -> bool:
        # (= (big? $x) (> $x 2))
        return x > 2

    @m.define
    def spin(n: int):
        # (= (spin $n) (if (> $n 0) (spin (- $n 1)) done))
        return spin(n - 1) if n > 0 else S.done

    @m.define
    def slow(x):
        # (= (slow $x) (let $_ (spin 300000) $x))
        _ = spin(300000)
        return x

    # par-map preserves the input list's order however the elements finish.
    # The BOUND namespace evaluates in this space, where inc lives; the
    # module-level par_map is the default context's verb.
    assert m.fn.par_map(S.inc, Expression((1, 2, 3, 4))) == [Expression((2, 3, 4, 5))]
    assert m.fn.par_map(S.inc, Expression(())) == [Expression(())]
    assert m.fn.par_filter(S["big?"], (1, 2, 3, 4, 5)) == [Expression((3, 4, 5))]
    assert m.fn.par_forall(S["big?"], (3, 4, 5)) == [True]
    assert m.fn.par_forall(S["big?"], (1, 4, 5)) == [False]

    # par-any stops at the first element that holds, and answers True even
    # though the elements before it fail.
    assert m.fn.par_any(S["big?"], (1, 2, 9)) == [True]
    assert m.fn.par_any(S["big?"], (1, 2)) == [False]

    # The module-level parallel verbs read the AMBIENT space, and entering
    # a space scopes it, so the block below runs where inc and slow live.
    with m:
        # The fast branch wins and the slow one is stopped, so this returns
        # without waiting for (slow 1). A branch that fails drops out rather
        # than ending the race.
        assert race(S.slow(1), S.inc(41)) == 42
        assert race(S.superpose(()), S.inc(41)) == 42

        # A future evaluates on its own thread; wait() waits for it. Two of
        # them overlap, which is the whole point.
        assert list(spawn(S.inc(41)).wait()) == [42]

        first, second = spawn(S.slow(1)), spawn(S.slow(2))
        assert first.wait().one() + second.wait().one() == 3

        # Waiting twice answers the same thing without waiting again.
        twice = spawn(S.inc(1))
        twice.wait()
        assert list(twice.wait()) == [2]

        # A future IS a space, so it holds the expression's whole ANSWER SET
        # rather than just the first answer.
        assert list(spawn(S.superpose((1, 2, 3))).wait()) == [1, 2, 3]
        assert list(spawn(S.superpose(())).wait()) == []
        assert m.fn.is_space(spawn(S.inc(1))) == [True]

        # Being a space, it reads back with the ordinary space operations too.
        settled_future = spawn(S.inc(41))
        settled_future.wait()
        assert list(settled_future) == [42]

    # Timers are futures that start later, so (after ...) is setTimeout and
    # there is no separate clearTimeout: the same cancel that stops a spawn
    # stops a timer. A pending timer is simply not settled yet.
    after, cancel = m.fn.after, m.fn.cancel
    settled = m.fn["settled?"]
    await_ = m.fn["await"]

    assert list(await_(after(0.05, S.inc(41)))) == [42]

    timer = after(30, S.inc(41)).one()
    was_settled = settled(timer).one()
    cancel(timer).one()
    assert was_settled is False

    timer = after(0.05, S.inc(41)).one()
    cancel(timer).one()
    time.sleep(0.25)
    assert list(timer) == []

    # A channel is a mailbox. The term is copied across, so the receiver gets
    # its own copy and no binding crosses.
    mailbox = channel()
    mailbox.send(S.hello)
    assert mailbox.recv() == S.hello

    queued = channel()
    queued.send(S.one)
    assert len(queued) == 1

    # A pool bounds the fan-out; submit answers the same handle await takes.
    m.fn.pool(S.demo_pool, 2).one()
    assert await_(m.fn.submit(S.demo_pool, S.inc(9))) == [10]

    # Blocking until another thread writes the atom, event-driven through the
    # engine's own write hooks. The spawned branch does the writing.
    writer = spawn(
        S.add_atom(m, S.ready(S.now))
    )  # rung: the write is DATA handed to another engine thread, not a store this process mutates, so `space += atom` cannot say it
    seen = m.peek(S.ready(V.what), deadline=10)
    writer.wait()
    assert seen == S.ready(S.now)

    # with-lock keeps every answer. SWI's with_mutex, which the built-in form
    # uses, is once/1 and would answer (1) here. Bounding by wall clock keeps
    # them too, unlike a bare call_with_time_limit.
    values = S.superpose((1, 2, 3))
    assert list(m.fn.with_lock(S.demo_lock, values)) == [1, 2, 3]
    assert list(m.fn["with_mutex"](S.demo_lock, values)) == [1]
    assert list(m.fn.timeout(10, values)) == [1, 2, 3]
    assert m.fn.timeout(10, S.inc(41)) == [42]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 1,248,269 inferences over the concurrent lane's own observations, because
#: the spin loop that proves a race really races is cut wherever the winning
#: branch happens to be
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 252593 to 254352, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 254352 to 254061, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 254061 to 254019, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 9
#: full-lane observations under 'full-lane/218/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: ENVELOPED 2026-08-25 by the observe pass: this twin's count is
#: intrinsically multi-valued (allocation-timing jitter moves GC
#: work between runs; ten serial runs of one such twin answered six
#: distinct counts), so a point pin with the +-4 tolerance is a
#: false claim here. Bounds are the exact extrema of 10
#: full-lane observations under 'full-lane/219/workers=32'; a cost outside them
#: is a real finding, and a new mode discovered later extends the
#: envelope with its observation count rather than widening blind.
#: RE-ENVELOPED 2026-09-01 on the operator-protocol tree. Generic Python
#: operators now dispatch through live protocols and relational twins name
#: engine heads explicitly, so ten fresh full-lane observations replace the
#: prior implementation's modes [measured: exact extrema over 10 observations;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/219/workers=32; commit=e3787593132a7ece2d300397045f7415709847c9].
#: The confirming differential extended the observed maximum from 591824 to
#: 608009 [measured: eleventh full-lane observation 608009; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: A second ten-round observe pass extended the maximum from 608009 to 608164
#: [measured: exact extrema over 10 further observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/219/workers=32; commit=e3787593132a7ece2d300397045f7415709847c9].
#: Four confirming differentials brought the current-tree sample to 25; the
#: third extended the maximum from 608164 to 618693 [measured: twenty-fourth
#: full-lane observation 618693 and twenty-fifth observation 617737; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-ENVELOPED 2026-09-02 after exact numeric annotations restored native
#: operator heads and published their MeTTa declarations. The prior
#: protocol-path modes describe another implementation, so ten fresh
#: full-lane observations replace them [measured: exact extrema over 10
#: observations; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10; fixture=full-lane/219/workers=32; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-ENVELOPED 2026-09-02 after static contract discharge made retained
#: translation policy-stable. The translation work changes this concurrent
#: twin's modes, so 25 fresh full-lane observations replace the prior
#: implementation's envelope [measured: minimum 542509, maximum 571598 over
#: 25 observations; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 25; fixture=full-lane/219/workers=32; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-ENVELOPED 2026-09-02 after policy checks were confined to invalidated
#: generated contracts. Twenty-five fresh full-lane observations replace the
#: broader intermediate implementation's modes [measured: minimum 542462,
#: maximum 575145 over 25 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 25;
#: fixture=full-lane/219/workers=32; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-ENVELOPED 2026-09-02 after the two generated policy-check fallbacks
#: joined the protected engine-emitted surface. Twenty-five fresh full-lane
#: observations replace the pre-protection bounds [measured: minimum 543027,
#: maximum 603919 over 25 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 25;
#: fixture=full-lane/219/workers=32; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: ENVELOPE 2026-09-08, 554438..770008 over 37 observations of 'full-
#: lane/231/workers=32': twenty-seven claims over parallel collections, races,
#: futures, timers, channels and bounded pools, and the loser of a race spends
#: however many of its 300,000 spin inferences it reached before the winner
#: finished; a point pin on it is a claim about a schedule and not about
#: this twin. Spread 215570 [measured 2026-09-08: `python
#: extensions/python/tools/twin_coverage.py --observe`, two runs of 12 and 25
#: rounds pooled; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because the every-atom merge widened
#: the corpus from 231 to 277 twinned examples and the scheduler this counter
#: answers to is the lane's own 32-worker pool over that corpus: 25 observations
#: pooled from two `--observe` runs of 10 and 15 rounds read 554467..583831 where the
#: 37 under 'full-lane/231/workers=32' read 554438..770008. A run outside this envelope is a
#: re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/mergeTW-observe-10.log and -15.log; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32', 552258..583831
#: over 51 observations to 589444..618249 over 26: the module boundary merged
#: with trunk (refactor/engine-and-libraries-as-modules at b64291369): the
#: twin's host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine. The
#: observations are this tree's own rather than pooled with the earlier ones,
#: because pooling would mix two boot images and the spread an envelope states
#: is a claim about ONE; ten rounds, then fifteen, plus the gate's own
#: readings between them, all under the same protocol on the same tree
#: [measured 2026-09-08: python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/merged68-observe-10.log and
#: merged68-observe-15.log; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32' and POOLED: this twin races two
#: `slow` branches whose loser is cut wherever the winner lands, so its count is the
#: scheduler's and not the engine's, and an envelope over it is a claim about how far
#: a losing spin gets on a loaded box. The trailed fuel scope (fix/every-intermittent-
#: root-caused, f6e05ca9) made each spin step cheaper, and the extension-package merge's
#: gate read 552971 under the 25 observations' floor of 554467; twenty-five fresh
#: full-lane rounds read 552258..573907 and the gate after them read 580293, inside the
#: earlier top. The union keeps that top as evidence, because the ceiling is set by load
#: and not by the engine: 51 observations read 552258..583831. A run outside it is a
#: re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 25,
#: ai-tmp/integrator-849a9e/mergeEXT-observe-25.log and mergeEXT-twins3.log; commit=4e0feaf6b8eb13cd17232f6e7d58679b6e22f2b9].
#: RE-OBSERVED 2026-09-08 after typed host doors joined the boot catalog.
#: Ten complete rounds observed 557650..596814. The race's losing branch
#: still contributes the work its schedule permits; these observations replace
#: the earlier catalog's envelope rather than pooling different boot states
#: [measured: exact extrema over 10 successful observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-OBSERVED 2026-09-09 after a library's Prolog half compiles beside itself
#: on its first import (metta_load_source/2, seam:compiled_source/1), POOLED
#: over every full-lane sample on this tree: two --observe runs of ten rounds
#: and 4 plain lane runs read 282220..313661 (spread 31441) over 24
#: observations, replacing the earlier envelope of the tree before this one.
#: Its count is the scheduler's, it races two `slow` branches whose loser is
#: cut wherever the winner lands, so the envelope is exact extrema and a run
#: outside it is a re-observation under --observe, not a re-pin [measured
#: 2026-09-09: python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10, twice, beside the plain lane runs ai-tmp records; fixture=full-
#: lane/277/workers=32; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-OBSERVED 2026-09-10 after fused syntax admission and shape compilation.
#: Ten complete-lane rounds supplied 10 successful observations under
#: full-lane/279/workers=32.
#: Samples: [284796, 288232, 291338, 302095, 283715, 291718, 298353, 292027, 291926, 293763].
#: Bounds are the observed extrema, with no added margin
#: [measured 2026-09-10: minimum 283715, maximum 302095;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/279/workers=32; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
#: RE-OBSERVED 2026-09-10 after the next complete lane exposed a new
#: channels/pools minimum. Two exact --observe --rounds 10 runs and
#: all three other final-code complete-lane receipts are pooled under
#: full-lane/279/workers=32: 23 successful costs and 0 failed observations.
#: Failed observations contribute no cost; no margin is added.
#: Samples: [284796, 288232, 291338, 302095, 283715, 291718, 298353, 292027, 291926, 293763, 308749, 344675, 299801, 284641, 297190, 302895, 291382, 292075, 290456, 285323, 298929, 292126, 286183].
#: [measured 2026-09-10: minimum 283715, maximum 344675;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/279/workers=32, two observation runs and three plain lane receipts;
#: commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
BUDGET = {
    "minimum": 283715,
    "maximum": 344675,
    "observations": 23,
    "protocol": "full-lane/279/workers=32",
}

#: OVERRUN 2026-09-07, 251100: it spins 300,000 inferences where the example
#: sleeps for a second, because a twin is priced by a counter and a sleep costs
#: nothing to count. Measured 561710 against a ceiling of 310696; a minimal
#: twin of this example costs 283393, inside the ceiling's 310696, so the
#: distance is this twin's own program [measured 2026-09-07: one fresh process
#: per side; command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-08, 460000, RE-DERIVED from the envelope above rather than
#: from one run: this twin's count is what a race schedule leaves, and the 37
#: pooled observations top out at 770,008 against a ceiling of 310,896 (the
#: example's own cheapest of three runs, 276,664, plus its 10% and the 6,598
#: four compiled definitions cost to author). 460,000 covers that top with
#: 149,112 to spare, and it hides nothing: BUDGET is the envelope and a run
#: outside it is red whatever this says [measured 2026-09-08: `python
#: extensions/python/tools/twin_coverage.py --observe`, two runs of 12 and 25
#: rounds pooled, beside three fresh-process runs of the example;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-09, 460000 to 159568 (-300432), RE-DERIVED from the pooled
#: envelope above after a library's Prolog half compiles beside itself on its
#: first import: the lib_thread consult this twin paid in every process left it
#: and its example alike, and the pooled observations top out at 313661 against
#: a ceiling of 154093 (the example's cheapest plain-lane run, 133772, plus its
#: 10% and the 6944 four compiled definitions cost to author under the
#: constants re-derived on this tree). The spin where the example sleeps is
#: still this twin's own program, and BUDGET is the envelope: a run outside it
#: is red whatever this says [measured 2026-09-09: the pooled --observe runs
#: above, beside the plain lane's example cost; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
OVERRUN = 159568

#: DIVERGED 2026-09-07, the example holds 1 atom the twin does not (1 =) and
#: the twin holds 5 the example does not (3 :, 2 =): the twin is an ordinary
#: Python program and its body lowers to the engine's own forms: a match
#: statement is ONE equation whose body is a case tower where the example
#: writes one clause per arm, a named intermediate is a let* the original does
#: not have, a Python truth test wraps its condition in py-truthy, and the
#: annotations and docstrings that come with it are stored beside them
#: [measured 2026-09-07: the two stored-atom surpluses, one fresh process per
#: side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "ed6553c84db2104e12f76c044cf5e4b46ae6ae3e18b51a55f7bf4672f97db5ea"
