"""examples/translation/translatepredicate.metta in Python: a Prolog goal inline.

`translatePredicate` compiles its argument straight into the clause the
translator is building, so `(is $x 2)` and `(+ $x 40 $z)` are Prolog goals that
run where the equation runs, and `progn` sequences them so the second sees what
the first bound.

That sequencing has to happen in one engine call, which is why this file is one
term rather than three Python statements: the first goal binds `$x` and the
second reads it, and a Python variable cannot hold a binding the engine has not
finished making (residue, P14.10). Everything else is ordinary: the term is
built at the `S.` door and the sequence is CALLED, `m.fn.progn(...)`, which
answers what the last goal left even though `$x` and `$z` are the caller's own
variables: their bindings are the parallel row face on the same view.
"""

from metta import S, V

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Run two Prolog goals in sequence, and read what the second bound."""
    translate = S.translatePredicate
    assert m.fn.progn(
        translate(S["is"](V.x, 2)), translate(S["+"](V.x, 40, V.z)), V.z
    ) == [42]
