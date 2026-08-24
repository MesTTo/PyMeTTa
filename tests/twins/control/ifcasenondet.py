"""Purpose: examples/control/ifcasenondet.metta in Python: a nondeterministic test.

`if` and `case` both take their condition from an ordinary expression, so a
condition that answers three times makes the whole form answer three times.
Nondeterminism is not a special case here; it is what an argument position
already is.

Both equations compile, and both keep the original's own shape: `if-nondet` is
Python's conditional expression and `case-nondet` is Python's `match`
statement, which is what a MeTTa `case` is.

The condition is `fn.superpose(y)`, the superposition OF a bound expression.
The ruled expression-position spelling for that is `superpose(*y)`, the guide's
own star form, and it refuses: "Starred has no MeTTa equivalent in the compiled
subset" [measured 2026-08-24; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. `superpose(y)` is not the same
operation, it wraps `$y` as a single alternative, so the descent goes one rung
to the function namespace, where naming the instruction reaches it exactly.
Filed as residue against P14.4, the same gap control/supercollapse.metta
records.
Guarantees:
  - TRUE and FALSE used here are package values rather than local
    reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, S, fn

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Give a condition three answers, twice."""
    @m.define
    def if_nondet(y):
        # (= (if-nondet $y) (if (superpose $y) a b))
        return S.a if fn.superpose(y) else S.b

    # !(test (collapse (if-nondet (True False True))) (a b a))
    assert if_nondet((TRUE, FALSE, TRUE)) == [S.a, S.b, S.a]

    @m.define
    def case_nondet(y):
        # (= (case-nondet $y) (case (superpose $y) ((True a) (False b))))
        match fn.superpose(y):
            case True:
                return S.a
            case False:
                return S.b

    # !(test (collapse (case-nondet (True False True))) (a b a))
    assert case_nondet((TRUE, FALSE, TRUE)) == [S.a, S.b, S.a]
