"""Purpose: examples/basics/booleansolver.metta in Python: solving for a boolean.

`and` and `or` are generate-and-test over two values, so an unbound variable
in one is SOLVED FOR rather than read, and one form answers twice. `|` and `&`
build those connectives at the term door, and `V.x` is the variable `$x`.

Two walls, and both are why this is a term rather than a decorated function.
Python's `and` and `or` are keywords, so a compiled body cannot name MeTTa's;
and Python's own `and` in a body lowers to a `py-truthy` short circuit, which
tests a value and never generates one, so a compiled `if x and y: yield ...`
answers once with both variables still unbound instead of enumerating the
solutions. Measured on this engine 2026-08-22.

The answers are pairs, so Python reads them as pairs: an expression is a
sequence and `tuple(pair)` is the unpacking.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, S, V

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Ask which pairs of booleans satisfy the condition."""
    # (if (and (or $x True) $y) ($x $y)): the two-argument `if` is the FILTER
    # that turns a solved condition into the pair that solved it, and nothing
    # where it does not hold.
    solutions = m.eval(S["if"]((V.x | TRUE) & V.y, (V.x, V.y)))  # rung: two-argument if
    assert [tuple(pair) for pair in solutions] == [(True, True), (False, True)]
