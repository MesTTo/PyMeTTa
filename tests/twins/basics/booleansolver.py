"""Purpose: examples/basics/booleansolver.metta in Python: solving for a boolean.

`and` and `or` are generate-and-test over two values, so an unbound variable
in one is SOLVED FOR rather than read, and one form answers twice. The public
`and_`, `or_`, and `if_` builders preserve that relational term at the term
door, while `V.x` is the variable `$x`.

The answers are pairs, so Python reads them as pairs: an expression is a
sequence and `tuple(pair)` is the unpacking.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import TRUE, V, and_, if_, or_

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1


def twin(m):
    """Ask which pairs of booleans satisfy the condition."""
    # (if (and (or $x True) $y) ($x $y)): the two-argument `if` is the FILTER
    # that turns a solved condition into the pair that solved it, and nothing
    # where it does not hold.
    solutions = m.eval(if_(and_(or_(V.x, TRUE), V.y), (V.x, V.y)))
    assert [tuple(pair) for pair in solutions] == [(True, True), (False, True)]
