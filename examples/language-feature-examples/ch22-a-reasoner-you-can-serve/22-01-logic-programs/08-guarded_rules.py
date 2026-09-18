"""Purpose: examples/ch22-a-reasoner-you-can-serve/22-01-logic-programs/08-guarded_rules.metta in Python: a rule's side condition and a tabled answer's witnesses.

The same scored facts, the threshold as a MeTTa equation and then as a Python
callable passed as `where=`, asked on both routes. `why()` on a tabled answer
asks the engine for its witnesses, the sources each derivation uses, so the
fixpoint route explains itself too.
"""

import metta
from metta import S, V


def twin(m):
    """The guard admits a and drops b, and the answer shows its witness."""
    m.add_tagged_fact(0.6, S.score(S.a))
    m.add_tagged_fact(0.3, S.score(S.b))
    m.add(S["="](S.above_half(V.s), S[">"](V.s, 0.5)))
    stored = m.add_tagged_rule(1, S.trusted(V.x), S.score(V.x), where=S.above_half)
    assert stored.children[4] == S.where(S.above_half)

    # Only a clears the bar, on the derived route and on the fixpoint.
    for derivations in (True, False):
        rows = list(m.match(S.trusted(V.x), under=metta.prob, derivations=derivations))
        assert [row.value for row in rows] == [S.trusted(S.a)]
        assert abs(rows[0].annotation - 0.6) < 1e-9

    # A Python guard registers under its own name, like a callable tag.
    def strong(score):
        return score > 0.5

    guarded = m.add_tagged_rule(1, S.vouched(V.x), S.score(V.x), where=strong)
    assert guarded.children[4] == S.where(S.rule_strong)
    assert [row.value for row in m.match(S.vouched(V.x), under=metta.prob)] == [S.vouched(S.a)]

    # The derived route shows the guard that held; the tabled route asks the
    # engine for the witness: one derivation through the fact and the rule.
    assert "where (above-half 0.6) held" in str(m.match(S.trusted(S.a), under=metta.prob).one().why())
    tabled = m.match(S.trusted(S.a), under=metta.prob, derivations=False).one()
    witnesses = tabled.why().alternatives
    assert len(witnesses) == 1
    assert sorted(child.is_rule for child in witnesses[0].children) == [False, True]


#: The twin's own program, priced when it was written; the lane compares it
#: with the example's cost and this pin [measured 2026-09-18: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --measure; commit=49478d67a10793a114d27d01a51f09a685d5136a].
#: RE-PINNED 2026-09-18, 23621 to 23658 (+37), the trunk merged (f97c4b0a3,
#: petta's 61 commits since c75181adc) with the definition batch's load pushed
#: as the running load (2da1155e3): every example moved with the engine, 279 of
#: 294 cheaper (median -0.78%), through the compiled runnable envelope
#: executing each runnable form's fixed answer, name and fuel envelope from
#: compiled clauses, the trunk's trailed scopes and compiled context readers (a
#: b_getval/2 read per recorded assertion in place of the branch's thread-local
#: rows), the host listener door and the receipts loop probing the owner once
#: per set; serial minimum of three fresh processes through the lane's run_twin
#: [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 23658

#: OVERRUN 2026-09-18, 538: the twin costs 23621 against the example's 18397
#: and a ceiling of 23083 (the band plus 2846 to author one compiled
#: definition); the distance is this twin's own program, the callable guard
#: registered as a second rule and the two why() asks, the tabled one running
#: the program again under (product prob polynomial), which the example has
#: no spelling for [measured 2026-09-18: one fresh process per side through the
#: lane's run_example and run_twin; command=python
#: extensions/python/tools/twin_coverage.py --measure; commit=49478d67a10793a114d27d01a51f09a685d5136a].
#: OVERRUN 2026-09-18, 538 to 3385 (+2847): the twin costs 23621 against the
#: example's 18397 and a ceiling of 20775 with the earlier declaration; a
#: minimal twin of this example costs 18461, inside the 20237 the band alone
#: allows, so the distance is this twin's own program. the declaration of 538
#: was priced while the twin authored one compiled definition, 2846 of
#: allowance the lane grants for authoring; the twin since mirrors the
#: example's guard as the MeTTa equation and registers its Python guard as a
#: grounded operation, which the lane does not price as authoring, so the whole
#: distance above the band is the twin's own program: the second rule with the
#: callable guard, both routes asked for it, the witness rendered and the
#: answer re-asked under another carrier, none of which the example does
#: [measured 2026-09-18: one fresh process per side through the lane's
#: run_example and run_twin, the floor from a minimal twin built by the probe;
#: command=python extensions/python/benchmarks/probes/twin_floor.py;
#: commit=bf5f100591493a91324b1d7552b5ad2731601691].
OVERRUN = 3385

#: DIVERGED 2026-09-18, the example holds 0 atoms the twin does not (none) and
#: the twin holds 4 atoms the example does not (1 :, 2 annotation, 1 rule): the
#: twin adds a second rule whose guard is a Python callable registered as the
#: function rule-strong, so its type row, its two annotation rows and the rule
#: row naming (where rule-strong) are the twin's alone; the example's guard is
#: the MeTTa function above-half, which the twin mirrors first [measured
#: 2026-09-18: the two stored-atom surpluses, one fresh process per side;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=bf5f100591493a91324b1d7552b5ad2731601691].
DIVERGENCE = "bdb3f2dcbafa7ac4abb5860bb62b1676e66d0d354482f067629aa25cf4cf836e"
