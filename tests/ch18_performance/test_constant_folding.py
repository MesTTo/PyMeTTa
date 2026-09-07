"""Purpose: verify retained constant planning through the public evaluator.

Guarantees:
  - source replacement invalidates a folded dependency, and generated
    arithmetic preserves complete bags against a variable-input reference
    [tested: test_folded_dependencies_rebuild_after_override_and_removal,
    test_generated_constant_expressions_preserve_answer_bags; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
  - immutable host declarations do not force an undemanded call at load time
    [tested: test_host_calls_remain_deferred; commit=3c64e2e24787362a5a5081513bc24b880711a1d7]
"""

from collections import Counter

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import MeTTa


def test_folded_dependencies_rebuild_after_override_and_removal():
    """The retained source rebuilds a folded caller when its native name changes.

    The overridden name is abs-math rather than +, which is equally foldable
    and is not one of Prolog's own predicates. Whether a space may define over
    a core predicate depends on what else has lived in the process: the same
    override is accepted in a fresh interpreter and refused after the space
    suite has run, on this tree and on the trunk alike, so a fixture built on
    it tests the process's history rather than this rebuild.
    """
    with MeTTa() as m:
        m.run("(= (folding-source-dependency) (abs-math -3))")
        assert m.run("!(folding-source-dependency)") == [[3]]
        m.run("(= (abs-math -3) 42)")
        assert m.run("!(folding-source-dependency)") == [[42]]
        m.run("!(remove-atom &self (= (abs-math -3) 42))")
        assert m.run("!(folding-source-dependency)") == [[3]]


@pytest.mark.parametrize("effect", ["immutable", "readOnlyLookup", "oracleIO"])
def test_host_calls_remain_deferred(effect):
    """A declaration about effects supplies no proof of termination or lifetime."""
    calls = []
    with MeTTa() as m:

        @m.op(name="folding-deferred-host", effect=effect)
        def host(value: int) -> int:
            calls.append(value)
            return value + 1

        m.run(
            "(= (folding-latent-host) (if False (folding-deferred-host 7) (+ 1 2))) "
            "(= (folding-demanded-host) (folding-deferred-host 7))"
        )
        assert calls == []
        assert m.run("!(folding-latent-host)") == [[3]]
        assert calls == []
        for _ in range(3):
            assert m.run("!(folding-demanded-host)") == [[8]]
        assert calls == [7, 7, 7]


def test_duplicate_host_answers_survive_a_folded_constant():
    """A scalar folded inside an enumerator retains every generator occurrence."""
    with MeTTa() as m:

        @m.op(name="folding-duplicates-host", effect="nondeterministicReadOnly")
        def host(value: int):
            yield value
            yield value

        m.run("(= (folding-duplicate-context) (let $x (folding-duplicates-host 8) (+ 3 4)))")
        assert m.run("!(folding-duplicate-context)") == [[7, 7]]


_EXPRESSIONS = st.recursive(
    st.integers(-30, 30),
    lambda child: st.tuples(
        st.sampled_from(["+", "-", "*", "%", "floor-div", "min", "max"]),
        child,
        child,
    ),
    max_leaves=12,
)


def _expression_source(expression, dynamic):
    if isinstance(expression, int):
        return f"(+ $zero {expression})" if dynamic else str(expression)
    operation, left, right = expression
    return (
        f"({operation} {_expression_source(left, dynamic)} "
        f"{_expression_source(right, dynamic)})"
    )


@given(expression=_EXPRESSIONS, occurrences=st.lists(st.integers(0, 3), max_size=7))
@settings(max_examples=50)
def test_generated_constant_expressions_preserve_answer_bags(expression, occurrences):
    """Variable leaves force the reference through runtime arithmetic and errors."""
    choices = " ".join(map(str, occurrences))
    constant = _expression_source(expression, dynamic=False)
    residual = _expression_source(expression, dynamic=True)
    with MeTTa() as m:
        m.run(
            f"(= (folding-generated-fast) (let $x (superpose ({choices})) {constant})) "
            f"(= (folding-generated-reference $zero) "
            f"(let $x (superpose ({choices})) {residual}))"
        )
        actual = m.run("!(folding-generated-fast)")[0]
        expected = m.run("!(folding-generated-reference 0)")[0]
        assert Counter(map(str, actual)) == Counter(map(str, expected))
