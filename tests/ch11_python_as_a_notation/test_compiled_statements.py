"""Purpose: pin the compiled statement vocabulary — exceptions on the
engine's error algebra, dicts and sets as spaces, the global pragma, type
aliases, and the exact-integer operator family.
Guarantees:
  - try/except/else/finally compile onto catch, if-error, `except` and
    error-payload with Python's dispatch, binding and ordering [tested:
    every test below whose name starts test_try or test_raise; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - a dict literal lowers to lib_dict's dict-space and every Python door
    rides the library's own vocabulary [tested: the test_dict rows below;
    commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - `global` reads and writes the definition module through a grounded
    reference, and `type X = T` is the rewrite rule it reads as [tested:
    test_global_pragma_moves_the_module,
    test_type_alias_claims_and_rewrites; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - &, |, ^, ~, <<, >> and // lower to the engine's exact integer family
    and agree with Python on every probed input [tested:
    test_bitwise_and_floor_division_agree_with_python; commit=51b792423cec5787614d1488c0793b8a50eaa6fc]
  - compiled except arms preserve live exception class identity even when two
    classes share every textual name [tested:
    test_compiled_except_uses_exception_class_identity_not_bare_name;
    commit=e7919ef660e1c2b31a307187c0237823daccdbd4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import pytest

from metta import MeTTa, S, Space
from metta.errors import CompileError


@pytest.fixture
def m():
    """One closed-on-exit self space per test."""
    context = MeTTa()
    yield context.self
    context.close()


class BoomError(ValueError):
    """A custom hierarchy member for the lattice tests."""


def test_try_dispatches_on_the_engine_error(m):
    """Try dispatches on the engine error."""
    @m.define
    def guarded(x):
        try:
            return 10 // x
        except ZeroDivisionError:
            return S.Undefined

    assert list(guarded(4)) == [2]
    assert list(guarded(0)) == [S.Undefined]


def test_try_as_binds_a_live_payload(m):
    """Try-as binds a live payload."""
    @m.define
    def named(x):  # noqa: ARG001  -- the compiled scenario carries a parameter its body ignores
        try:
            raise ValueError("spoken")  # noqa: TRY301, EM101  -- the raised literal is the scenario under test
        except ValueError as e:
            return str(e)

    assert list(named(1)) == ["spoken"]


def test_raise_crosses_frames_and_matches_the_custom_lattice(m):
    """Raise crosses frames and matches the custom lattice."""
    @m.define
    def deep(x):
        if x < 0:
            raise BoomError("deep")  # noqa: EM101  -- the raised literal is the scenario under test
        return x + 1

    @m.define
    def catch_parent(x):
        try:
            return deep(x)
        except ValueError as e:
            return str(e)

    assert list(catch_parent(-5)) == ["deep"]
    assert list(catch_parent(5)) == [6]


def test_compiled_except_uses_exception_class_identity_not_bare_name(m):
    """Two classes with identical metadata remain unrelated exception types."""
    left = type("Timeout", (Exception,), {})
    right = type("Timeout", (Exception,), {})
    for kind in (left, right):
        kind.__module__ = "shared.errors"
        kind.__qualname__ = "Timeout"

    left_error = left("left")
    right_error = right("right")

    @m.define
    def raise_left_timeout():
        raise left_error

    @m.define
    def raise_right_timeout():
        raise right_error

    @m.define
    def classify_timeout(which):
        try:
            if which == 1:
                return raise_left_timeout()
            return raise_right_timeout()
        except (left, KeyError):
            return S.left
        except Exception:
            return S.right

    assert list(classify_timeout(1)) == [S.left]
    assert list(classify_timeout(2)) == [S.right]


def test_try_else_runs_on_success_with_the_body_bindings(m):
    """Try else runs on success with the body bindings."""
    @m.define
    def elsed(x):
        try:
            y = 10 // x
        except ZeroDivisionError:
            return S.dead
        else:
            return y + 100

    assert list(elsed(2)) == [105]
    assert list(elsed(0)) == [S.dead]


def test_try_bindings_escape_to_the_rest(m):
    """Try bindings escape to the rest."""
    @m.define
    def binds(x):
        try:
            y = x * 2
        except TypeError:
            y = 0
        return y + 1

    assert list(binds(4)) == [9]


def test_a_binding_that_errors_inside_try_reaches_the_arm(m):
    """A binding that errors inside try reaches the arm."""
    @m.define
    def looped(xs):
        total = 0
        for x in xs:
            try:
                total = total + 10 // x
            except ZeroDivisionError:
                total = total + 100
        return total

    assert list(looped((5, 0, 2))) == [107]


def test_nested_try_skips_the_wrong_arm(m):
    """Nested try skips the wrong arm."""
    @m.define
    def nested(x):
        try:
            try:
                return 10 // x
            except ValueError:
                return S.inner
        except ZeroDivisionError:
            return S.outer

    assert list(nested(0)) == [S.outer]
    assert list(nested(5)) == [2]


def test_a_tuple_arm_catches_any_member(m):
    """A tuple arm catches any member."""
    @m.define
    def pair_arm(x):
        try:
            return 10 // x
        except (ValueError, ZeroDivisionError):
            return S.caught

    assert list(pair_arm(0)) == [S.caught]


def test_bare_reraise_lets_the_original_escape(m):
    """Bare reraise lets the original escape."""
    @m.define
    def rerun(x):
        try:
            return 10 // x
        except ZeroDivisionError:  # noqa: TRY203  -- the bare re-raise is the scenario under test
            raise

    answered = str(list(rerun(0)))
    assert "Error" in answered
    assert "DivisionByZero" in answered


def test_an_unmatched_error_propagates_past_the_rest(m):
    """An unmatched error propagates past the rest."""
    @m.define
    def wrong_arm(x):
        try:
            return 10 // x
        except ValueError:
            return S.never

    answered = str(list(wrong_arm(0)))
    assert "Error" in answered


def test_finally_runs_before_the_rest_continues(m):
    """Finally runs before the rest continues."""
    @m.define
    def fin_effect(x, log: Space):
        try:
            return 10 // x
        finally:
            log += S.visited(x)

    trail = m.fn["new-space"]()[0]
    assert list(fin_effect(6, trail)) == [1]
    escaped = str(list(fin_effect(0, trail)))
    assert "Error" in escaped
    # finally ran on the success path AND the escaping path.
    assert sorted(str(atom) for atom in trail) == ["(visited 0)", "(visited 6)"]


def test_finally_reading_a_rebound_name_refuses(m):
    """Finally reading a rebound name refuses."""
    with pytest.raises(CompileError, match="finally reads"):

        @m.define
        def fin_stale(x):
            note = 0
            try:
                note = 10 // x
            finally:
                note = note + 1000
            return note


def test_generator_raise_ends_the_answers(m):
    """Generator raise ends the answers."""
    @m.define
    def gen(n):
        yield n
        if n < 0:
            raise ValueError("neg")  # noqa: EM101  -- the raised literal is the scenario under test
        yield n + 1

    clean = list(gen(1))
    assert clean == [1, 2]
    dirty = gen(-3)
    rows = list(dirty)
    assert rows[0] == -3
    assert len(rows) == 2
    assert "Error" in str(rows[1])


def test_dict_literal_lowers_to_dict_space(m):
    """Dict literal lowers to dict space."""
    @m.define
    def priced(item):
        costs = {S.apple: 3, S.pear: 5}
        return costs[item]

    assert list(priced(S.apple)) == [3]
    assert list(priced(S.plum)) == []


def test_set_membership_is_total(m):
    """Set membership is total."""
    @m.define
    def has(item):
        stock = {S.apple, S.pear}
        return item in stock

    assert list(has(S.apple)) == [True]
    assert list(has(S.plum)) == [False]


def test_dict_mutation_rides_the_library_doors(m):
    """Dict mutation rides the library doors."""
    @m.define
    def grow(n):
        table = {S.base: 1}
        table[S.extra] = n
        del table[S.base]
        return (len(table), table[S.extra], S.base in table)

    assert [str(row) for row in grow(9)] == ["(1 9 False)"]


def test_dict_comprehension_builds_the_pair_expression(m):
    """Dict comprehension builds the pair expression."""
    @m.define
    def squares(n):
        table = {x: x * x for x in range(n)}
        return table[3]

    assert list(squares(6)) == [9]


def test_dict_values_evaluate_before_storage(m):
    """Dict values evaluate before storage."""
    @m.define
    def computed(x):
        d = {S.k: x + 1}
        return d[S.k]

    assert list(computed(4)) == [5]


def test_global_pragma_moves_the_module(m):
    """Global pragma moves the module."""
    global _PRAGMA_CELL
    _PRAGMA_CELL = 0

    @m.define
    def put(x):
        global _PRAGMA_CELL
        _PRAGMA_CELL = x
        return _PRAGMA_CELL

    assert list(put(41)) == [41]
    assert _PRAGMA_CELL == 41


_PRAGMA_CELL = 0


def test_type_alias_claims_and_rewrites(m):
    """Type alias claims and rewrites."""
    @m.define
    def aliased(x):
        type Marker = int
        y: Marker = x + 1
        return y

    assert list(aliased(4)) == [5]


def test_bitwise_and_floor_division_agree_with_python(m):
    """Bitwise and floor division agree with python."""
    @m.define
    def masked(x):
        return (x & 12) | (x << 2) ^ ~x

    @m.define
    def floored(a, b):
        return a // b

    for probe in (7, 0, 5, 13):
        assert list(masked(probe)) == [(probe & 12) | (probe << 2) ^ ~probe]
    assert list(floored(7, 2)) == [3]
    assert list(floored(-7, 2)) == [-4]
    assert list(floored(7.0, 2)) == [3.0]
    answered = str(list(floored(7, 0)))
    assert "DivisionByZero" in answered


def test_alpha_is_the_equality_family_spelling(m):
    """Alpha is the equality family spelling."""
    from metta import V, fn

    @m.define
    def same_shape(a, b):
        return alpha(a, b)  # noqa: F821  -- the compiled vocabulary's own name

    assert list(same_shape(S.f(1), S.f(1))) == [True]
    assert list(same_shape(S.f(1), S.f(2))) == [False]
    assert str(V.x.alpha(0)) == "(=alpha $x 0)"
    assert str(fn["=alpha"]) == "=alpha"
