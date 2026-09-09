"""Purpose: examples/ch09-types/23-variadic_arrow_faces.metta in Python.

Declaration/equation atoms are the rung below compiled def for segment heads.
The raw answer door keeps Error atoms as values for the refusal cells.
[tested: variadic_arrows; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7]
"""

from metta import Expression, S, V, arrow, equation, seg, typed


def twin(m):
    """Exercise expansion, element positions, holding and the fixed control."""
    m += typed(S.vsum, arrow(S[":seg"](S.Number), S.Number))
    m += equation(S.vsum(seg(V.ns))).to(S.foldl_atom(V.ns, 0, S["+"]))  # rung: compiled def has no segment parameter
    for count in range(4):
        assert m.fn.vsum(*range(1, count + 1)) == [sum(range(1, count + 1))]
    m += typed(S.vflag, S.Bool)
    for position in range(3):
        arguments = [1, 2, 3]
        arguments[position] = S.vflag
        call = S.vsum(*arguments)
        assert m.answers(call) == [S.Error(call, S.BadArgType(position + 1, S.Number, S.Bool))]

    signature = arrow(S[":seg"](S.Atom), S.Atom)
    m += typed(S.vheld, signature)
    m += equation(S.vheld(seg(V.es))).to(V.es)  # rung: as above
    assert m.fn.vheld() == [Expression()]
    assert m.fn.vheld(S["+"](1, 1), S["+"](2, 2)) == [Expression(S["+"](1, 1), S["+"](2, 2))]
    assert m.type(S.vheld) == signature

    m += typed(S.mixed, arrow(S.Number, S[":seg"](S.Atom), S.Atom))
    m += equation(S.mixed(V.n, seg(V.xs))).to(S.kept(V.n, V.xs))  # rung: as above
    assert m.fn.mixed(S["+"](1, 1), S["+"](2, 2), S["+"](3, 3)) == [S.kept(2, Expression(S["+"](2, 2), S["+"](3, 3)))]
    assert m.fn.mixed(2) == [S.kept(2, Expression())]

    @m.define
    def fixed2(a: int, b: int) -> int:
        return a + b

    assert fixed2(1, 2) == [3]
    assert m.answers(S.repr(S.catch(S.fixed2(1, 2, 3)))) == [
        "(Error (domain_error (function_input_arities fixed2 (2)) 3) none)"
    ]


#: The initial 36,561-inference price includes once-per-arity segment
#: compilation and positional type diagnostics;
#: the no-work compiled-call matrix matches fixed callees and no allowance is
#: widened [measured 2026-09-09: min-of-3 serial fresh processes;
#: command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
#: RE-PINNED 2026-09-09, 36561 to 36514 (-47), The fixed diagnostic reader now
#: consumes parameter and argument spines together, and segment families
#: compile once per shape. Fixed-arrow presentation and warmed single-run
#: callees keep their controls. Fused syntax admission adds 44 inferences for a
#: cold prepare/admit type shape versus the old annotation scan and eight per
#: source-preflight declaration; repeated shapes reuse the analysis. The
#: authoring control moves by -16 once, with its per-definition slope
#: unchanged. Cold family generation is included. See
#: docs/journal/2026-09-09-the-splice-in-an-arrow.md [measured 2026-09-09: min-
#: of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6031c83ab3002b5703cb6fcb10e70a60a89f4ad7].
BUDGET = 36514
