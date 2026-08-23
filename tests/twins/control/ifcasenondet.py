"""Purpose: examples/control/ifcasenondet.metta in Python: a nondeterministic test.

`if` and `case` both take their condition from an ordinary expression, so a
condition that answers three times makes the whole form answer three times.
Nondeterminism is not a special case here; it is what an argument position
already is.

`if-nondet` is that in Python: a `for` loop over the argument IS
`(superpose $y)`, and the conditional expression inside it is the `if`, so the
compiled equation comes out as the original's own shape. `case-nondet` is the
same program through `case`, which is what Python's `match` statement would
spell and the compiled subset has no lowering for (P14.4), so writing it as an
`if` would only repeat the line above it.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, S, V, equation

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=e59442d0e96847cf3a4a0a8bf9686e9f38fee2d1].
BUDGET = 1


def twin(m):
    """Give a condition three answers, twice."""
    @m.define(name="if-nondet")
    def if_nondet(y):
        # (= (if-nondet $y) (if (superpose $y) a b))
        for flag in y:
            yield S.a if flag else S.b

    # !(test (collapse (if-nondet (True False True))) (a b a))
    assert if_nondet((True, False, True)) == [S.a, S.b, S.a]

    # The top rung is the same loop above with a `match` statement inside,
    # which is what a MeTTa `case` is:
    #
    #     @m.define(name="case-nondet")
    #     def case_nondet(y):
    #         for flag in y:
    #             match flag:
    #                 case True: yield S.a
    #                 case False: yield S.b
    #
    # `ast.Match` has no lowering in the compiled subset. Residue: P14.4.
    # (= (case-nondet $y) (case (superpose $y) ((True a) (False b))))
    cases = S.case(S.superpose(V.y), ((TRUE, S.a), (FALSE, S.b)))  # rung: a `case` over patterns is Python's `match` statement, which has no lowering
    m += equation(S["case-nondet"](V.y)).to(cases)

    # !(test (collapse (case-nondet (True False True))) (a b a))
    assert m.eval(S["case-nondet"]((TRUE, FALSE, TRUE))) == [S.a, S.b, S.a]
