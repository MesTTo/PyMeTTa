"""Purpose: examples/reasoning/logicprog.metta in Python: a recursive relation over facts.

Six successor facts and a transitive closure over them, asked backwards: which
letters come before `d`. The two dispatch policies go into the reflection space
through the ordinary write door, `space += atom`, because that is what
`add-atom` is; `petta.reflection` IS that space, so the `&petta` symbol is
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

import petta
from petta import TRUE, Expression, S, V, equation

#: Six letters, each with the one before it.
SUCCESSORS = ((S.b, S.a), (S.c, S.b), (S.d, S.c), (S.e, S.d), (S.f, S.e), (S.g, S.f))

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """State six facts, close them transitively, and search backwards."""
    # Reaching either relation's unmatched boundary must FAIL the search rather
    # than answering the P3 residual-call dispatch value.
    reflection = petta.reflection
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
