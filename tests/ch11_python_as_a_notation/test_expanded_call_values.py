"""Purpose: bind expanded calls from native values and live keyword spaces.

Guarantees:
  - named and parametric keyword spaces supply their current native entries
    through the ordinary expanded-call binder [tested:
    test_keyword_expansion_reads_native_space_entries; commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - operand effects and mapping failures follow the Python oracle [tested:
    test_expanded_calls_match_python_operand_and_mapping_failure_order;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - computed calls read native signatures and answer cardinality [tested:
    test_expanded_native_calls_read_the_live_contract;
    test_computed_calls_share_iteration_consumers; commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
  - named references retain current ports, captures and registration ownership
    [tested: test_expanded_operations_use_each_registered_arity;
    test_expanded_partial_references_preserve_capture_and_parameter_names;
    test_expanded_operation_contracts_follow_replacement_and_retirement;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
"""

import inspect
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from metta import Expression, G, MeTTa, S, Space, V, convert
from metta._catalog import call_signatures


@pytest.mark.parametrize("name", ("&keyword-entries", S["keyword-entries"](1)))
def test_keyword_expansion_reads_native_space_entries(name):
    """A later native mapping edit changes the next expanded Python call."""
    with MeTTa() as context:
        space = context.self
        keywords = Space(name)
        try:
            row = Expression(["scale", 3])
            keywords.add(row)

            def multiply(value, *, scale=1):
                return value * scale

            @space.define
            def scaled(value):
                return multiply(value, **keywords)

            assert list(scaled(2)) == [6]
            keywords.remove(row)
            keywords.add(Expression(["scale", 5]))
            assert list(scaled(2)) == [10]
        finally:
            keywords.drop()


def test_expanded_calls_match_python_operand_and_mapping_failure_order():
    """A mapping merge fails before later source operands can have effects."""
    events = []

    def mark(name, value):
        events.append(name)
        return value

    class Positional:
        def __iter__(self):
            events.append("iterate")
            yield 2

    class Keywords:
        def __init__(self, key):
            self.key = key

        def keys(self):
            events.append("keys")
            return [self.key]

        def __getitem__(self, key):
            events.append(f"get:{key}")
            return 5

    class GeneratedKeys(Keywords):
        def keys(self):
            events.append("keys")
            yield self.key
            events.append("keys-finished")

    class DictKeys(dict):
        def keys(self):
            events.append("dict-keys")
            return super().keys()

        def __getitem__(self, key):
            events.append(f"dict-get:{key}")
            return super().__getitem__(key)

    def result(first, *rest, tail, bonus, final):
        events.append("call")
        return 1 + first + sum(rest) + tail + bonus + final

    with MeTTa() as context:
        m = context.self

        @m.define
        def apply(values: Any, mapping: Any) -> int:
            return result(*mark("args", values), tail=mark("tail", 3),
                          **mark("mapping", mapping), final=mark("final", 4))

        @m.define
        def mixed(values: Any, mapping: Any) -> int:
            return result(0, *mark("args", values), tail=mark("tail", 3),
                          **mark("mapping", mapping), final=mark("final", 4))

        @m.define
        def keywords_after(values: Any, mapping: Any) -> int:
            return result(*mark("args", values), **mark("mapping", mapping),
                          tail=mark("tail", 3), final=mark("final", 4))

        for selected in (apply, mixed, keywords_after):
            for mapping in (Keywords("bonus"), GeneratedKeys("bonus"), DictKeys(bonus=5), Keywords("tail"), Keywords(9)):
                results = []
                for python in (True, False):
                    events.clear()
                    try:
                        answer = selected.py(Positional(), mapping) if python else selected(Positional(), mapping).one()
                    except Exception as error:
                        answer = str(error)
                    results.append((answer, events.copy()))
                assert results[0][1] == results[1][1], results
                key = getattr(mapping, "key", "bonus")
                if key == "bonus":
                    assert results[0][0] == results[1][0] == 15
                else:
                    message = "multiple values for keyword argument" if key == "tail" else "keywords must be strings"
                    assert message in results[0][0]
                    assert message in results[1][0]


