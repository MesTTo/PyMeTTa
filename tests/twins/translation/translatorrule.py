"""examples/translation/translatorrule.metta in Python: when the cons happens.

Three definitions of one computation, differing only in WHEN it runs.
`runtime42` has no translator rule, so its call runs at run time.
`compileeval42` has one, so the compiler expands the call and then evaluates
the expansion. `compile42` wraps its body in `noeval`, so the expansion is
handed back as data.

All three are ordinary compiled functions, and `cons` and `noeval` are reached
at the static function namespace, which is what that namespace is for: a
compiled body resolves those names against the engine's catalog, and writing
them as attributes keeps the file readable by a linter and by a reader.

Registering a rule has no Python declaration door yet, so it is the engine's
own function under its MeTTa name. That name ends in `!`, so the call performs
where it is written and needs no forcing read.
"""

from metta import Expression, S, fn

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 10146 to 10241, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 10241 to 10249, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 10249 to 10218, on the release tree:
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
BUDGET = 10218


def twin(m):
    """Write one computation three ways, and see which of them runs when."""

    @m.define
    def runtime42(arg):                   # (= (runtime42 $arg) (cons 42 $arg))
        return fn.cons(42, arg)

    @m.define
    def compileeval42(arg):               # (= (compileeval42 $arg) (cons 42 $arg))
        return fn.cons(42, arg)

    @m.define
    def compile42(arg):                   # (= (compile42 $arg) (noeval (cons 42 $arg)))
        return fn.noeval(fn.cons(42, arg))

    m.fn.add_translator_rule(S.compileeval42)   # (add-translator-rule! compileeval42)
    m.fn.add_translator_rule(S.compile42)       # (add-translator-rule! compile42)

    assert runtime42((43,)) == [Expression((42, 43))]   # [(42 43)]
    assert compileeval42((43,)) == [Expression((42, 43))]   # [(42 43)]
    assert compile42((43,)) == [Expression((42, 43))]   # [(42 43)]
