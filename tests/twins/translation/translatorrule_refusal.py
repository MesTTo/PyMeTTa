"""examples/translation/translatorrule_refusal.metta in Python: a rule with reasons.

A rule head says WHICH shape it rewrites. A guard inside the rule says whether
the match it got is one the rewrite can honour, which is a different question
and needs a different answer: `(refuse Reason)`. A refusal is a decline rather
than an error, so the call carries on down the dispatch chain and the next
equation gets its turn, and the words the rule gave are published where a
program can read them.

Both equations select on STRUCTURE, `(dose $n)` and `(unit mg)`, and both must
coexist in the order the rule tries them, which is the pair `@m.rules` exists
for. A bundle body EXECUTES, so its comparison is built by the word door,
`S.gt(n, 1000)`, where a lowered body would write `n > 1000`; the arithmetic
builds either way, so `n / 1000` there is the term `(/ $n 1000)`.

Which is why the last claim is an ordinary query: the reason lands in the
reflection space as a fact, so asking why a rewrite did not happen is
`reflection[pattern]` like any other question.
"""

from typing import Any

import metta
from metta import Atom, S, V, arrow, equation, ground, if_, typed

#: The words the rule declines with, which are its own.
TOO_STRONG = ground("a dose above 1000 is not a milligram strength")


def twin(m):
    """Register a rule that declines above a threshold, then cross it."""
    m += typed(S.strength, arrow(Atom, Atom, Any))   # (: strength (-> Atom Atom %Undefined%))

    @m.rules
    def dosing(n):
        # (= (strength (dose $n) (unit mg))
        #    (if (> $n 1000) (refuse "...") (noeval (mg $n))))
        yield equation(S.strength(S.dose(n), S.unit(S.mg))).to(
            if_(S.gt(n, 1000), S.refuse(TOO_STRONG), S.noeval(S.mg(n))))
        # A refusal is a decline, so a rule with another equation tries that one.
        yield equation(S.strength(S.dose(n), S.unit(S.mg))).to(
            S.noeval(S.grams(n / 1000)))       # (= ... (noeval (grams (/ $n 1000))))

    # The directive's MeTTa name ends in `!`, so calling it is the whole of
    # performing it and the statement needs no forcing read.
    m.fn.add_translator_rule(S.strength)

    # A match the rule can honour rewrites.
    assert m.fn.strength(S.dose(250), S.unit(S.mg)) == [S.mg(250)]
    # A match it declines falls through to the second equation.
    assert m.fn.strength(S.dose(5000), S.unit(S.mg)) == [S.grams(5)]

    # And the words are the rule's own, published where a program can ask.
    assert [row.why for row in
            metta.reflection[S.translator_rule_refusal(S.strength, V.why)]] == [TOO_STRONG]


#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 10071 to 10126, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 10126 to 10129, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 10129 to 10131, on the release tree:
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
#: RE-PINNED 2026-08-26, 10131 to 10192 (+61), by the open-tail-index
#: pricing pass, one sweep over the whole corpus after four attributed
#: engine movements: the writable-specialization merge 5c731b03 prices
#: each lazily translated match-bearing equation (~+1,500, first-call
#: probe 2,208 to 3,724 across that merge alone;
#: ai-brief-p14-specializer-translation-tax names the follow-up), the
#: relational-candidate rows of 6917bef7, and the open-tail head-index
#: and deprecation apply-seam fixes recovering their shares; the
#: remainder is compiled-image layout, the class this file's own chain
#: documents [measured: min-of-3 serial fresh processes; command=python bindings/python/tools/twin_coverage.py --measure --rounds 3; fixture=p14-integration open-tail-index pricing tree with engine/reader.so; commit=5ca9ef775933e349f8dc3ec64ec3cb85273a5a00].
BUDGET = 10192
