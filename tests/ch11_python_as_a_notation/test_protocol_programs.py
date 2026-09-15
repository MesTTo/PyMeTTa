"""Purpose: run generated protocol programs in CPython and compiled MeTTa.

Guarantees: every source operator callable has a public compiled witness;
direct syntax, guarded calls, larger operand frames and exception values use
the existing twin oracle [source:
extensions/python/tools/protocolgen.py:render_programs; commit=WORKTREE].
Owns resources: each scratch_space fixture retires its native declarations.
"""

from __future__ import annotations

import inspect
import operator
from operator import add as imported_add
from operator import call as invoke_operator

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from metta import Expression, Grounded, S, testing
from metta._atoms._python_protocols import BY_CALLABLE

from ._protocol_programs import ALIAS_PROGRAMS, CALL_PROGRAMS, PROGRAMS

# Inputs vary by operand shape, independent of the operator roster. Immutable
# values keep check_twin's successive engine/Python calls independent.
_UNARY_CASES = ((None,), (False,), (0,), (-2,), (1.5,), ("",), ("a",), ((1, 2),))
_BINARY_CASES = ((7, 2), (-7, 2), (0, 0), (1, -1), (False, True),
                 ("", "x"), ("x", 2), ((1,), (2,)), (None, 1), (1.5, 0.5))


def _cases(count):
    if count == 0:
        return ((),)
    if count == 1:
        return _UNARY_CASES
    if count == 2:
        return _BINARY_CASES
    return (tuple(range(count)), tuple(None for _ in range(count)))


def _fuzz_positional_values(defined, count):
    @settings(max_examples=16, derandomize=True, database=None, deadline=None)
    @given(st.tuples(*(st.integers(-8, 8) for _ in range(count))))
    def check(case):
        assert testing.check_twin(defined, [case])

    check()


@pytest.mark.parametrize(("member", "kind", "node", "syntax", "exact"), PROGRAMS,
                         ids=[row[0][1] for row in PROGRAMS])
def test_generated_source_syntax_and_exact_calls_have_twins(scratch_space, member, kind, node, syntax, exact):  # noqa: PLR0917 -- pytest supplies the independent source-row columns
    """Each recognized semantic shape executes independently on both sides."""
    for source in (syntax, exact):
        defined = scratch_space.define(source, name=source.__name__.replace("_", "-"))
        assert inspect.unwrap(defined.py).__code__ is source.__code__
        assert testing.check_twin(defined, _cases(source.__code__.co_argcount)), (member, kind, node)
        _fuzz_positional_values(defined, source.__code__.co_argcount)


@pytest.mark.parametrize(("identity", "count", "source"), CALL_PROGRAMS + ALIAS_PROGRAMS,
                         ids=[source.__name__ for _, _, source in CALL_PROGRAMS + ALIAS_PROGRAMS])
def test_every_available_source_callable_uses_the_operator_frame(scratch_space, identity, count, source):
    """Every actual export uses the exact callable and retains error details."""
    if identity[1] not in vars(operator):
        pytest.skip(f"{identity[0]}.{identity[1]} is absent from this Python version")
    defined = scratch_space.define(source, name=source.__name__.replace("_", "-"))
    assert "py-operator" in defined.runtime_ops
    assert BY_CALLABLE[identity].accepts_positional(count)
    assert testing.check_twin(defined, _cases(count))


def test_guarded_concat_and_iconcat_keep_sequence_eligibility(scratch_space):
    """Having numeric add hooks does not bypass CPython's sequence guard."""
    class AddOnly:
        def __add__(self, other):
            return ("numeric", other)

        def __iadd__(self, other):
            return ("inplace", other)

    exact = {identity[1]: source for identity, _, source in CALL_PROGRAMS}
    value = AddOnly()
    assert operator.add(value, 2) == ("numeric", 2)
    assert operator.iadd(value, 2) == ("inplace", 2)
    for name in ("concat", "iconcat"):
        defined = scratch_space.define(exact[name], name=f"guarded-{name}")
        assert "py-operator" in defined.runtime_ops
        observed = exact[name](value, 2)
        assert observed[:2] == ("raise", "TypeError")
        assert testing.check_twin(defined, [(value, 2), ((1,), (2,))])


def test_public_operator_call_retains_falsey_values_and_atom_identity(scratch_space):
    """A compiled public call carries several held operands through one frame."""
    seen = []

    def receive(*values):
        seen.append(values)
        return len(values)

    @scratch_space.define
    def call_values(function, missing, false, zero, empty, atom):  # noqa: PLR0917 -- several operands discriminate the structural frame from the old finite arities
        return invoke_operator(function, missing, false, zero, empty, atom)

    held = Expression(S.literal, S.body)
    assert "py-operator" in call_values.runtime_ops
    operands = (receive, None, False, 0, "", Grounded(held))
    assert call_values(*operands) == [5]
    assert len(seen) == 1
    values = seen[0]
    assert values[0] is None and values[1] is False and type(values[2]) is int
    assert values[2] == 0 and values[3] == "" and values[4] is held


def test_bare_alias_arity_errors_keep_the_exact_python_call(scratch_space):
    """An imported alias with a refused shape cannot become a native head."""
    @scratch_space.define
    def missing_operand(value):
        try:
            result = imported_add(value)
        except TypeError as error:
            return ("raise", error.__class__.__name__, str(error))
        return ("return", result)

    assert "py-operator" not in missing_operand.runtime_ops
    assert testing.check_twin(missing_operand, [(1,), (None,)])


def test_operator_calls_preserve_literal_local_and_nested_container_species(scratch_space):
    """Literal inputs and completed call results retain Python list/tuple kinds."""
    @scratch_space.define
    def container_calls():
        values = [2]
        added = imported_add([1], values)
        joined = operator.concat(added, [3])
        pair = operator.add((1,), (2,))
        return (str(added), str(joined), str(operator.concat(pair, (3,))))

    assert "py-operator" in container_calls.runtime_ops
    assert container_calls.py() == ("[1, 2]", "[1, 2, 3]", "(1, 2, 3)")
    assert testing.check_twin(container_calls, [()])


def test_successful_operator_calls_return_none_and_mutate_the_borrowed_list(scratch_space):
    """None is one result, and borrowed arguments keep their mutation target."""
    @scratch_space.define
    def mutate(values, callback):
        written = operator.setitem(values, 0, 5)
        removed = operator.delitem(values, 1)
        called = invoke_operator(callback)
        return written, removed, called

    values = [1, 2]
    assert "py-operator" in mutate.runtime_ops
    assert mutate(Grounded(values), lambda: None) == [(None, None, None)]
    assert values == [5]


def test_operator_call_results_preserve_object_identity_and_later_use(scratch_space):
    """Imported call results remain held through another imported call."""
    @scratch_space.define
    def consume(callback, observer):
        value = invoke_operator(callback)
        return invoke_operator(observer, value)

    held = S.OperatorReturnedAtom(S.payload)
    scratch_space.add(S["="](held, S.UnwantedReduction))
    assert scratch_space.eval(held) == [S.UnwantedReduction]
    observed = []

    def observer(item):
        observed.append(item)
        return item is held

    assert consume(lambda: held, observer).one() is True
    assert len(observed) == 1 and observed[0] is held

    values = []

    def return_list():
        return values

    def append(items):
        items.append(7)
        return items is values

    assert consume(return_list, append).one() is True
    assert values == [7]