def test_expanded_native_calls_read_the_live_contract():
    """Parameter kinds, defaults and equation edits govern the next call."""
    with MeTTa() as context:
        m = context.self
        parameters = Expression([V.value, V.extra, V.scale, V.options])
        application = Expression([S["native-expanded"], *parameters.children])
        equation = S["="](application, S.noeval(S.bound(*parameters.children)))
        m.add(equation)
        image = S["|->"](parameters, S.evalc(application, m))
        signature = inspect.Signature([
            inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("extra", inspect.Parameter.VAR_POSITIONAL),
            inspect.Parameter("scale", inspect.Parameter.KEYWORD_ONLY, default=2),
            inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD),
        ])
        contract = S["@python-callable"](image, call_signatures.project(signature, G), S.one)
        m.add(contract)
        callback = convert.build(image, Callable[..., Any])

        @m.define
        def apply(function: Callable[..., Any], values: tuple[int, ...], options: dict[str, int]):
            return function(*values, **options)

        answer = apply(callback, (1, 2, 3), {"scale": 4, "bonus": 5}).one()
        assert answer.head == S.bound
        assert tuple(part.value for part in answer.args) == (1, (2, 3), 4, {"bonus": 5})
        assert tuple(part.value for part in apply(callback, (1,), {}).one().args) == (1, (), 2, {})
        m.remove(contract)
        changed = signature.replace(parameters=[
            parameter.replace(default=8) if parameter.name == "scale" else parameter
            for parameter in signature.parameters.values()
        ])
        m.add(S["@python-callable"](image, call_signatures.project(changed, G), S.one))
        assert tuple(part.value for part in apply(callback, (1,), {}).one().args) == (1, (), 8, {})
        m.remove(equation)
        m.add(S["="](application, 73))
        assert apply(callback, (1,), {}).one() == 73


@pytest.mark.parametrize("kind", ("stream", "container", "host"))
def test_computed_calls_share_iteration_consumers(kind):
    """A native stream and a returned iterable feed the same Python consumers."""
    with MeTTa() as context:
        m = context.self
        if kind == "stream":
            m.run("(= (native-items $start) (superpose ((+ 3 $start) (+ 4 $start))))")
        else:
            m.run("(= (native-items $start) (chain (+ 3 $start) $x (chain (+ 4 $start) $y (noeval ($x $y)))))")
        image = S["|->"](Expression([V.start]), S.evalc(S["native-items"](V.start), m))
        signature = inspect.Signature([
            inspect.Parameter("start", inspect.Parameter.KEYWORD_ONLY, default=0),
        ], return_annotation=Iterator[int] if kind == "stream" else list[int])
        m.add(S["@python-callable"](image, call_signatures.project(signature, G), S.stream if kind == "stream" else S.one))
        callback = (lambda *, start=0: [3 + start, 4 + start]) if kind == "host" else convert.build(image, Callable[..., Any])

        @m.define
        def collected(function: Callable[..., Any]) -> list[int]:
            return list(function(start=2))

        @m.define
        def summed(function: Callable[..., Any]) -> int:
            total = 0
            for item in function(start=2):
                total += item
            return total

        @m.define
        def comprehension(function: Callable[..., Any]) -> list[int]:
            return [item + 1 for item in function(start=2)]

        assert convert.build(collected(callback).one(), list[int]) == [5, 6]
        assert summed(callback).one() == 11
        assert convert.build(comprehension(callback).one(), list[int]) == [6, 7]


def test_computed_lambda_calls_bind_keywords_after_creating_the_value():
    """A computed native lambda binds source keywords to its native parameters."""
    with MeTTa() as context:
        @context.self.define
        def calculated() -> int:
            return (lambda left, right: left * 10 + right)(right=2, left=1)  # noqa: PLC3002 -- computed callee is the behavior under test

        assert calculated().one() == 12


@pytest.mark.parametrize("kind", ("definition", "operation", "host"))
def test_expanded_known_calls_keep_their_parameter_names(kind):
    """Known and parameter-carried callees bind the same expanded arguments."""
    with MeTTa() as context:
        m = context.self

        def target(left: int, right: int) -> int:
            return left * 10 + right

        if kind == "definition":
            target = m.define(target)
        elif kind == "operation":
            target = m.op(target, name="expanded-known-target", effect="oracleIO")

        @m.define
        def expanded(values: tuple[int, ...], options: dict[str, int]) -> int:
            return target(*values, **options)

        @m.define
        def stored(function: Callable[..., int], values: tuple[int, ...], options: dict[str, int]) -> int:
            return function(*values, **options)

        try:
            assert expanded((1,), {"right": 2}).one() == 12
            assert stored(target, (1,), {"right": 2}).one() == 12
        finally:
            if kind == "operation":
                m.unregister_op("expanded-known-target")


