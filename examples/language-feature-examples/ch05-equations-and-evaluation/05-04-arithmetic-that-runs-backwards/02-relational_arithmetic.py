"""examples/ch05-equations-and-evaluation/05-04-arithmetic-that-runs-backwards/02-relational_arithmetic.metta in Python: CLP(FD) both ways.

The `#` operators are constraints rather than evaluations, so they run in
every direction: give any two of the three and the engine solves for the
third, by propagation rather than by search.

Two doors, one per job, and this file uses both deliberately. `m.fn["#+"]`
CALLS the constraint, so `plus(1, 2)` answers `[3]` and reads as Python;
`fn["#+"]` is the static namespace, whose members are the symbols themselves,
so it BUILDS the term, which is what a backward query needs, because the
thing being solved for has to reach the engine unevaluated. Python has no `#+`
and should not: these are MeTTa names, and the subscript is the door for a
name Python's own grammar will not take.

Running one backwards is `m.solve(pattern, subject)`: the known value on
`let`'s pattern side, the constraint on its subject side, and the answer
projected by the variable's own name.
"""

from metta import V, fn


def twin(m):
    """Run each constraint forwards, then run three of them backwards."""
    # COST, recorded because the lane's band reports it and it is the
    # library's to fix, not this twin's: `m.fn[...]` resolves its handle
    # against the engine on every access, about 1,200 inferences per name,
    # and this file names fourteen. With the first answer view's own ~4,700
    # setup that is most of the twin's 24,730 against the example's 19,446.
    # Nothing about the spelling changes; the resolution should be cached
    # [measured 2026-08-23: 1,206 for the first name and 1,178 for the second,
    # with m.stats() around one m.fn["#<"] and one m.fn["#>"] access;
    # commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    plus, times, minus = m.fn["#+"], m.fn["#*"], m.fn["#-"]
    divide, modulo = m.fn["#div"], m.fn["#mod"]
    smallest, largest = m.fn["#min"], m.fn["#max"]
    less, greater = m.fn["#<"], m.fn["#>"]
    equal, unequal = m.fn["#="], m.fn[r"#\="]
    at_most, at_least = m.fn["#=<"], m.fn["#>="]

    # Forwards, the same as ordinary arithmetic.
    assert plus(1, 2) == [3]
    assert times(3, 4) == [12]
    assert minus(10, 4) == [6]

    # Backwards: the result is known and the operand is not.
    assert m.solve(5, fn["#+"](V.x, 2)).x == 3
    assert m.solve(12, fn["#*"](V.y, 4)).y == 3
    assert m.solve(6, fn["#-"](V.z, 4)).z == 10

    # Integer division, remainder, and the two extremes.
    assert divide(13, 4) == [3]
    assert modulo(13, 4) == [1]
    assert smallest(3, 7) == [3]
    assert largest(3, 7) == [7]

    # All six comparisons answer True or False rather than succeeding or
    # failing, so they compose with `if`.
    assert less(1, 2) == [True]
    assert less(2, 1) == [False]
    assert greater(2, 1) == [True]
    assert equal(3, 3) == [True]
    assert unequal(3, 4) == [True]
    assert at_most(1, 2) == [True]
    assert at_most(2, 1) == [False]
    assert at_least(2, 1) == [True]
    assert at_least(1, 2) == [False]

    # Composed, and still solvable backwards through two constraints.
    assert m.solve(20, fn["#*"](fn["#+"](V.a, 1), 4)).a == 4


#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 5197 to 5501, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (metta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 5501 to 5502, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 5502 to 5536, on the release tree:
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
#: RE-PINNED 2026-08-26, 5536 to 5560 (+24), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 5560 to 6313 (+753), the compiled-language batch:
#: try/raise on the error algebra, dict-space literals with lib_dict auto-
#: import, the exact-integer operator family as engine builtins (bit-
#: and/or/xor/not, floor-div, five registration rows moving clause indexing),
#: the implicit-island fallback, the except/error-payload runtime ops replacing
#: seven py- bridges, the variadic door family (transfer, batched remove and
#: eval), the -= drain-law repair, and fourteen twins healed to the arbiter
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=51b792423cec5787614d1488c0793b8a50eaa6fc].
#: RE-PINNED 2026-09-01, 6313 to 6273 (-40), the subtract-atom primitive and
#: the Counter grain for -=: a new engine head shifts every twin's load
#: structure, and the removal doors changed meaning where a twin spells one
#: [measured 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=c6a40460b1db341198a6150e3600f502831a6e83].
#: RE-PINNED 2026-09-01, 6273 to 6352 (+79), generic Python operators now
#: dispatch through live protocols while source twins explicitly name
#: relational engine heads [measured 2026-09-01: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=e3787593132a7ece2d300397045f7415709847c9].
#: RE-PINNED 2026-09-02, 6352 to 6484 (+132), static contract discharge and
#: policy-stable recompilation [measured 2026-09-02: min-of-3 serial fresh
#: processes; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=c00341f0ff9d83d1b9338ca86ad51708eaf07ebd].
BUDGET = 6484
