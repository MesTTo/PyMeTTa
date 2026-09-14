"""Purpose: exercise callable values and argument ownership across class grains.

Guarantees:
  - call syntax and Python projections preserve native method selection
    [tested: test_method_call_expansions_preserve_native_dispatch; commit=WORKTREE]
"""

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

import pytest

from metta import Atom, MeTTa, S, Space, V, convert
from metta._declare.classes import declaration
from metta.vocabularies import EffectClass


def test_captured_native_callables_preserve_live_python_and_native_bindings():
    """An explicit host capture still reaches the native callable's live body."""
    with MeTTa() as context:
        m = context.self
        original = S["+"](3, 4)
        replacement = S["*"](2, 5)

        @m.define
        def captured_source() -> Atom:
            return original

        @m.define
        def other_source() -> Atom:
            return replacement

        captured = convert.build(S["captured-source"], Callable[[], Atom], space=m)

        @m.define
        @dataclass(frozen=True)
        class CapturedMethod:
            def read(self) -> Any:
                return captured()

        receiver = CapturedMethod()
        assert receiver.read() == original
        plan = declaration(CapturedMethod)
        m.remove(S["="](S["captured-source"](), V.body))
        m.add(S["="](S["captured-source"](), S.noeval(replacement)))
        assert receiver.read() == replacement
        captured = convert.build(S["other-source"], Callable[[], Atom], space=m)
        m.remove(S["="](S["other-source"](), V.body))
        m.add(S["="](S["other-source"](), S.noeval(original)))
        assert receiver.read() == original
        assert plan.space.effect_plan(S["CapturedMethod-read"](receiver)).effect is EffectClass.oracleIO


@pytest.mark.parametrize("as_image", [False, True])
def test_kept_unbound_methods_retain_their_class_program(as_image):
    """An unbound method is a program value even before a receiver is supplied."""
    with MeTTa() as context:
        m = context.self
        with m.scope():
            with m.scope() as inner:
                @dataclass(frozen=True)
                class KeptUnboundMethod:
                    value: int

                    def plus(self, amount: int) -> int:
                        return self.value + amount

                KeptUnboundMethod.__qualname__ += str(as_image)
                m.define(KeptUnboundMethod)
                receiver = KeptUnboundMethod(3)
                method = KeptUnboundMethod.plus
                held = inner.keep(convert.project(method).atom if as_image else method)
                owner = declaration(KeptUnboundMethod)
            assert not owner.space.dropped
            native = convert.build(held) if as_image else held
            assert native(receiver, amount=4) == 7
        assert declaration(KeptUnboundMethod) is None


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
@pytest.mark.parametrize("started", [False, True])
def test_kept_generator_cursors_close_with_their_execution_scope(grain, started):
    """Keeping a cursor value does not transfer its running engine to a parent."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object
        with m.scope():
            with m.scope() as inner:
                @dataclass(frozen=grain == "value")
                class KeptCursorClass(base):
                    value: int

                    def values(self) -> Iterator[int]:
                        yield self.value
                        yield self.value + 1

                KeptCursorClass.__qualname__ += f"_{grain}_{started}"
                m.define(KeptCursorClass)
                cursor = KeptCursorClass(3).values()
                if started:
                    assert next(cursor) == 3
                inner.keep(cursor)
            assert list(cursor) == []
            cursor.close()
            assert declaration(KeptCursorClass) is None


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_method_arguments_borrow_containers_independently_of_receiver_grain(grain):
    """A Python argument and a Python default keep their ordinary aliases."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object
        default = []

        @m.define
        @dataclass(frozen=grain == "value")
        class BorrowedArguments(base):
            value: int

            def append(self, items: list[int] = default) -> list[int]:
                items.append(self.value)
                return items

        value = BorrowedArguments(3)
        items = []
        assert value.append(items) is items
        assert items == [3]
        assert value.append() is default
        assert value.append() is default
        assert default == [3, 3]
        bound = convert.build(convert.project(value.append).atom, Callable[..., list[int]])
        assert bound(items) is items
        assert items == [3, 3]


