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

The two answers are capitalised. A compiled body reads a lowercase free name
as a function and a capitalised one as data, which case2 records against
P14.4.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3789 to 5441, +1652 (+43.6%), by the twin contract
#: change: `if-nondet` ENTERED the engine as a compiled `for` loop over its
#: argument with a conditional expression inside, which is the original's own
#: shape, and pays `@m.define`'s fixed registration; two `test`s and two
#: collapses LEFT for `assert`s and lists. Measured min-of-3 over fresh
#: processes with the MORK backend linked in, which the artefact-free
#: worktree omits and which moves a compiled twin by about 10 inferences per
#: definition; against the example's 7251 the ratio is 0.7504. Prior: 3789,
#: the transliterated twin this replaces.
BUDGET = 5441


def twin(m):
    """Give a condition three answers, twice."""
    @m.define(name="if-nondet")
    def if_nondet(y):
        # (= (if-nondet $y) (if (superpose $y) a b))
        for flag in y:
            yield A if flag else B  # noqa: F821  -- capitalised free names in a compiled body are MeTTa data, which has no Python value to bind

    # !(test (collapse (if-nondet (True False True))) (a b a))
    assert if_nondet((True, False, True)) == [S.A, S.B, S.A]

    # (= (case-nondet $y) (case (superpose $y) ((True a) (False b))))
    cases = S.case(S.superpose(V.y), ((TRUE, S.a), (FALSE, S.b)))  # rung: a `case` over patterns is Python's `match` statement, which has no lowering
    m += equation(S["case-nondet"](V.y)).to(cases)

    # !(test (collapse (case-nondet (True False True))) (a b a))
    assert m.eval(S["case-nondet"]((TRUE, FALSE, TRUE))) == [S.a, S.b, S.a]
