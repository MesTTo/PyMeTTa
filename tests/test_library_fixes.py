"""Purpose: pin the library defects exposed by the P14 twin authoring wave.

Guarantees:
  - a bound call whose resolved MeTTa name ends in ``!`` completes its effect
    before the Python call returns [tested: test_resolved_bang_call_is_eager;
    commit=WORKTREE]
  - bound calls expose evaluation values through iteration and scalar doors,
    with caller bindings retained on their row and projection faces both in
    and out of a stats scope [tested: test_calls_keep_values_and_binding_rows;
    commit=WORKTREE]
  - all four rich comparisons use the engine's total atom order, reject raw
    mixed operands symmetrically, and leave comparison terms to explicit
    symbol construction [tested: test_atom_comparisons_are_only_ordering;
    commit=WORKTREE]
  - builtin discovery is cached per logical space and invalidated after every
    function-catalog mutation [tested: test_builtin_discovery_is_cached,
    test_builtin_cache_invalidates_after_a_miss; commit=WORKTREE]
  - rational number payloads cross lazy values and binding rows exactly as
    ``Fraction`` [tested: test_rational_payloads_cross_the_scalar_door;
    commit=WORKTREE]
  - one defined MeTTa name may own independent Python clauses at different
    arities [tested: test_define_supports_one_name_at_multiple_arities;
    commit=WORKTREE]
  - compiled bodies call a host-bound sibling Defined through that object's
    own MeTTa name [tested: test_compiled_body_calls_renamed_defined_sibling;
    commit=WORKTREE]
  - function handles and Defined objects suspend endless producers between
    requested answers [tested: test_function_calls_suspend_endless_producers;
    commit=WORKTREE]
  - a grounded atom participates in term-building operators instead of
    computing as its carried Python value [tested:
    test_grounded_atoms_lift_python_operators_to_terms; commit=WORKTREE]
  - an Answers view used as a term operand is observed through exact-one
    cardinality, making deterministic calls nest and refusing ambiguity
    [tested: test_answer_views_observe_when_used_as_operands; commit=WORKTREE]
  - eager Rows and lazy Answers share attribute and Variable projection
    spellings [tested: test_rows_share_the_answer_projection_contract;
    commit=WORKTREE]
  - the public space factory accepts a space-name Symbol returned by the
    engine [tested: test_space_factory_accepts_a_name_symbol; commit=WORKTREE]
  - relational solve returns variables introduced by either its winning
    pattern or its producing subject [tested:
    test_solve_projects_variables_from_the_winning_pattern; commit=WORKTREE]
  - waiting on a space loads Linda support in the caller context without
    adding library definitions to the waited-on space [tested:
    test_peek_does_not_import_linda_into_the_waited_space; commit=WORKTREE]
"""

from fractions import Fraction
from pathlib import Path

import pytest

from petta import TRUE, UNIT, Expression, G, S, V, space
from petta.atoms import order_key
from petta.errors import EngineError


def test_resolved_bang_call_is_eager(tmp_path: Path) -> None:
    """A statement-like import is complete without observing its answers."""
    source = tmp_path / "eager-effect.metta"
    source.write_text("(= (libfix-eager-effect) eager)\n", encoding="utf-8")
    target = space()

    answers = target.fn["import!"](target, str(source))

    assert target.eval(S["libfix-eager-effect"]()) == [S.eager]
    assert list(answers) == [UNIT]


def test_calls_keep_values_and_binding_rows() -> None:
    """Values and bindings stay available through distinct answer faces."""
    target = space()
    target.run(
        "(libfix-answer-fact 41)\n"
        "(= (libfix-answer-pick $x) "
        "(match &self (libfix-answer-fact $x) True))"
    )

    answers = target.fn["libfix-answer-pick"](V.x)

    assert list(answers) == [TRUE]
    assert list(answers.x) == [G(41)]
    assert answers.rows[0].x == G(41)
    assert answers.one() is True

    @target.define(name="libfix-defined-truth")
    def defined_truth(_value):
        return True

    outside = defined_truth(V.value)
    with target.stats():
        inside = defined_truth(V.value)

    assert outside.one() is True
    assert inside.one() is True


def test_atom_comparisons_are_only_ordering() -> None:
    """Rich comparisons order atoms; an explicit head builds a condition."""
    atoms = [S.z, V.a, Expression(S.f, 1), G(2)]
    for left in atoms:
        for right in atoms:
            expected_left = order_key(left)
            expected_right = order_key(right)
            assert (left < right) is (expected_left < expected_right)
            assert (left <= right) is (expected_left <= expected_right)
            assert (left > right) is (expected_left > expected_right)
            assert (left >= right) is (expected_left >= expected_right)

    with pytest.raises(TypeError):
        _ = V.a < 2
    with pytest.raises(TypeError):
        _ = 2 > V.a

    pool = space()
    pool.add(S.present())
    guard = S["<"](
        S["space-atom-count"](pool), S["car-atom"](Expression(2))
    )
    assert pool.eval(guard) == [TRUE]


def test_builtin_discovery_is_cached() -> None:
    """A second namespace lookup does not enumerate the engine catalogue."""
    target = space()
    with target.stats() as first:
        first_handle = target.fn.car_atom
    with target.stats() as second:
        second_handle = target.fn.cdr_atom

    assert first_handle.__name__ == "car-atom"
    assert second_handle.__name__ == "cdr-atom"
    assert second.inferences < first.inferences // 10


