"""Purpose: examples/spaces/matespace2.metta in Python: the same growth, collapsed first.

matespace.py's sibling. `expand` and `mate` here read the space through
`(superpose (collapse (match ...)))` rather than matching lazily, so each round
works from a snapshot of what was there when it started, and `rewriteK` runs
both of them per round instead of expanding 390 times and mating once. Eighty
rounds answer just under 1.3 million atoms.

The count is Python's, `len(answers)` being what `(length (collapse X))`
dissolves into, and it is expensive at this size for the reason matespace.py
measures beside this file: every atom crosses the seam to be counted and thrown
away. The cost is named there and is the library's to close (residue, P14.7).

The three definitions whose bodies name `case` or `once` remain terms
(residue, P14.4). `rewriteK` and the driver compile: sequencing is assignment,
the driver's ambient handle comes from `context-space`, and its seed write is
`space +=`.
"""

from metta import S, V, equation, fn, if_, match

#: Why this twin sits below the top rung, stated once for the whole file.
RUNG = (
    "expand, mate and add-atom-no-duplicate are built as terms: their bodies "
    "name case or once, neither of which a compiled body reaches (residue, P14.4)"
)

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5].
BUDGET = 1


def twin(m):
    """Run eighty expand-and-mate rounds, then count what the space holds."""
    nodup = S.add_atom_no_duplicate

    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    seen = S.collapse(S.once(S.match(V.space, V.atom, V.atom)))
    m += equation(nodup(V.space, V.atom)).to(
        if_(S.eq((), seen), S.add_atom(V.space, V.atom), S.empty())
    )

    # (= (expand) (case (superpose (collapse (match &self (num $t) $t))) ...))
    m += equation(S.expand()).to(
        S.case(
            S.superpose(S.collapse(S.match(m, S.num(V.t), V.t))),
            ((V.t, (nodup(m, S.num(S.M(V.t))), nodup(m, S.num(S.W(V.t))))),),
        )
    )

    # (= (mate) (case (superpose (collapse (match &self (num (M $t)) $t))) ...))
    paired = S.case(
        S.once(S.match(m, S.num(S.W(V.t)), V.t)),
        ((V.t, nodup(m, S.num(S.C(V.t)))),),
    )
    m += equation(S.mate()).to(
        S.case(
            S.superpose(S.collapse(S.match(m, S.num(S.M(V.t)), V.t))),
            ((V.t, paired),),
        )
    )

    # (= (rewriteK $n) (if (== $n 0) done (let* (($temp1 (expand)) ($temp2 (mate)))
    #                                           (rewriteK (- $n 1)))))
    @m.define(name="rewriteK")  # camelCase is outside the underscore map
    def rewrite_k(n):
        if fn.eq(n, 0):
            return S.done
        _grown = fn.expand()
        _mated = fn.mate()
        return rewrite_k(n - 1)

    # (= (mate-space-demo $K) (let* (($s (add-atom ...)) ($g (rewriteK $K)))
    #                               (match &self (num $1) (num $1))))
    @m.define
    def mate_space_demo(k):
        space = fn.context_space()
        space += S.num(S.Z)
        _done = fn.rewriteK(k)
        return match(space, S.num(V.x), S.num(V.x))

    assert len(m.fn.mate_space_demo(80)) == 1297533
