"""Purpose: examples/ch17-concurrency-and-the-loop/02-thread_linda.metta in Python: the two blocking binds.

A space is a tuple space. `peek-atom` waits until a matching atom is there and
answers it LEAVING it, which is Linda's rd; `take-atom` does the same and
REMOVES exactly one, which is Linda's in. The difference is the coordination
model itself: a read is one-to-n, every consumer sees the tuple, and a take is
one-of-n, exactly one consumer gets it. Both are event-driven through the
engine's own write hooks rather than polls, and both take an optional deadline
in seconds. The non-blocking pair needs nothing new: matching is Linda's rdp
and removing is its inp.

The blocking binds are the handle verbs the coordination family rules,
`jobs.peek(S.job(V.n))` and `jobs.take(...)`: each answers the ONE atom it
waited for, and a deadline that expires RAISES rather than answering nothing,
which is the absence law and Python's own way of saying a wait gave up. Both
load lib_thread in the caller's context, so `&jobs` still holds nothing but
this example's jobs and the emptiness claims stand. `await-atom` is the older
name for `peek-atom` and has no verb of its own, so the sugar claim names it
at the function namespace.

The miss is caught as `TimeoutError`, which is what these two doors raise;
`metta.Timeout`, the guide's taught spelling and what `Channel.recv` raises, is
a SUBCLASS of it, so this line keeps working when the two doors agree. The
split is a library defect the report carries, not something a twin should
paper over.

Everything else is Python: each space is created by ATOM because a space name
is a symbol, writing is `+=`, enumerating is `list`, the example's `let` chains
are assignments, the writer thread is `spawn`, taking the number out of a
`(job N)` atom is `atom[1]`, and adding two of those numbers reads their
carried scalars, since `+` over grounded atoms stages a term instead of
computing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import S, V, lib, spawn


def twin(m):
    """Peek twice, take once, drain a queue, and rendezvous with a thread."""
    m += lib.thread

    @m.define
    def inc(x: int) -> int:
        # (= (inc $x) (+ $x 1))
        return x + 1

    # A peek leaves the atom, so two peeks answer the same job.
    jobs = metta.space(S.jobs)
    jobs += S.job(7)
    assert jobs.peek(S.job(V.n)) == S.job(7)
    assert jobs.peek(S.job(V.n)) == S.job(7)

    # await-atom is the older name for the same thing and stays as sugar.
    assert m.fn.await_atom(jobs, S.job(V.n)) == [S.job(7)]

    # A take removes the one it answers, so the second finds nothing and gives
    # up on its deadline instead of answering the same job twice.
    assert jobs.take(S.job(V.n)) == S.job(7)
    try:
        jobs.take(S.job(V.n), deadline=0.05)
    except TimeoutError:
        gave_up = True
    else:
        gave_up = False
    assert gave_up
    assert list(jobs) == []

    # A worker is the point: take a job, do it, take the next. Each take
    # consumes its own job, so two takes drain two.
    work = metta.space(S.work)
    work += S.job(1)
    work += S.job(2)
    first = work.take(S.job(V.a), deadline=1)
    second = work.take(S.job(V.b), deadline=1)
    assert first[1].value + second[1].value == 3
    assert list(work) == []

    # Blocking means blocking: the take below starts before the atom exists and
    # another thread writes it, which is the rendezvous a channel would
    # otherwise be needed for.
    inbox = metta.space(S.inbox)
    writer = spawn(
        S.add_atom(inbox, S.msg(S.hello))
    )  # rung: the write is DATA handed to another engine thread, not a store this process mutates, so `space += atom` cannot say it
    seen = inbox.take(S.msg(V.what), deadline=10)
    writer.wait()
    assert seen == S.msg(S.hello)
    assert list(inbox) == []


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree. This one
#: needs an EMPIRICAL ENVELOPE rather than a point: its cost moved across
#: 14 inferences over the concurrent lane's own observations, because
#: the rendezvous waits on another thread
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: Until it is measured again, this file's own distribution-budget residue
#: entry, retired 2026-08-22 because the twin declared an envelope, is
#: unbacked: a point budget is not the envelope that retired it.
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 135764 to 136197, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 136197 to 136183, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 136183 to 136133, on the release tree:
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
#: false claim here. Bounds are the exact extrema of 10
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
#: The confirming differential supplied an eleventh observation inside those
#: bounds [measured: eleventh full-lane observation 401241; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: A second ten-round observe pass stayed inside the first pass's bounds
#: [measured: exact extrema over 10 further observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/219/workers=32; commit=e3787593132a7ece2d300397045f7415709847c9].
#: Four confirming differentials stayed inside those bounds [measured: four
#: further full-lane observations, the last 401241; command=python
#: extensions/python/tools/twin_coverage.py; fixture=full-lane/219/workers=32;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RETIRED THE ENVELOPE 2026-09-02 after exact numeric annotations restored
#: native operator heads and published their MeTTa declarations. The current
#: implementation answered 401370 in all ten full-lane observations and all
#: three serial measurements, so a point pin states the measured distribution
#: while an envelope would have to invent a spread [measured: 10 full-lane
#: observations and min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, then python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3
#: examples/ch17-concurrency-and-the-loop/02-thread_linda.metta;
#: fixture=full-lane/219/workers=32 and serial fresh processes; commit=d0dfff1a3ee6c85472fd9b12d6e4aec007a9c301].
#: RE-PINNED 2026-09-02, 401370 to 405731 (+4361), static contract discharge
#: and policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 405731 to 405788 (+57), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 405788 to 405840 (+52), P43 protects both generated
#: policy-check fallbacks from space-local capture [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 405840 to 419241 (+13401), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 419241 to 427810 (+8569), trunk's own movement since
#: each twin's pin was taken on the base its own branch had: twenty-two first-
#: parent steps between the 0.8.0 release re-pin and this tree, the prelude's
#: move into Prolog the largest of them at +39 to +115 a twin and -65,806 on
#: the error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: ENVELOPE 2026-09-08, 427772..427810 over 37 observations of 'full-
#: lane/231/workers=32': every claim is a coordination between two sides the
#: engine's own writes wake, so the count carries which side ran first, so a
#: point pin on it is a claim about a schedule and not about this twin. Spread
#: 38 [measured 2026-09-08: `python extensions/python/tools/twin_coverage.py
#: --observe`, two runs of 12 and 25 rounds pooled; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because the every-atom merge widened
#: the corpus from 231 to 277 twinned examples and the scheduler this counter
#: answers to is the lane's own 32-worker pool over that corpus: 25 observations
#: pooled from two `--observe` runs of 10 and 15 rounds read 427823..427856 where the
#: 37 under 'full-lane/231/workers=32' read 427772..427810. A run outside this envelope is a
#: re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/mergeTW-observe-10.log and -15.log; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because metta_substitute_self/3 now
#: probes a term for the text &self before walking it, where the twins-lane merge's
#: one-equation door walked every natively added equation, so this counter's whole
#: envelope moved down by the equations it adds: 25 observations pooled from two
#: `--observe` runs of 10 and 15 rounds read 427720..427720 where the 25 under
#: 'full-lane/277/workers=32' read 427823..427856. A run outside this envelope is a re-observation,
#: not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/law3-observe-10.log and -15.log; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because the evaluation-fuel scope
#: marker is a trailed write (fix/every-intermittent-root-caused, f6e05ca9) and
#: every runnable form pays fewer inferences per scope, so this counter's whole
#: envelope moved down by its runnables: 25 observations pooled from two
#: `--observe` runs of 10 and 15 rounds read 427685..427713 where the 25 under
#: 'full-lane/277/workers=32' read 427720..427720. A run outside this envelope is a re-observation,
#: not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/mergeFL-observe-10.log and -15.log; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32', 427703..427730
#: over 15 observations to 462787..462825 over 27: the module boundary merged
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
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32' and POOLED: the gate on the face-generator
#: merge read 427680 against 427685..427713, a scheduler extreme the 25
#: observations had not reached, so ten more full-lane rounds plus that reading join
#: them: 36 observations read 427680..427713. Nothing in that merge runs on this twin's
#: path; the envelope widens with its evidence, as an extremal envelope does. A run
#: outside it is a re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10,
#: ai-tmp/integrator-849a9e/mergeFACE-observe-10.log; commit=4a6029296381da416c61a3b25d1609c72a3e062a].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32' and POOLED again: twenty-five full-lane rounds
#: on the extension-package merge read 427675..427713, one scheduler extreme under the
#: 36 observations' floor, so they join them: 61 observations read 427675..427713. The
#: merge changes the Python seat's dispatch (a point's rows partitioned by fallback
#: rank) and nothing this twin spins on; the envelope widens with its evidence. A run
#: outside it is a re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 25,
#: ai-tmp/integrator-849a9e/mergeEXT-observe-25.log; commit=4e0feaf6b8eb13cd17232f6e7d58679b6e22f2b9].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32', 427675..427713
#: over 61 observations to 427703..427730 over 15: boot content moved
#: with the every-closed-set-derived branch -- the refusal table and the typing
#: point are modules this package did not have, three convert doors became one,
#: per-library faces are projections, and the engine gained a catalog watch
#: point -- which shifts SWI clause-indexing shape and moves a twin count by
#: tens. The observations are this tree's own rather than pooled with the
#: earlier ones, because pooling would mix two boot images and the spread an
#: envelope states is a claim about ONE [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 15,
#: ai-tmp/ai-derive-observe.log; commit=c26b6a4d28ef8fb50742440feed2c0578ebb0f58].
#: RE-OBSERVED 2026-09-08 after typed host doors joined the boot catalog.
#: Ten complete rounds observed 432905..432930. Catalog lookup and context
#: setup now see the declared doors; the rendezvous retains its scheduling
#: spread. These observations replace the earlier catalog's envelope
#: [measured: exact extrema over 10 successful observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-OBSERVED 2026-09-09 after a library's Prolog half compiles beside itself
#: on its first import (metta_load_source/2, seam:compiled_source/1), POOLED
#: over every full-lane sample on this tree: two --observe runs of ten rounds
#: and 4 plain lane runs read 134847..134989 (spread 142) over 24 observations,
#: replacing the earlier envelope of the tree before this one. Its count is the
#: scheduler's, its tuple-space workers settle in the order the scheduler runs
#: them, so the envelope is exact extrema and a run outside it is a re-
#: observation under --observe, not a re-pin [measured 2026-09-09: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10, twice,
#: beside the plain lane runs ai-tmp records; fixture=full-lane/277/workers=32;
#: commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: RE-OBSERVED 2026-09-10 after fused syntax admission and shape compilation.
#: Ten complete-lane rounds supplied 10 successful observations under
#: full-lane/279/workers=32.
#: Samples: [136106, 135798, 135798, 135798, 135798, 135798, 136101, 136101, 135794, 135794].
#: Bounds are the observed extrema, with no added margin
#: [measured 2026-09-10: minimum 135794, maximum 136106;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/279/workers=32; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
#: RE-OBSERVED 2026-09-10 after the next complete lane exposed a new
#: channels/pools minimum. Two exact --observe --rounds 10 runs and
#: all three other final-code complete-lane receipts are pooled under
#: full-lane/279/workers=32: 23 successful costs and 0 failed observations.
#: Failed observations contribute no cost; no margin is added.
#: Samples: [136106, 135798, 135798, 135798, 135798, 135798, 136101, 136101, 135794, 135794, 135798, 135798, 135783, 136101, 136101, 135798, 136106, 136101, 135798, 135798, 136101, 136101, 135794].
#: [measured 2026-09-10: minimum 135783, maximum 136106;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/279/workers=32, two observation runs and three plain lane receipts;
#: commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
BUDGET = {
    "minimum": 135783,
    "maximum": 136106,
    "observations": 23,
    "protocol": "full-lane/279/workers=32",
}

#: OVERRUN 2026-09-07, 184000: it drives both sides of every Linda coordination
#: from Python, where the example lets the engine's own writes wake the waiting
#: side. Measured 427810 against a ceiling of 243859; a minimal twin of this
#: example costs 221118, inside the ceiling's 243859, so the distance is this
#: twin's own program [measured 2026-09-07: one fresh process per side;
#: command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: OVERRUN 2026-09-08, 184000 to 199526 (+15526, four of them the deterministic
#: allowance the point pins carry, because a band met exactly is refused): the module boundary merged
#: with trunk (refactor/engine-and-libraries-as-modules at b64291369): the
#: twin's host crossings each resolve through one more chain link, prelude ->
#: metta_engine -> user, while the example runs inside the engine; every
#: crossing this twin makes pays it and the example pays none. Measured 462825
#: against a ceiling of 447303; a minimal twin costs 238746 against the band's
#: 263309, within that ceiling, so the rest is this twin's own program
#: [measured 2026-09-08: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=f1038acdcaf5230b6431c112f38a719d3dc9ef19].
#: OVERRUN 2026-09-08, 186171: the published host catalog changes lookup and
#: context setup costs on both sides. The example costs 221859, giving the
#: band a ceiling of 246759.9. The current envelope's maximum is 432930, so
#: its difference rounds up to 186171 [measured: the full-lane maximum above
#: and a fresh-process example; command=python ai-tmp/ai-door-band-cost.py
#: ch17-concurrency-and-the-loop/02-thread_linda.metta; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: OVERRUN 2026-09-08, 186191: the example also has a scheduling spread.
#: Ten fresh example runs read 221840..221859, so its observed floor gives
#: a ceiling of 246739. Against the twin envelope's maximum 432930 the
#: required difference is 186191 [measured: ten fresh
#: example processes and the twin's full-lane envelope above;
#: command=python ai-tmp/ai-door-example-extrema.py;
#: fixture=example extrema 221840..221859; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: OVERRUN 2026-09-09, 186191 to 199545 (+13354): the door table landed
#: (feat/space-as-a-projection-of-door-rows merged at 6471faa37, its
#: reconciliation fixes at 58bf75947): every Space door is a generated alias
#: over its body, the catalog publishes the door contracts at boot as typed
#: atoms, and the seam's listeners publish on every registration, so boot
#: content and clause layout moved; every crossing this twin makes pays it and
#: the example pays none. Measured 462847 against a ceiling of 449493; a
#: minimal twin costs 238745 against the band's 263308, within that ceiling,
#: so the rest is this twin's own program [measured 2026-09-09: one fresh
#: process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: The example's own count moves between lane runs (236892 to 236904 on
#: the module-boundary tree, 236897 here) while the twin's 462847 holds, so
#: the raise covers the lowest reading of the example plus the four-inference
#: allowance the module-boundary pins recorded [measured 2026-09-09: the
#: twins lane, three runs on the re-pinned tree; commit=aeb46b14152274db84f6415c8a3dd8c98a9c9eb1].
#: OVERRUN 2026-09-09, 199556 to 306483 (+106927): the compiled vocabulary
#: seed, the membership index, base-module type lookups and the singleton
#: decoder landed (perf/cross-engine-waivers merged): a Python decode with one
#: named variable builds no index and one with more builds it at the second
#: distinct name, which moves a twin's engine-side cost while its example,
#: which decodes nothing, holds; boot content and clause layout moved the
#: rest; against the trunk's own run at da0e5755d the twin moved -449 and the
#: example -280, and the twin sat 107068 over its ceiling there already.
#: Measured 704473 against a ceiling of 597546; a minimal twin costs 361658
#: against the band's 397997, within that ceiling, so the rest is this twin's
#: own program [measured 2026-09-09: one fresh process per side;
#: command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=b4341ae382c48ef225f4a52e566af6a9a71757c4].
OVERRUN = 306483

#: DIVERGED 2026-09-07, the example holds 0 atoms the twin does not (none) and
#: the twin holds 1 atom the example does not (1 :): a Python annotation IS a (:
#: name (-> ...)) row and a docstring on a compiled function IS an (@doc name
#: ...) row, so the twin's space carries the declarations and the documentation
#: its own file states where the example leaves both unsaid [measured
#: 2026-09-07: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
DIVERGENCE = "2017524a1cb76351a1648426410b796419548382661d11cfbc6f3c2a279d533a"
