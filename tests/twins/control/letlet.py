"""Purpose: examples/control/letlet.metta in Python: a destructuring binding.

The `let*` binding here is a PATTERN, `(($f1 $c1 3) (1 2 $d1))`: three
variables and a literal on the left meeting three values on the right, so `$f1`
and `$c1` bind leftwards while `$d1` binds rightwards from the literal 3. The
answer is `(1 2 3)`.

Python spells the left-to-right half `f1, c1, _ = 1, 2, d1`, and a compiled
body refuses even that: "a compiled body binds plain names; destructuring and
attribute assignment have no let* form". Filed as residue against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, V, equation

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let*` binding whose left side is a PATTERN has no assignment spelling"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1709 to 1036, -673 (-39.4%), by the twin contract
#: change: the `test` wrapper LEFT the engine for `assert`, and the answer is
#: compared as an atom in Python rather than by an engine `test`. Measured
#: min-of-3 over fresh processes with the MORK backend linked in, which the
#: artefact-free worktree omits and which moves a compiled twin by about 10
#: inferences per definition; against the example's 3689 the ratio is 0.2808.
#: Prior: 1709, the transliterated twin this replaces.
BUDGET = 1036


def twin(m):
    """Unify a three-element pattern with a three-element value."""
    # (= (f) (let* ((($f1 $c1 3) (1 2 $d1))) ($f1 $c1 $d1)))
    m += equation(S.f()).to(
        S["let*"](
            (((V.f1, V.c1, 3), (1, 2, V.d1)),),
            (V.f1, V.c1, V.d1),
        )
    )

    # !(test (f) (1 2 3))
    assert m.eval(S.f()) == [Expression((1, 2, 3))]