@pytest.mark.parametrize("stream", (False, True))
@pytest.mark.parametrize("converted", (False, True))
def test_expanded_operations_use_each_registered_arity(stream, converted):
    """Defaults and variadic ports preserve their operation's answer count."""
    with MeTTa() as context:
        m = context.self

        def target(first=1, second=2):
            return first * 10 + second

        def answers(*values):
            yield from values

        m.op(answers if stream else target, name="expanded-ports",
             arities=[0, 1, 2, 3] if stream else None, effect="oracleIO")
        operation = convert.build(S["expanded-ports"], Callable[..., Any], space=m) if converted else S["expanded-ports"]

        @m.define
        def expanded(function: Callable[..., Any], values: tuple[int, ...], options: dict[str, int]):
            return function(*values, **options)

        @m.define
        def collected(function: Callable[..., Any], values: tuple[int, ...]) -> list[int]:
            return list(function(*values))

        try:
            if stream:
                for values in ((), (3,), (3, 4), (3, 4, 5)):
                    assert list(expanded(operation, values, {})) == list(values)
                    assert convert.build(collected(operation, values).one(), list[int]) == list(values)
            else:
                for values, options, expected in (((), {}, 12), ((3,), {}, 32), ((3, 4), {}, 34), ((3,), {"second": 4}, 34)):
                    assert expanded(operation, values, options).one() == expected
        finally:
            m.unregister_op("expanded-ports")


def test_expanded_operation_contracts_follow_replacement_and_retirement():
    """A retained native reference reads names from the current registration."""
    with MeTTa() as context:
        m = context.self

        def original(left: int, right: int) -> int:
            return left * 10 + right

        def replacement(first: int, last: int) -> int:
            return first * 100 + last

        wrapper = m.op(original, name="replaced-expanded", effect="oracleIO")
        operation = S["replaced-expanded"]

        @m.define
        def expanded(function: Callable[..., int], values: tuple[int, ...], options: dict[str, int]) -> int:
            return function(*values, **options)

        try:
            assert expanded(operation, (3,), {"right": 4}).one() == 34
            m.op(replacement, name="replaced-expanded", effect="oracleIO")
            assert expanded(operation, (3,), {"last": 4}).one() == 304
            assert expanded(wrapper, (3,), {"right": 4}).one() == 34
            with pytest.raises(Exception, match=r"missing a required argument: 'last'|unexpected keyword argument 'right'"):
                expanded(operation, (3,), {"right": 4}).one()
        finally:
            m.unregister_op("replaced-expanded")
        with pytest.raises(Exception, match="no native callable image"):
            expanded(operation, (3,), {"last": 4}).one()


def test_expanded_definition_contracts_keep_distinct_lexical_homes():
    """Equal native names in two programs retain independent parameter rows."""
    with MeTTa() as first_context, MeTTa() as second_context, MeTTa() as caller:
        def first(left: int, right: int) -> int:
            return left * 10 + right

        def second(front: int, back: int) -> int:
            return front * 100 + back

        first_context.self.define(first, name="scoped-expanded")
        second_context.self.define(second, name="scoped-expanded")
        left = convert.build(S["scoped-expanded"], Callable[..., int], space=first_context.self)
        right = convert.build(S["scoped-expanded"], Callable[..., int], space=second_context.self)

        @caller.self.define
        def expanded(function: Callable[..., int], values: tuple[int, ...], options: dict[str, int]) -> int:
            return function(*values, **options)

        assert expanded(left, (3,), {"right": 4}).one() == 34
        assert expanded(right, (3,), {"back": 4}).one() == 304
        first_context.self.remove(S["="](S["scoped-expanded"](V.left, V.right), V.body))
        first_context.self.add(S["="](S["scoped-expanded"](V.left, V.right), 73))
        assert expanded(left, (3,), {"right": 4}).one() == 73
        assert expanded(right, (3,), {"back": 4}).one() == 304


