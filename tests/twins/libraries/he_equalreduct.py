"""examples/libraries/he_equalreduct.metta in Python: equality and reduction, HE's vocabulary.

`=alpha` is equality modulo a consistent renaming of variables, and that
relation belongs to the atom: `a.alpha_eq(b)` is the method, so the two claims
about it are ordinary Python truth tests and the twin never spells the MeTTa
head. `id` and `if-equal` are lib_he's own functions and stay named.

`(= (add 1 2) 3)` goes to the container door. Its head carries LITERAL
arguments, and a decorated Python function's parameters are always variables,
so `@m.define` would store `(= (add $x $y) 3)`, a different equation.

That head keeps the BRACKET, and this is the one place in the folder where the
choice is load-bearing. `add` is one of the operator words, so the attribute
door reads `S.add` as `+` and would store `(= (+ 1 2) 3)`, an equation about
addition instead of about the symbol the example defines. Rung 5's bracket is
the exact door, so `S["add"]` is the head literally named `add`.
"""

from metta import G, S, V, equation

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1


def twin(m):
    """Store an equation with a literal head, then ask three equality questions."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    m += equation(S["add"](1, 2)).to(3)

    assert m.fn.id(5) == [5]

    # Alpha equality is equality up to a consistent renaming of variables.
    assert S.Father(V.X).alpha_eq(S.Father(V.Y))
    assert not S.Father(V.X).alpha_eq(S.Son(V.X))

    assert m.fn.if_equal(1, 1, G("Equal"), G("Not Equal")) == [G("Equal")]
