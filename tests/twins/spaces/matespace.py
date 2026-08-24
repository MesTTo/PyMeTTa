"""Purpose: examples/spaces/matespace.metta in Python: a space grown to a million atoms.

`expand` doubles every `num` atom into an M-branch and a W-branch, `expandK`
does that 390 times, `mate` pairs the branches, and the whole thing answers
just over a million atoms. It is a scale example, and the scale is what its
Python twin has to respect.

The count is Python's: `len(answers)` is what `(length (collapse X))`
dissolves into. It is expensive at this size, and the number belongs in the
open rather than in a different spelling: 114,470,667 inferences, 23.5 seconds
and 1.2 GB of resident memory in one process, against the engine's own count at
26,313,301 and 5.9 seconds, because a million atoms cross the seam one at a
time to be counted [measured 2026-08-24; commit=8a8b75a1f4052c00c70c29e25e95e4d5a1812cd5]. The missing door is
the one peanofast.py names, a query that projects or aggregates before it
crosses (residue, P14.7); the cost of not having it is the library's.

The three definitions whose bodies name `case` or `once` remain terms because
neither translator form is in the function registry (residue, P14.4).
`expandK` and the driver compile: their sequencing is assignment, the driver's
ambient handle comes from `context-space`, and its seed write is `space +=`.
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
    """Grow a space by 390 doublings, mate the branches, and count what is left."""
    nodup = S.add_atom_no_duplicate

    # (= (add-atom-no-duplicate $Space $Atom)
    #    (if (== () (collapse (once (match $Space $Atom $Atom))))
    #        (add-atom $Space $Atom)
    #        (empty)))
    seen = S.collapse(S.once(S.match(V.space, V.atom, V.atom)))
    m += equation(nodup(V.space, V.atom)).to(
        if_(S.eq((), seen), S.add_atom(V.space, V.atom), S.empty())
    )

    # (= (expand) (case (match &self (num $t) $t) (($t ((add-atom-no-duplicate ...))))))
    m += equation(S.expand()).to(
        S.case(
            S.match(m, S.num(V.t), V.t),
            ((V.t, (nodup(m, S.num(S.M(V.t))), nodup(m, S.num(S.W(V.t))))),),
        )
    )

    # (= (mate) (case (match &self (num (M $t)) $t) (($t (case (once ...) ...)))))
    paired = S.case(
        S.once(S.match(m, S.num(S.W(V.t)), V.t)),
        ((V.t, nodup(m, S.num(S.C(V.t)))),),
    )
    m += equation(S.mate()).to(
        S.case(S.match(m, S.num(S.M(V.t)), V.t), ((V.t, paired),))
    )

    # (= (expandK $n) (if (== $n 0) done (let $temp1 (expand) (expandK (- $n 1)))))
    @m.define(name="expandK")  # camelCase is outside the underscore map
    def expand_k(n):
        if fn.eq(n, 0):
            return S.done
        _step = fn.expand()
        return expand_k(n - 1)

    # (= (mate-space-demo $K) (let* (($s (add-atom ...)) ($g (expandK $K)) ($h (mate)))
    #                               (match &self (num $1) (num $1))))
    @m.define
    def mate_space_demo(k):
        space = fn.context_space()
        space += S.num(S.Z)
        _grown = fn.expandK(k)
        _mated = fn.mate()
        return match(space, S.num(V.x), S.num(V.x))

    assert len(m.fn.mate_space_demo(390)) == 1063919