def test_builtin_cache_invalidates_after_a_miss(tmp_path: Path) -> None:
    """Registration, definition, and import cannot hide behind stale misses."""
    target = space()
    operation_name = "libfix-late-operation"
    assert operation_name not in target.builtins()

    @target.op(name=operation_name)
    def late_operation(value):
        return value

    assert operation_name in target.builtins()
    target.unregister_op(operation_name)
    assert operation_name not in target.builtins()

    definition_name = "libfix-late-definition"

    @target.define(name=definition_name)
    def late_definition(value):
        return value

    assert definition_name in target.builtins()

    import_name = "libfix-late-import"
    source = tmp_path / "late-import.metta"
    source.write_text(f"(= ({import_name}) imported)\n", encoding="utf-8")
    target.fn["import!"](target, str(source))
    assert import_name in target.builtins()


def test_rational_payloads_cross_the_scalar_door() -> None:
    """A rational in a value or a parallel binding retains exactness."""
    target = space()
    target.run("!(import! &self (library lib_constraints))")
    rational = Fraction(1, 2)
    represented = target.parse(
        "(let True (clpq (= (* 2 $x) 1)) (repr $x))"
    )
    value = target.parse("(let True (clpq (= (* 2 $x) 1)) $x)")

    assert target.answers(represented).one() == "1r2"
    assert target.answers(value).one() == rational
    assert target.answers(G(rational)).one() == rational


def test_define_supports_one_name_at_multiple_arities() -> None:
    """Different arities stack and dispatch independently in engine and twin."""
    target = space()

    @target.define(name="libfix-multi-arity")
    def unary_clause(value):
        return value + 1

    @target.define(name="libfix-multi-arity")
    def binary_clause(left, right):
        return left + right

    assert unary_clause(3).one() == 4
    assert binary_clause(3, 4).one() == 7
    assert unary_clause.py(3) == 4
    assert binary_clause.py(3, 4) == 7


def test_compiled_body_calls_renamed_defined_sibling() -> None:
    """A sibling's Python binding resolves to its declared MeTTa head."""
    target = space()

    @target.define(name="libfix-sibling-head")
    def python_sibling(value):
        return value + 1

    @target.define(name="libfix-sibling-caller")
    def sibling_caller(value):
        return python_sibling(value)

    assert sibling_caller(4).one() == 5
    assert "(libfix-sibling-head $value)" in sibling_caller.source()


def test_function_calls_suspend_endless_producers() -> None:
    """Each cursor pull resumes rather than materialising an endless source."""
    target = space()
    target.run(
        "(= (libfix-stream-from $n) "
        "(superpose ($n (libfix-stream-from (+ $n 1)))))"
    )
    handle = target.fn["libfix-stream-from"]

    # Warm the cursor shim so this test measures producer suspension.  Its
    # one-time installation cost has its own regression in fix 24.
    assert list(handle(0)[:1]) == [G(0)]
    with target.stats() as engine_cost:
        expected = target.eval(S.take(4, S["libfix-stream-from"](0)))
    with target.stats() as handle_cost:
        actual = list(handle(0)[:4])

    @target.define(name="libfix-defined-stream-from")
    def defined_count_up(n):
        yield n
        yield from defined_count_up(n + 1)

    with target.stats() as defined_cost:
        defined_actual = list(defined_count_up(0)[:4])

    assert expected == actual == defined_actual == [G(0), G(1), G(2), G(3)]
    assert handle_cost.inferences < engine_cost.inferences
    assert defined_cost.inferences < engine_cost.inferences


def test_grounded_atoms_lift_python_operators_to_terms() -> None:
    """G(value) is the explicit bridge from Python data to staged syntax."""
    target = space()

    assert G(1) + 2 == S["+"](1, 2)
    assert 2 + G(1) == S["+"](2, 1)
    assert -G(1) == S["-"](0, 1)
    assert target.answers(G(1) + 2).one() == 3


def test_answer_views_observe_when_used_as_operands() -> None:
    """Term construction is the explicit observation point for a view."""
    target = space()
    target.run(
        "(= (libfix-inner $x) (+ $x 1))\n"
        "(= (libfix-outer $x) (* $x 2))\n"
        "(= (libfix-many) (superpose (1 2)))"
    )

    nested = target.fn["libfix-outer"](target.fn["libfix-inner"](2))

    assert nested.one() == 6
    with pytest.raises(EngineError, match="exactly one answer"):
        target.fn["libfix-outer"](target.fn["libfix-many"]())


def test_rows_share_the_answer_projection_contract() -> None:
    """Both answer containers project caller variables the same two ways."""
    target = space()
    target += S["libfix-projection"](1)
    target += S["libfix-projection"](2)

    rows = target.query(S["libfix-projection"](V.value))

    assert rows.value == rows[V.value] == [G(1), G(2)]
    with pytest.raises(TypeError):
        _ = rows["value"]


def test_space_factory_accepts_a_name_symbol() -> None:
    """A space name returned as an atom opens directly without str()."""
    name = S["&libfix-symbol-space"]

    opened = space(name)

    assert opened.name == name.name


def test_solve_projects_variables_from_the_winning_pattern() -> None:
    """A pattern-only variable is a result column, as relational let requires."""
    target = space()

    solved = target.solve(S["libfix-solved"](V.value), S["libfix-solved"](42))

    assert solved.value == G(42)


def test_peek_does_not_import_linda_into_the_waited_space() -> None:
    """The target keeps only its own facts after a handle-level wait."""
    mailbox = space()
    message = S["libfix-mail"](1)
    mailbox += message

    assert mailbox.peek(S["libfix-mail"](V.value), deadline=0.1) == message
    assert mailbox.atoms() == [message]
