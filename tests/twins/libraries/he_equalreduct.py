"""examples/libraries/he_equalreduct.metta in Python: equality and reduction, HE's vocabulary.

`=alpha` is equality modulo a consistent renaming of variables, and that
relation belongs to the atom: `a.alpha_eq(b)` is the method, so the two claims
about it are ordinary Python truth tests and the twin never spells the MeTTa
head. `id` and `if-equal` are lib_he's own functions and stay named.

`(= (add 1 2) 3)` goes to the container door. Its head carries LITERAL
arguments, and a decorated Python function's parameters are always variables,
so `@m.define` would store `(= (add $x $y) 3)`, a different equation.
"""

from metta import G, S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Store an equation with a literal head, then ask three equality questions."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    m += equation(S.add(1, 2)).to(3)

    assert m.fn.id(5) == [5]

    # Alpha equality is equality up to a consistent renaming of variables.
    assert S.Father(V.X).alpha_eq(S.Father(V.Y))
    assert not S.Father(V.X).alpha_eq(S.Son(V.X))

    assert m.fn.if_equal(1, 1, G("Equal"), G("Not Equal")) == [G("Equal")]
