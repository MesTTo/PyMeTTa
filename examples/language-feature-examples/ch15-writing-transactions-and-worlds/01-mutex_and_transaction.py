"""Purpose: examples/ch15-writing-transactions-and-worlds/01-mutex_and_transaction.metta in Python: a counter five threads share.

Read-modify-write on a shared count is a race unless the readers and the
writers agree on a lock, so the example writes the increment three ways: the
sloppy one that would race, the mutex-protected one that does not, and one
wrapped in a transaction whose branch fails, which rolls the removal back.
Five protected increments run at once and 37 becomes 42.

`m.parallel(*targets)` is the parallel door under the language's own name, so
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

    m.parallel(*(S.mutexinc() for _ in range(5)))
    assert list(temp) == [S.cnt(42)]

    m.eval(rollback())
    assert list(temp) == [S.cnt(42)]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships. This file is also the one in its folder whose counter is not
#: point-deterministic, because hyperpose schedules five OS threads; the
#: re-pin pass owns that decision too [assumed 2026-08-24: the number is a
#: placeholder, not a measurement; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 24312 to 24332, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 24332 to 24330, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 24330 to 24332, on the release tree:
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
#: RE-PINNED 2026-08-25, 24332 to 24334, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 24334 to 24250 (-84), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 24250 to 24256 (+6), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 24256 to 16210 (-8046), the compiled-language batch:
#: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 16210 to 16203 (-7), the subtract-atom primitive and
#: Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-02, 16203 to 16322 (+119), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-02, 16322 to 16328 (+6), static contract discharge with
#: policy checks confined to invalidated contracts [measured 2026-09-02: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
#: RE-PINNED 2026-09-06, 16328 to 15758 (-570), the one pricing pass at the
#: 0.8.0 release cut, and trunk's own movement rather than any mechanism in
#: this twin: each pin was taken on the base its own branch had, and the
#: September merge wave has moved the engine's clause layout, the evaluation
#: path and the library's write doors since [measured 2026-09-06: min-of-3
#: serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=b96e1a15260b7538a8e42be613bcc5dd0dddd136].
#: RE-PINNED 2026-09-07, 15758 to 16163 (+405), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: ENVELOPE 2026-09-08, 16152..16164 over 37 observations of 'full-
#: lane/231/workers=32': five OS threads take one mutex in turn, so the count
#: carries the order they got it in; a point pin on it is a claim about a
#: schedule and not about this twin. Spread 12 [measured 2026-09-08: `python
#: extensions/python/tools/twin_coverage.py --observe`, two runs of 12 and 25
#: rounds pooled; commit=9010a79b01c9b2a66b96a3952fa378fb3e939dc3].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because the every-atom merge widened
#: the corpus from 231 to 277 twinned examples and the scheduler this counter
#: answers to is the lane's own 32-worker pool over that corpus: 25 observations
#: pooled from two `--observe` runs of 10 and 15 rounds read 16152..16165 where the
#: 37 under 'full-lane/231/workers=32' read 16152..16164. A run outside this envelope is a
#: re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/mergeTW-observe-10.log and -15.log; commit=08f6f4df19a283bb84ba5f679c83944b42685b2e].
#: RE-ENVELOPED 2026-09-08 under 'full-lane/277/workers=32', because metta_substitute_self/3 now
#: probes a term for the text &self before walking it, where the twins-lane merge's
#: one-equation door walked every natively added equation, so this counter's whole
#: envelope moved down by the equations it adds: 25 observations pooled from two
#: `--observe` runs of 10 and 15 rounds read 15888..15897 where the 25 under
#: 'full-lane/277/workers=32' read 16152..16165. A run outside this envelope is a re-observation,
#: not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and --rounds 15,
#: ai-tmp/integrator-849a9e/law3-observe-10.log and -15.log; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-OBSERVED 2026-09-08 under 'full-lane/277/workers=32', 15888..15903 over
#: 36 observations to 16096..16107 over 26: the module boundary merged with
#: trunk (refactor/engine-and-libraries-as-modules at b64291369): the twin's
#: host crossings each resolve through one more chain link, prelude ->
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
#: merge read 15899 against 15888..15897, a scheduler extreme the 25
#: observations had not reached, so ten more full-lane rounds plus that reading join
#: them: 36 observations read 15888..15903. Nothing in that merge runs on this twin's
#: path; the envelope widens with its evidence, as an extremal envelope does. A run
#: outside it is a re-observation, not a re-pin [measured 2026-09-08: python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10,
#: ai-tmp/integrator-849a9e/mergeFACE-observe-10.log; commit=4a6029296381da416c61a3b25d1609c72a3e062a].
#: RE-OBSERVED 2026-09-08 after typed host doors joined the boot catalog.
#: Ten observation rounds read 15888..15898; the subsequent complete gate
#: read 15886. These eleven observations replace the earlier boot state's
#: envelope and retain the mutex's scheduling spread [measured: exact extrema
#: over 11 full-lane observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and
#: sh check.sh twins; fixture=full-lane/277/workers=32; commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543].
#: RE-OBSERVED 2026-09-09 after a library's Prolog half compiles beside itself
#: on its first import (metta_load_source/2, seam:compiled_source/1), POOLED
#: over every full-lane sample on this tree: two --observe runs of ten rounds
#: and 4 plain lane runs read 17032..17040 (spread 8) over 24 observations,
#: replacing the earlier envelope of the tree before this one. Its count is the
#: scheduler's, five OS threads take one mutex, so the envelope is exact
#: extrema and a run outside it is a re-observation under --observe, not a re-
#: pin [measured 2026-09-09: python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10, twice, beside the plain lane runs ai-tmp records;
#: fixture=full-lane/277/workers=32; commit=f26de01fbf3e0e3c64bb691c66a59fa959fee7f3].
#: POOLED 2026-09-09: published 17032..17040 over 24
#: observations, receipt pass 16864..16936 over 10, and
#: final pass 16857..16930 over 10. Exact extrema and counts
#: retain the existing empirical protocol; no point budget becomes an envelope.
#: [measured: two complete ten-round passes; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: RE-OBSERVED 2026-09-10 after setting the file-search cache lifetime
#: before engine creation. This complete ten-round population uses
#: 16854..16862 over 10 observations. Earlier protocol
#: samples remain above as history and do not enter this envelope.
#: [measured: all 277 pairs, this twin succeeds in every round; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043]
#: POOLED 2026-09-10: the earlier before-boot population has 16854..16862 over
#: ten samples; the receipt-frame repair's complete population has 16836..16844
#: over ten. The full lanes at 17bec75f1 and e70deddaa add 16857 and 16855.
#: Their exact pooled extrema are 16836..16862 over 22 observations under the
#: same cache-normalised protocol. Earlier runtime samples remain identified
#: separately; the receipt watcher now transfers ownership at live completion.
#: No point becomes an envelope. The final gate is an independent validation
#: sample [measured 2026-09-10: two complete ten-round populations and two full
#: lane checks; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and sh check.sh twins; fixture=full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: the retained 22 observations have 16836..16862. The full
#: lane at 71535ae17 adds 16842; a further complete ten-round population at
#: db8640733 adds 16836..16841. All 2770 new samples succeed. Exact pooled
#: extrema are 16836..16862 over 33 observations under the same before-boot
#: cache protocol. No point becomes an envelope [measured 2026-09-10: three
#: complete ten-round populations and three full-lane readings; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10 and sh
#: check.sh twins; fixture=full-lane/277/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-10: retain the previous33 observations and both full-gate
#: samples (3fb950149: 16841; 503e21f8a: 16838), then append the complete ten-
#: round populations (2f1be07e9: 16836..16845; e93f2028d: 16836..16845). Both
#: populations have2770 successful samples, no failures and no point movements
#: or excursions. The e93f2028d population measures the repaired concurrent
#: join; the2f1be07e9 observation retains its own version. Exact pooled extrema
#: are16836..16862 over55 samples, without padding. No point becomes an
#: envelope. [measured 2026-09-10: five complete ten-round populations and five
#: full-lane readings; command=python extensions/python/tools/twin_coverage.py
#: --observe --rounds 10 and sh check.sh twins; fixture=full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: POOLED 2026-09-11: keep all 55 previous observations, append the two
#: complete gate readings (895878bbe=16841, 4d4fa2c55=16845), then all ten
#: qualified 4d4fa2c55 rounds (16836..16840). The resulting 67 observations
#: have exact extrema 16836..16862. The prior scheduling mechanisms remain;
#: this complete lane also measures the explicit pending-definition provider.
#: No targeted or instrumented reading enters an envelope. The end-of-wave
#: battery re-observes and re-pins the whole lane on the merged tree under this
#: protocol, pooling every empirical extension with its count and mechanism.
#: [measured 2026-09-11: six complete ten-round populations and seven full-lane
#: readings; command=python extensions/python/tools/twin_coverage.py --observe
#: --rounds 10 and sh check.sh twins; fixture=full-lane/277/workers=32/file-
#: search-cache-time=9223372036854775807/before-boot; commit=8ca8a387fc61d0918484b19a1a3baf85b6523043].
#: RE-ENVELOPED 2026-09-11 under 'full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot': the lane grew from 277 to 282 twinned
#: examples (the REDS corpus example and the wave's own), and the merged tree
#: carries FROM's reference rows, BINDING's one native evaluation entry,
#: W-OBSERVE's observer guard, PERF's receipts batching and cursor retirement,
#: and the REDS shared loader; ten fresh full-lane observations read
#: 16693..16701 (spread 8, samples [16696, 16699, 16700, 16700, 16698, 16701,
#: 16700, 16693, 16697, 16699]) where the 67 under 'full-
#: lane/277/workers=32/file-search-cache-time=9223372036854775807/before-boot'
#: read 16836..16862. A run outside this envelope is a real finding, and a new
#: mode discovered later extends it with its observation count rather than
#: widening blind [measured 2026-09-11: exact extrema over 10 observations;
#: command=python extensions/python/tools/twin_coverage.py --observe --rounds
#: 10; fixture=full-lane/282/workers=32/file-search-cache-
#: time=9223372036854775807/before-boot; commit=57f84148ba2684015f052d533f3197eca07b1f7b].
#: POOLED 2026-09-11: a second ten-round population under the same protocol,
#: taken on the tree that carries engine/metta/limits.pl and the re-pinned
#: twins, read 16709..16714 (samples [16710, 16711, 16714, 16711, 16710,
#: 16714, 16711, 16709, 16712, 16713]); pooled with the 10 above at
#: 16693..16701, 16693..16714 over 20 observations [measured 2026-09-11: exact
#: extrema over 10 observations; command=python
#: extensions/python/tools/twin_coverage.py --observe --rounds 10;
#: fixture=full-lane/282/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=23ed2559a7c9b5712e1f6f4710ed02f8d5c6a23d].
#: EXTENDED 2026-09-12: the lane run that verified the twins' +8 repair (sh
#: check.sh twins on the finished tree, the box carrying three Codex jobs'
#: benchmarks) read 16717, 3 above the pooled maximum; the envelope takes that
#: observation with its count, 16693..16717 over 21, rather than widening
#: blind, and the next battery's ten rounds re-observe it [measured
#: 2026-09-12: one full-lane reading; command=sh check.sh twins;
#: fixture=full-lane/282/workers=32/file-search-cache-time=9223372036854775807/before-boot;
#: commit=23ed2559a7c9b5712e1f6f4710ed02f8d5c6a23d].
BUDGET = {
    "minimum": 16693,
    "maximum": 16717,
    "observations": 21,
    "protocol": "full-lane/282/workers=32/file-search-cache-time=9223372036854775807/before-boot"
}
