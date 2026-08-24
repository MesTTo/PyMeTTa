"""Purpose: examples/performance/matespacefast.metta in Python: a million and a half atoms.

`rewriteK` writes three atoms per level and recurses down two branches, so
nineteen levels leave 1,572,862 atoms in the space; `mate-space-demo` runs that
and then matches everything back out. The claim is how many came back.

The recursive equation compiles and then cannot run, which is why it is built
here. A compiled `if` wraps its condition in `py-truthy` and `==` lowers to
`py-eq`, so every level spends reductions the original does not, and the evaluator's
default 100,000 stack bound is reached long before nineteen levels: the
compiled pair answers `(Error (rewriteK (M (W ...)) 2) StackOverflow)` at K=14
where the built pair completes K=19 [measured 2026-08-24; commit=WORKTREE].
`m.limits` bounds inferences and time and not stack depth, and the example
states no pragma to copy. PERFECT: a compiled `if` that leaves an engine-Bool
condition alone. Residue P14.4 and P14.14.

The count IS Python's, and it is the most expensive line in this folder.
`len(answers)` is what `(length (collapse X))` dissolves into, and here the
answers are 1,572,862 atoms: 295,442,370 inferences, 66 seconds and 5.3 GB of
resident memory in one process, against the engine's own count which never
materialises one [measured 2026-08-24; commit=WORKTREE]. It no longer FAILS,
which it did when this twin was first written: the answer view streams where
the old door built one Prolog list, so the wall moved from "cannot run" to
"expensive". The missing door is the one peanofast.py names, a query that
projects or aggregates before it crosses (residue, P14.7); the cost of not
having it is the library's.

The space every equation writes into and matches is the HANDLE, because a space
is an ordinary term operand.
"""

from metta import S, V, equation, fn, if_, match

#: Inferences this twin spends, its own tripwire. PLACEHOLDER: the wave's
#: single re-pin pass prices the whole corpus on the merged tree, because a
#: cost measured in one agent's worktree is a cost measured on a base nothing
#: ships [assumed 2026-08-23: the number is a placeholder, not a measurement;
#: commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Rewrite nineteen levels deep, then count what landed."""
    m += equation(S.rewriteK(V.t, V.n)).to(
        if_(V.n.eq(0),  # rung: the compiled body answers StackOverflow at this depth
                S.done,
                S["let*"](((V["_1"], S.add_atom(m, S.num(S.M(V.t)))),  # rung: as above
                           (V["_2"], S.add_atom(m, S.num(S.W(V.t)))),  # rung: as above
                           (V["_3"], S.add_atom(m, S.num(S.C(V.t))))),  # rung: as above
                          (S.rewriteK(S.M(V.t), V.n - 1),
                           S.rewriteK(S.W(V.t), V.n - 1)))))

    @m.define
    def mate_space_demo(k):
        space = fn.context_space()
        space += S.num(S.Z)
        _rewritten = fn.rewriteK(S.Z, k)
        return match(space, S.num(V.stored), S.num(V.stored))

    assert len(m.fn.mate_space_demo(19)) == 1572862
