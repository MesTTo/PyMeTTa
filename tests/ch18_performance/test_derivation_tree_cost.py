"""Purpose: keep proof consumers linear and independent of recursion depth.

Guarantees:
  - recursive parser and traversal controls fail on a depth-2,000 chain while
    current consumers return every node [tested:
    test_recursive_derivation_controls_capture_the_depth_ceiling;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - fact and rule projection use bounded hash comparisons and preserve
    first-seen order [tested:
    test_fact_and_rule_projection_use_hash_membership;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
  - branching construction retains the recursive parser's child order [tested:
    test_iterative_derivation_parser_preserves_branching_order;
    commit=9903250d082ab019535ab0c10b742053f9e640f0]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from benchmarks.derivation_trees import (
    derivation_atom,
    measure_depth,
    recursive_from_atom,
)
from metta import Expression, S
from metta.derivation import Builtin, Derivation, Fact, Step, Truncated


def test_recursive_derivation_controls_capture_the_depth_ceiling():
    """Only the retained recursive controls fail at depth 2,000."""
    row = measure_depth(2_000, rounds=1)

    assert row.recursive_parse_us is None
    assert row.recursive_walk_us is None
    assert row.current_parse_us is not None
    assert row.current_walk_us is not None


def test_fact_and_rule_projection_use_hash_membership(monkeypatch):
    """Two passes over 400 values use linear equality work and keep order."""
    count = 400
    facts = tuple(Fact("&self", S.item(index)) for index in range(count))
    proof = Derivation(S.root, S.answer, (*facts, *facts))
    fact_comparisons = 0
    original_fact_eq = Fact.__eq__

    def counted_fact_eq(left, right):
        nonlocal fact_comparisons
        fact_comparisons += 1
        return original_fact_eq(left, right)

    monkeypatch.setattr(Fact, "__eq__", counted_fact_eq)
    projected = proof.facts

    assert fact_comparisons <= count * 2
    assert [fact.atom for fact in projected] == [S.item(i) for i in range(count)]

    equations = tuple(Expression(S.rule, index) for index in range(count))
    equal_equations = tuple(Expression(S.rule, index) for index in range(count))
    steps = tuple(Step(S.call, S.answer, equation) for equation in (*equations, *equal_equations))
    proof = Derivation(S.root, S.answer, steps)
    rule_comparisons = 0
    original_expression_eq = Expression.__eq__

    def counted_expression_eq(left, right):
        nonlocal rule_comparisons
        rule_comparisons += 1
        return original_expression_eq(left, right)

    monkeypatch.setattr(Expression, "__eq__", counted_expression_eq)
    projected_rules = proof.rules

    assert rule_comparisons <= count * 2
    assert projected_rules == list(equations)


def test_iterative_derivation_parser_preserves_branching_order():
    """A step's mixed children keep their source order after reconstruction."""
    tree = derivation_atom(2)
    answer = tree[1]
    branch = Expression(
        S.step,
        Expression(S.call, S.branch, S.out),
        Expression(S["="], S.branch, S.out),
        Expression(S.fact, S["&self"], S.first),
        Expression(S.builtin, "second"),
        Expression(S.truncated, "third"),
    )
    planted = Expression(S.derivation, answer, tree[2], branch)

    actual = Derivation.from_atom(planted)
    expected = recursive_from_atom(planted)

    assert actual == expected
    assert isinstance(actual.children[1], Step)
    assert [type(node) for node in actual.children[1].children] == [
        Fact,
        Builtin,
        Truncated,
    ]
