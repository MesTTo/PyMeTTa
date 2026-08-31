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
BUDGET = 16210