def test_returned_generator_callable_preserves_declared_cardinality():
    """A generator streams, while a container return remains one value."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class CallableCardinality:
            value: int

            def elements(self) -> Iterator[int]:
                yield self.value
                yield self.value + 1

            def container(self) -> list[int]:
                return [self.value, self.value + 1]

            def iterator(self) -> Callable[[], Iterator[int]]:
                return self.elements

            def collection(self) -> Callable[[], list[int]]:
                return self.container

        receiver = CallableCardinality(3)
        cursor = receiver.iterator()()
        assert next(cursor) == 3
        assert list(cursor) == [4]
        assert receiver.collection()() == [3, 4]
        with m.scope():
            unopened = receiver.iterator()()
        assert list(unopened) == []


def test_method_call_expansions_preserve_native_dispatch():
    """Expanded arguments and a local bound value use the selected equation."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ExpandedMethod:
            value: int

            def score(self, first: int, /, *rest: int, scale: int = 2, **options: int) -> int:
                return self.value + (first + sum(rest)) * scale + options["bonus"]

            def expanded(self, items: tuple[int, ...], options: dict[str, int]) -> int:
                return self.score(*items, **options)

            def stored(self) -> int:
                selected = self.score
                return selected(2, 3, scale=4, bonus=5)

        receiver = ExpandedMethod(1)
        assert receiver.expanded((2, 3), {"scale": 4, "bonus": 5}) == 26
        assert receiver.stored() == 26
        plan = declaration(ExpandedMethod)
        pattern = S["ExpandedMethod-score"](V.self, V.first, V.rest, V.scale, V.options)
        plan.space.remove(S["="](pattern, V.body))
        plan.space.add(S["="](pattern, 73))
        assert receiver.expanded((2, 3), {"scale": 4, "bonus": 5}) == 73
        assert receiver.stored() == 73


def test_native_partial_callable_keeps_its_lexical_home():
    """A native partial remains applicable after storage in another space."""
    with MeTTa() as context:
        m = context.self
        m.run("(: native-add (-> Number Number Number)) (= (native-add $x $y) (+ $x $y))")
        value = m.eval(S["native-add"](3))[0]
        function = convert.build(value, Callable[[int], int], space=m)
        assert function(4) == 7
        with m._new_space() as other:
            other.add(S.callback(convert.project(function).atom))
            stored = other.match(S.callback(V.value))[0].value
            recovered = convert.build(stored, Callable[[int], int])
            assert recovered(5) == 8


def test_generic_compiled_call_binds_native_callable_values():
    """A callable parameter keeps its body in the graph, including keywords."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class PassedMethod:
            value: int

            def add(self, x: int, *, y: int = 2) -> int:
                return self.value + x + y

        @m.define
        def apply(function: Callable[..., int], values: tuple[int, ...], options: dict[str, int]) -> int:
            return function(*values, **options)

        receiver = PassedMethod(3)
        assert apply(receiver.add, (4,), {"y": 5}).one() == 12
        plan = declaration(PassedMethod)
        pattern = S["PassedMethod-add"](V.self, V.x, V.y)
        plan.space.remove(S["="](pattern, V.body))
        plan.space.add(S["="](pattern, 61))
        assert apply(receiver.add, (4,), {"y": 5}).one() == 61


def test_computed_generator_calls_share_iteration_consumers():
    """Binding the generator before calling it preserves answer cardinality."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class StoredStream:
            value: int

            def elements(self, *, start: int = 0) -> Iterator[int]:
                yield self.value + start
                yield self.value + start + 1

            def collected(self) -> list[int]:
                function = self.elements
                return list(function(start=2))

            def summed(self) -> int:
                function = self.elements
                total = 0
                for item in function(start=2):
                    total += item
                return total

            def comprehension(self) -> list[int]:
                function = self.elements
                return [item + 1 for item in function(start=2)]

        receiver = StoredStream(3)
        assert receiver.collected() == [5, 6]
        assert receiver.summed() == 11
        assert receiver.comprehension() == [6, 7]


