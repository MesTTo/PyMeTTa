"""Purpose: examples/ch18-performance/18-01-larger-workloads/03-superpose_primes.metta in Python: four divisor searches.

Four eight-digit primes, each found by trial division, sharing one branch
budget. Both equations are ordinary Python functions under the decorator: the
recursion delegates by name, and the arithmetic is Python's own, which is what
the guide means by the syntax BEING the semantics.

One thing is worth knowing about what the body compiles to, and it is the
reason the two equality tests name their head.

Python's `==` inside a compiled body lowers to the prelude's `py-eq`, a host
crossing per iteration where the original's `(== 0 (% $n $d))` crosses not at
all, and a compiled `if` used to wrap any non-comparison condition in
`py-truthy` besides. MeTTa's own `==` is declared `(-> $t $t Bool)`, so a
compiled `if` now emits it bare, and `fn.eq(0, n % test_divisor)` stores
exactly the original's condition [measured 2026-08-23 on the merged tree, min
of one fresh process each: 922,119 inferences with the Python operators and
539,720 with the named head, against the example's 543,116; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].

`with-pragma!` stays a term for the one gap left: the four searches overflow the
evaluator's default stack depth without it, and `m.limits` bounds inferences
and time but not stack depth (residue, P14.14). PERFECT:
`with m.limits(stack=1_000_000): ...`, the mode family carrying the pragma
vocabulary the way it carries the other two bounds.

Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, Expression, S, fn

#: The branch allowance these searches state above the evaluator's 100000
#: default. `m.limits` bounds inferences and time, not stack depth.
DEEP = (S.max_stack_depth(1_000_000),)


def twin(m):
    """Define trial division, then ask it about four primes."""

    @m.define
    def find_divisor(n, test_divisor):
        if test_divisor * test_divisor > n:
            return n
        if fn.eq(0, n % test_divisor):  # rung: `==` lowers to the prelude's `py-eq`, a host crossing per iteration, where the example writes MeTTa's own `==`
            return test_divisor
        return find_divisor(n, test_divisor + 1)

    @m.define(name="prime?")
    def prime(n):
        return fn.eq(n, fn.find_divisor(n, 2))  # rung: the same host crossing, in answer position

    # Four searches share one branch budget, so the benchmark states a finite
    # allowance above the evaluator's 100000 default.
    searches = (S["prime?"](53537257), S["prime?"](53781811),
                S["prime?"](54218443), S["prime?"](54734431))
    assert m.fn.with_pragma(DEEP, searches) == [Expression((TRUE, TRUE, TRUE, TRUE))]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 667871 to 667873, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 667873 to 667879, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 667879 to 667844, on the release tree:
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
#: RE-PINNED 2026-08-25, 667844 to 667849, at the release cut: the
#: identity-wire merge (numeric ownership seams, exact-primitive
#: wire, Python operator dispatch), the rules-body staging split
#: (ground folds, op-call staging), and the door-combinations
#: example growing the corpus each move counts through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the whole corpus re-pins once on the exact release tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 after a canonical single-boot QLF regeneration].
#: RE-PINNED 2026-08-26, 667849 to 667995 (+146), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-08-26, 667995 to 668015 (+20), on the composed
#: async-scheduler tree: a live operation call pays the six-inference
#: admission probe the baseline's p14_async_scheduler_comment prices,
#: and the scheduler, context-callback and exact-memo lifecycle clauses
#: move compiled-image layout by tens, the class this file's chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=merged p14-audit-async composed tree with engine/reader.so; commit=5059173b1767600ce4df0f6b7841d88116ee62d3].
#: RE-PINNED 2026-09-01, 668015 to 543912 (-124103), the compiled-language
#: batch: try/raise/dict/set/global/type-alias compilation, engine bit family
#: builtins, prelude except/error-payload ops, variadic doors, twin heals
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 543912 to 543897 (-15), the subtract-atom primitive
#: and Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
BUDGET = 543897
