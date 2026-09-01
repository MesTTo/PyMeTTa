"""examples/ch20-extending-the-engine/20-02-metta-written-in-metta/05-he_minimalmetta.metta in Python: the minimal instruction set, by hand.

This one file is deliberately NOT idiomatic in its body, and the reason is its
subject: `div` is written in minimal MeTTa, out of `chain`, `eval` and `unify`
alone, to exercise the instruction set 70,000 recursions deep. Assignment
lowers to `let*`, not to `chain`, so a compiled Python body would store a
different program and stop being the exercise. The equation therefore goes to
the container door and says exactly what the example says, which the residue
table records against P14.4.

Inside that built body the arithmetic is still Python's own, because an
operator with a VARIABLE operand builds the term: `V.x - V.y` is `(- $x $y)`
and `1 + V.accum` is `(+ 1 $accum)`. The comparison takes its WORD, `S.lt`,
since the four rich comparisons order atoms rather than building terms. The
four-argument `unify` is the conditional matcher, which the exported two-
argument `unify` is not, so it is spelled at the mention door.

Everything outside the equation is Python: the definition is built once and
named, and the claim is an ordinary comparison.

`with-pragma!` is named too, and this is the one mode in the folder no
with-block reaches. `m.limits` grew a `stack=` keyword, but it is SWI's stack
size in BYTES: measured 2026-08-24, this same 350,000-step run under
`m.limits(stack=8_000_000_000)` still answers
`(Error (div 278580 5 14284) StackOverflow)`, where `with-pragma!` raising
`max-stack-depth` answers 70000. The residue entry says so.

The pragma takes the attribute door, not a bracket. A trailing `!` has no
Python image, so `m.fn.with_pragma` resolves `with-pragma!` by rung 4's own
fallback, and because the resolved name ends in `!` the call performs on the
line that writes it.
"""

from metta import S, V, equation, lib

#: The 70,000-step interpreter exercise states a budget above the engine default.
DEEP_STACK = (S.max_stack_depth(1_000_000),)


def twin(m):
    """Write integer division as chain, eval and unify, then run it 70,000 deep."""
    m += lib.he

    m += equation(S.div(V.x, V.y, V.accum)).to(
        S.chain(S.eval(V.x - V.y), V.r1,
          S.chain(S.eval(S.lt(V.r1, 0)), V.r2,
            S.chain(S.unify(V.r2, True,  # noqa: FBT003  -- True is the ATOM the comparison answers, matched against, not a flag
              V.accum,
              S.chain(S.eval(1 + V.accum), V.inc,
                S.chain(S.eval(S.div(V.r1, V.y, V.inc)), V.r4, V.r4))), V.r3, V.r3))))

    counted = S.chain(S.eval(S.div(350000, 5, 0)), V.rr, V.rr)
    assert m.fn.with_pragma(DEEP_STACK, counted) == [70000]


#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 105850648 to 105850667, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 105850667 to 105850670, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 105850670 to 105850672, on the release tree:
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
#: RE-PINNED 2026-08-26, 105850672 to 104380670 (-1470002): an unre-pinned
#: improvement of the same era as c7468b27's algebra-tower routing,
#: stable across every later bracket probe [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 104380670 to 28989842 (-75390828), one corpus pricing
#: pass on the merged tree for the 2026-08-27..09-01 engine span
#: (8e75816d..f0744f86), whose four mechanisms are decomposed per lane in
#: benchmarks/baseline.json and ai-parametricity-audit.md passes 10-16: the
#: seam-offer routing and its one-wrap fold (net +8 inferences per evaluation),
#: the strict-scope removal leaving the eval path, the doubling cursor chunk
#: (~3 engine-side inferences per answer replacing per-answer crossings; drains
#: halve on CPU), and the aligned-path work; thirteen twins additionally carry
#: the idiom sweep's local deltas tabulated in the twin-idioms notes, none
#: above 347 [measured 2026-09-01: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 28989842 to 28989836 (-6), the subtract-atom primitive
#: and Counter's grain for -=: a new engine head shifts every twin's load
#: structure, the removal doors changed meaning where a twin spells one, and
#: the quad twin stopped being a different program [measured 2026-09-01: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 28989836
