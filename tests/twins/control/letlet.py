"""Purpose: examples/control/letlet.metta in Python: a destructuring binding.

The `let*` binding here is a PATTERN, `(($f1 $c1 3) (1 2 $d1))`: three
variables and a literal on the left meeting three values on the right, so `$f1`
and `$c1` bind leftwards while `$d1` binds rightwards from the literal 3. The
answer is `(1 2 3)`.

Python spells the left-to-right half `f1, c1, _ = 1, 2, d1`, and a compiled
body refuses even that: "a compiled body binds plain names; destructuring and
attribute assignment have no let* form" [re-measured 2026-08-24;
commit=028b41a056cfd706e516cd0b945cbf69ac066da7]. Nor does `solve`, the `let` door for a pattern that must win
variables, reach into a body: it is a module function and the subset reads only
its own names there. So the equation is stated as the term it is and filed
against P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=028b41a056cfd706e516cd0b945cbf69ac066da7]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import Expression, S, V, equation

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let*` binding whose left side is a PATTERN has no assignment spelling"

#: PLACEHOLDER, never measured in this worktree: the integrator's single
#: re-pin pass prices the whole corpus under the lane's own protocol after the
#: wave merges [assumed: BUDGET states no measured cost; commit=028b41a056cfd706e516cd0b945cbf69ac066da7].
BUDGET = 1


def twin(m):
    """Unify a three-element pattern with a three-element value."""
    # The top rung is Python's own destructuring assignment, which IS a
    # `let*` binding whose left side is a pattern:
    #
    #     @m.define
    #     def f():
    #         f1, c1, _three = 1, 2, d1
    #         return f1, c1, d1
    #
    # A compiled body refuses it: "a compiled body binds plain names;
    # destructuring and attribute assignment have no let* form", and even
    # then the assignment carries only the left-to-right half. Residue: P14.4.
    # (= (f) (let* ((($f1 $c1 3) (1 2 $d1))) ($f1 $c1 $d1)))
    m += equation(S.f()).to(
        S["let*"](
            (((V.f1, V.c1, 3), (1, 2, V.d1)),),
            (V.f1, V.c1, V.d1),
        )
    )

    # !(test (f) (1 2 3))
    assert m.eval(S.f()) == [Expression((1, 2, 3))]