@pytest.mark.parametrize("defaults", (False, True))
def test_expanded_partial_references_preserve_capture_and_parameter_names(defaults):
    """Both fixed and segment forwarding values use the remaining native port."""
    with MeTTa() as context:
        m = context.self

        def fixed(first: int, second: int, third: int) -> int:
            return first * 100 + second * 10 + third

        def optional(first: int, second: int = 2, third: int = 3) -> int:
            return first * 100 + second * 10 + third

        m.op(optional if defaults else fixed, name="captured-expanded", effect="oracleIO")
        callback = convert.build(S.partial(S["captured-expanded"], Expression([1])), Callable[..., int], space=m)

        @m.define
        def expanded(function: Callable[..., int], values: tuple[int, ...], options: dict[str, int]) -> int:
            return function(*values, **options)

        try:
            assert expanded(callback, (4,), {"third": 5}).one() == 145
            assert callback(4, third=5) == 145
        finally:
            m.unregister_op("captured-expanded")


def test_forwarding_contracts_preserve_explicit_cardinality_and_bound_captures():
    """Eta contraction cannot override a contract or free a bound operand."""
    with MeTTa() as context:
        m = context.self

        def target(first: int, second: int, third: int) -> int:
            return first * 100 + second * 10 + third

        m.op(target, name="forwarded-expanded", effect="oracleIO")
        repeated = S["|->"](Expression([V.first, S[":seg"](V.rest)]), S.evalc(
            S.chain(S["cons-atom"](S.noeval(S["forwarded-expanded"]),
                    S["cons-atom"](S.noeval(V.first), S["cons-atom"](S.noeval(V.first), V.rest))),
                    V.result, S.eval(V.result)), m))
        forwarded = S["|->"](Expression([S[":seg"](V.values)]), S.evalc(
            S.chain(S["cons-atom"](S.noeval(S["forwarded-expanded"]), V.values), V.result, S.eval(V.result)), m))
        signature = inspect.Signature([inspect.Parameter("values", inspect.Parameter.VAR_POSITIONAL)])
        m.add(S["@python-callable"](forwarded, call_signatures.project(signature, G), S.stream))
        try:
            assert convert.build(repeated, Callable[..., int])(3, 4) == 334
            stream = convert.build(forwarded, Callable[..., Iterator[int]])(3, 4, 5)
            with stream:
                assert list(stream) == [345]
        finally:
            m.unregister_op("forwarded-expanded")


def test_native_references_observe_later_arity_changes():
    """The value names a native callable, not the first arrow seen at capture."""
    with MeTTa() as context:
        m = context.self

        def original(value: int) -> int:
            return value + 1

        def replacement(first: int, second: int) -> int:
            return first * 10 + second

        m.op(original, name="changing-arity", effect="oracleIO")
        callback = convert.build(S["changing-arity"], Callable[..., int], space=m)
        try:
            assert callback(3) == 4
            m.op(replacement, name="changing-arity", effect="oracleIO")
            assert callback(3, second=4) == 34
        finally:
            m.unregister_op("changing-arity")


def test_static_keywords_carry_segment_callable_operands():
    """Keyword operand sequencing preserves a native forwarding value."""
    with MeTTa() as context:
        m = context.self
        m.run("(= (keyword-callback $value) (+ $value 4))")
        callback = convert.build(S["keyword-callback"], Callable[[int], int], space=m)

        @m.define
        def invoked(function: Callable[[int], int], value: int) -> int:
            return function(value)

        @m.define
        def ordered(function: Callable[[int], int]) -> int:
            return invoked(value=3, function=function)

        assert ordered(callback).one() == 7


@pytest.mark.parametrize("shared_names", (False, True))
def test_expanded_stacked_clauses_keep_positional_dispatch(shared_names):
    """Clause-local variable names do not make positional calls ambiguous."""
    with MeTTa() as context:
        m = context.self

        def first_case(value=1):  # noqa: ARG001 -- a literal default is a native head pattern
            return 11

        def same_name(value=2):  # noqa: ARG001 -- a literal default is a native head pattern
            return 22

        def different_name(other=2):  # noqa: ARG001 -- a literal default is a native head pattern
            return 22

        m.define(first_case, name="stacked-expanded")
        m.define(same_name if shared_names else different_name, name="stacked-expanded")

        @m.define
        def expanded(function: Callable[..., int], values: tuple[int, ...], options: dict[str, int]) -> int:
            return function(*values, **options)

        for value, expected in ((1, 11), (2, 22)):
            assert expanded(S["stacked-expanded"], (value,), {}).one() == expected
        if shared_names:
            assert expanded(S["stacked-expanded"], (), {"value": 2}).one() == 22
        else:
            with pytest.raises(Exception, match="missing a required argument"):
                expanded(S["stacked-expanded"], (), {"value": 2}).one()
