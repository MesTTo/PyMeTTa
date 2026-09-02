"""Purpose: keep stacked-definition publication linear in clause count.

Guarantees:
  - a disjoint clause publishes only its own main and helper equations in one
    engine call [tested: test_stacked_definition_writes_scale_with_the_new_clause;
    commit=9b6695455c30809c75267c50a5137e38925af386]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from benchmarks.definition_stacking_crossings import rows


def test_stacked_definition_writes_scale_with_the_new_clause():
    """Unchanged physical equations never cross the engine again."""
    small, large = rows((4, 8))

    assert small.crossings == small.clauses
    assert large.crossings == large.clauses
    assert small.transported == 2 * small.clauses
    assert large.transported == 2 * large.clauses
