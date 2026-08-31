"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/02-logicprogset.metta in Python: a set built by checking it.

`myf` says what a two-element set containing `a` and `b` is, and the example
then asks for one. Nothing constructs it: the first two conjuncts BIND `$M` by
membership and the third fixes its size, so the answer falls out of the search.

The clause is a `@m.rules` bundle because MeTTa's `and` is not Python's.
Python's `and` short-circuits on truthiness and lowers to a `let*`-then-`if`
chain; `(and (member a $M) (member b $M))` is a generate-and-test in which the
first conjunct binds for the second, and that binding IS the example. A rules
body EXECUTES, so `&` builds the conjunction term there, rung 3 of the descent
ladder, and `S.eq` builds the equality by its operator word.

The claim is `solve`, which is the relational `let`: the subject is evaluated,
its answer is unified with the pattern, and the subject's own variables come
back as bindings. That is what carries `$M` out, where an evaluation would
answer values.
"""

from metta import TRUE, S, V, equation, fn


def twin(m):
    """Say what the set is, then let the search find one."""

    @m.rules
    def membership(members):
        """The one equation, as a term: (and (and (member a $M) (member b $M)) (== (size-atom $M) 2))."""
        yield equation(S.myf(members)).to(
            fn.member(S.a, members)
            & fn.member(S.b, members)
            & S.eq(fn.size_atom(members), 2)  # rung: `len()` needs a value; $M is a variable the search has not bound yet
        )

    # `(a b)` is the two-member SET the search found. Calling the head is the
    # shorter spelling of that same two-element atom.
    # !(test (if (once (myf $M)) $M) (a b))
    assert m.solve(TRUE, fn.once(S.myf(V.M))).M == S.a(S.b)


#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=6a3e8b959229afa7adce172704045d1456a40df6].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 11691 to 11694, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-26, 11694 to 11708 (+14), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python extensions/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
#: RE-PINNED 2026-09-01, 11708 to 4493 (-7215), one corpus pricing pass on the
#: merged tree for the 2026-08-27..09-01 engine span (8e75816d..f0744f86),
#: whose four mechanisms are decomposed per lane in benchmarks/baseline.json
#: and ai-parametricity-audit.md passes 10-16: the seam-offer routing and its
#: one-wrap fold (net +8 inferences per evaluation), the strict-scope removal
#: leaving the eval path, the doubling cursor chunk (~3 engine-side inferences
#: per answer replacing per-answer crossings; drains halve on CPU), and the
#: aligned-path work; thirteen twins additionally carry the idiom sweep's local
#: deltas tabulated in the twin-idioms notes, none above 347 [measured
#: 2026-09-01: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 4493