def test_unbound_private_and_super_values_keep_the_lexical_provider():
    """Taking a method as data preserves each Python lookup's receiver."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ValueBase:
            value: int

            def score(self, *, increment: int = 1) -> int:
                return self.value + increment

        @m.define
        @dataclass(frozen=True)
        class ValueChild(ValueBase):
            def __secret(self, *, increment: int = 2) -> int:
                return self.value + increment

            def score(self, *, increment: int = 3) -> int:
                return self.value + increment + 10

            def qualified(self) -> int:
                function = ValueBase.score
                return function(self, increment=4)

            def cooperative(self) -> int:
                function = super().score
                return function(increment=4)

            def explicit(self) -> int:
                function = super(ValueChild, self).score  # noqa: UP008 -- exercise explicit super as a value
                return function(increment=4)

            def private(self) -> int:
                function = self.__secret
                return function(increment=4)

        receiver = ValueChild(2)
        assert receiver.qualified() == 6
        assert receiver.cooperative() == 6
        assert receiver.explicit() == 6
        assert receiver.private() == 6
        unbound = convert.build(convert.project(ValueBase.score).atom, Callable[..., int])
        assert unbound(receiver, increment=4) == 6


def test_method_defaults_are_read_from_one_native_signature():
    """A signature rewrite reaches direct, bound, unbound and compiled calls."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class SignatureRewrite:
            value: int

            def add(self, increment: int = 2) -> int:
                return self.value + increment

            def invoke(self) -> int:
                return self.add()

        receiver = SignatureRewrite(3)
        bound = convert.build(convert.project(receiver.add).atom, Callable[..., int])
        unbound = convert.build(convert.project(SignatureRewrite.add).atom, Callable[..., int])
        assert receiver.add() == bound() == unbound(receiver) == receiver.invoke() == 5
        plan = declaration(SignatureRewrite)
        plan.space.run('''
          !(match &SignatureRewrite
             (@python-callable $image
               (signature ($self (parameter "increment" $kind $type (default 2))) $return)
               $cardinality)
             (progn
               (remove-atom &SignatureRewrite
                 (@python-callable $image
                   (signature ($self (parameter "increment" $kind $type (default 2))) $return)
                   $cardinality))
               (add-atom &SignatureRewrite
                 (@python-callable $image
                   (signature ($self (parameter "increment" $kind $type (default 8))) $return)
                   $cardinality))))
        ''')
        assert receiver.add() == bound() == unbound(receiver) == receiver.invoke() == 11


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_expanded_constructors_run_native_defaults_and_initialization(grain):
    """Call assembly reaches make-Class and its transaction for every grain."""
    factories = []

    def default_values():
        factories.append("factory")
        return [7]

    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value")
        class PackedConstructor(base):
            value: int
            values: list[int] = field(default_factory=default_values)

        @m.define
        def construct(values: tuple[int, ...], options: dict[str, Any]) -> PackedConstructor:
            return PackedConstructor(*values, **options)

        one = convert.build(construct((3,), {}).one(), PackedConstructor)
        two = convert.build(construct((), {"value": 4}).one(), PackedConstructor)
        assert (one.value, two.value) == (3, 4)
        assert one.values == two.values == [7]
        assert factories == ["factory", "factory"]
        plan = declaration(PackedConstructor)
        initialize = S["_initialize-PackedConstructor"]
        equation = next(row for row in plan.space.atoms()
                        if row.head == S["="] and row.args[0].head == initialize)
        head, body = equation.args
        value = head.args[-2]
        replacement = S.chain(S["+"](value, 100), V.adjusted,
                              body.subs({value: V.adjusted}))
        plan.space.remove(S["="](head, V.body))
        plan.space.add(S["="](head, replacement))
        three = convert.build(construct((5,), {"values": [9]}).one(), PackedConstructor)
        assert three.value == 105
        assert three.values == [9]
        assert PackedConstructor(6, values=[9]).value == 106
        assert factories == ["factory", "factory"]


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_constructor_defaults_follow_the_native_callable_contract(grain):
    """Python, written and compiled construction read the same default row."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value")
        class ConstructorContract(base):
            value: int = 2

        @m.define
        def construct() -> ConstructorContract:
            return ConstructorContract()

        assert ConstructorContract().value == 2
        assert convert.build(construct().one(), ConstructorContract).value == 2
        plan = declaration(ConstructorContract)
        plan.space.run('''
          !(match &ConstructorContract
             (@python-callable $image
               (signature ((parameter "value" $kind $type (default $previous))) $return)
               $cardinality)
             (progn
               (remove-atom &ConstructorContract
                 (@python-callable $image
                   (signature ((parameter "value" $kind $type (default $previous))) $return)
                   $cardinality))
               (add-atom &ConstructorContract
                 (@python-callable $image
                   (signature ((parameter "value" $kind $type (default (+ 3 5)))) $return)
                   $cardinality))))
        ''')
        assert ConstructorContract().value == 8
        assert convert.build(construct().one(), ConstructorContract).value == 8
        assert convert.build(m.eval(S["make-ConstructorContract"]())[0], ConstructorContract).value == 8


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_constructor_arguments_are_borrowed_until_field_assignment(grain):
    """Initialization borrows arguments; storing a field applies its grain."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value", init=False)
        class ConstructorStorage(base):
            values: list[int]

            def __init__(self, values: list[int]):
                values.append(2)
                object.__setattr__(self, "values", values)

        supplied = [1]
        receiver = ConstructorStorage(supplied)
        assert supplied == [1, 2]
        assert receiver.values == [1, 2]
        supplied.append(3)
        if grain == "value":
            assert receiver.values == [1, 2]
            assert convert.project(receiver).atom == S.ConstructorStorage((1, 2))
        else:
            assert receiver.values is supplied


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_keyword_named_atoms_remain_positional_method_and_constructor_values(grain):
    """Call syntax cannot consume a positional atom because of its head name."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value")
        class KeywordData(base):
            payload: Any

            def identity(self, value: Atom) -> Any:
                return value

            def nested(self, value: Atom) -> Any:
                return self.identity(value)

            def named(self, *, value: Atom) -> Any:
                return value

        @m.define
        def invoke(function: Callable[..., Any], value: Atom) -> Any:
            return function(value)

        @m.define
        def expanded(function: Callable[..., Any], values: tuple[Atom, ...]) -> Any:
            return function(*values)

        for value in (S.Kwargs(S.entry(3)), S.Kwargs(), S.Kwargs(S.malformed), S.Data(S.entry(3))):
            receiver = KeywordData(value)
            assert receiver.payload == value
            assert receiver.identity(value) == value
            assert receiver.nested(value) == value
            assert receiver.named(value=value) == value
            assert KeywordData.identity(receiver, value) == value
            assert invoke(receiver.identity, value).one() == value
            assert expanded(receiver.identity, (value,)).one() == value
            created = convert.build(invoke(KeywordData, value).one(), KeywordData)
            assert created.payload == value


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_method_receivers_follow_the_original_parameter_kind(grain):
    """An unbound receiver can be named; a positional-only receiver leaves its name free."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value")
        class ReceiverArguments(base):
            value: int

            def named(self, amount: int = 1, **options: int) -> int:
                return self.value + amount + options.get("extra", 0)

            def positional(self, /, amount: int = 1, **options: int) -> int:
                return self.value + amount + options.get("self", 0)

        @m.define
        def named_receiver(value: ReceiverArguments) -> int:
            return ReceiverArguments.named(self=value, amount=2)

        @m.define
        def positional_receiver(value: ReceiverArguments) -> int:
            return value.positional(self=4, amount=2)

        value = ReceiverArguments(3)
        assert ReceiverArguments.named(self=value, amount=2) == 5
        assert named_receiver(value).one() == 5
        unbound = convert.build(convert.project(ReceiverArguments.named).atom, Callable[..., int])
        assert unbound(self=value, amount=2) == 5
        for call in (value.named, value.named.py, convert.build(convert.project(value.named).atom, Callable[..., int])):
            with pytest.raises(TypeError, match=r"multiple values.*self"):
                call(self=4)
        assert value.positional(self=4, amount=2) == value.positional.py(self=4, amount=2) == 9
        assert positional_receiver(value).one() == 9
