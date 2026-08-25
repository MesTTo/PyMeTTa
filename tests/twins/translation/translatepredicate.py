"""examples/translation/translatepredicate.metta in Python: a Prolog goal inline.

`translatePredicate` compiles its argument straight into the clause the
translator is building, so `(is $x 2)` and `(+ $x 40 $z)` are Prolog goals that
run where the equation runs, and `progn` sequences them so the second sees what
the first bound.

That sequencing has to happen in one engine call, which is why this file is one
term rather than three Python statements: the first goal binds `$x` and the
second reads it, and a Python name cannot hold a binding the engine has not
finished making (friction, P14.10).

Everything else is ordinary. The two goals are built at the naming door, where
`is` takes the bracket because Python's grammar has the word and `+` because
Python's grammar has no name for it at all, and the sequence is CALLED. It
answers what the last goal left, even though `$x` and `$z` are the caller's own
variables: their bindings are the parallel row face on the same view.
"""

from metta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-24: unpriced placeholder, re-pinned by the
#: integrator; commit=8fd49997be43f7909c3582062138c5011df7e811].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 601 to 602, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
BUDGET = 602


def twin(m):
    """Run two Prolog goals in sequence, and read what the second bound."""
    translate = S.translatePredicate

    assert m.fn.progn(                        # (progn
        translate(S["is"](V.x, 2)),           #   (translatePredicate (is $x 2))
        translate(S["+"](V.x, 40, V.z)),      #   (translatePredicate (+ $x 40 $z))
        V.z,                                  #   $z)
    ).one() == 42                             # [42]
