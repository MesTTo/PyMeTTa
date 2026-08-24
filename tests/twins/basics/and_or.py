"""Purpose: examples/basics/and_or.metta in Python: the boolean connectives.

`(and true false)` is False, so `(or ... true)` is True and the original's
`if` takes its first branch. The public `and_`, `or_`, and `if_` builders use
Python's sanctioned trailing underscore for keywords and build the stored
engine terms directly.

`m.answers(term).one()` is the cardinality door: exactly one answer, decoded
to the Python bool the conditional expression then reads.

Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import FALSE, TRUE, and_, if_, or_

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1


def twin(m):
    """Reduce the connectives in the engine, then choose in Python."""
    # (or (and true false) true)
    assert m.answers(if_(or_(and_(TRUE, FALSE), TRUE), 1, 2)).one() == 1
