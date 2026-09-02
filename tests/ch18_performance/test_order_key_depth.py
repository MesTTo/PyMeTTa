"""Purpose: keep atom ordering independent of Python's recursion limit.

Guarantees:
  - order_key, sorted, min, max, and all four rich comparisons answer at 600
    expression levels [tested:
    test_deep_atom_ordering_uses_a_constant_python_call_stack;
    commit=WORKTREE]
  - expression-prefix ordering remains childwise at the same depth [tested:
    test_deep_expression_prefixes_keep_childwise_order;
    commit=WORKTREE]
  - the durable recursive reference retains the removed failure at depth 600
    [tested: test_recursive_reference_captures_the_removed_depth_failure;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from benchmarks.order_key_depth import measure, nested
from metta import Expression, G, S
from metta.atoms import order_key


def test_deep_atom_ordering_uses_a_constant_python_call_stack():
    """All public ordering operations answer beyond the recursion limit."""
    left = nested(600, G(1))
    right = nested(600, G(2))

    assert order_key(left) < order_key(right)
    ordered = sorted((right, left))
    assert ordered[0] is left
    assert ordered[1] is right
    assert min(right, left) is left
    assert max(left, right) is right
    assert left < right
    assert left <= right
    assert right > left
    assert right >= left


def test_deep_expression_prefixes_keep_childwise_order():
    """An exhausted child list sorts before another child at depth 600."""
    short = nested(600, Expression((S.f, G(1))))
    long = nested(600, Expression((S.f, G(1), G(2))))

    assert order_key(short) < order_key(long)
    assert short < long


def test_recursive_reference_captures_the_removed_depth_failure():
    """The benchmark keeps a measurable form of the former implementation."""
    row = measure(600, repetitions=1, rounds=1)

    assert row.recursive_microseconds is None
    assert row.current_microseconds is not None
    assert row.current_items == 1_801
