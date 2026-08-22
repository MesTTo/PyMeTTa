"""examples/libraries/he_equalreduct.metta in Python: equality and reduction, HE's vocabulary.

`=alpha` has a Python name already: `petta.alpha_eq`, whose own docstring calls
it "PeTTa's =alpha", so the two claims about it are ordinary Python truth tests
and the twin never spells the MeTTa head. `id` and `if-equal` are lib_he's own
functions and stay named.

`(= (add 1 2) 3)` goes to the container door. Its head carries LITERAL
arguments, and a decorated Python function's parameters are always variables,
so `@m.define` would store `(= (add $x $y) 3)`, a different equation.
"""

from petta import S, V, alpha_eq, equation, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 11367 to 7441, -3926 (-34.54%), by the idiomatic
#: rewrite: the two `=alpha` claims left the engine entirely for
#: `petta.alpha_eq`, whose own docstring names it PeTTa's =alpha, and four
#: `test` wrappers went with them. Measured min-of-three with the MORK
#: backend linked into this worktree, which the earlier figure may not have
#: been. Prior: 11367 was the last figure for the generator twin that yielded
#: `m.eval(S.test(...))` once per runnable form.
BUDGET = 7441


def twin(m):
    """Store an equation with a literal head, then ask three equality questions."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    m += equation(S.add(1, 2)).to(3)

    assert m.fn("id")(5) == 5

    # Alpha equality is equality up to a consistent renaming of variables.
    assert alpha_eq(S.Father(V.X), S.Father(V.Y))
    assert not alpha_eq(S.Father(V.X), S.Son(V.X))

    assert m.fn("if-equal")(1, 1, val("Equal"), val("Not Equal")) == val("Equal")
