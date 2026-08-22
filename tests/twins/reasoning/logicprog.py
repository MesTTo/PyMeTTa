"""Purpose: examples/reasoning/logicprog.metta in Python: a recursive relation over facts.

Six successor facts and a transitive closure over them, asked backwards: which
letters come before `d`. The two dispatch policies go into the reflection space
through the ordinary write door, `space += atom`, because that is what
`add-atom` is; `petta.REFLECTION_SPACE` names it so the `&petta` symbol is
never written.

`successor`'s six clauses are ground facts, so they are a Python loop over
pairs. `later-in-alphabet` stays at the container door for two reasons that
both bite. Its two clauses are ALTERNATIVES, and stacked `@m.define` clauses
read as first-match, which would make the recursive one unreachable; and the
second clause's `$Z` appears in neither head, while a free name in a compiled
body is a parameter, a known function or a data constructor, never a fresh
variable. So the equation is built as the term it is, with `&` for `and`.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import REFLECTION_SPACE, TRUE, Expression, S, V, equation

#: Six letters, each with the one before it.
SUCCESSORS = ((S.b, S.a), (S.c, S.b), (S.d, S.c), (S.e, S.d), (S.f, S.e), (S.g, S.f))

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9036 to 7849, -1187 (-13.1%), by the twin contract
#: change: the `test` wrapper and the `collapse` left the engine for Python's
#: own `assert` and the answer list `m.eval` already hands back, and the two
#: `add-atom` forms became `space += atom`. The closure search itself did not
#: move. Against the example's 16678 the ratio is 0.4706 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure examples/reasoning/logicprog.metta`].
#: Prior: ADDED 2026-08-22 at 9036 by the wave-3 twin baseline.
BUDGET = 7849


def twin(m):
    """State six facts, close them transitively, and search backwards."""
    # Reaching either relation's unmatched boundary must FAIL the search rather
    # than answering the P3 residual-call dispatch value.
    reflection = m.space(REFLECTION_SPACE)
    reflection += S["dispatch-policy"](S.successor, S.NoMatchEnum, S.NoMatchFail)
    reflection += S["dispatch-policy"](S["later-in-alphabet"], S.NoMatchEnum, S.NoMatchFail)

    for after, before in SUCCESSORS:
        m += equation(S.successor(after, before)).to(TRUE)

    m += equation(S["later-in-alphabet"](V.X, V.Y)).to(S.successor(V.X, V.Y))
    m += equation(S["later-in-alphabet"](V.X, V.Y)).to(
        S.successor(V.X, V.Z) & S["later-in-alphabet"](V.Z, V.Y)
    )

    # Asking with the second argument open enumerates every letter before d,
    # nearest first, each paired with the True its clause answered.
    assert m.eval((S["later-in-alphabet"](S.d, V.earlier), V.earlier)) == [
        Expression((TRUE, S.c)), Expression((TRUE, S.b)), Expression((TRUE, S.a)),
    ]
