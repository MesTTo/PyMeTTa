"""Purpose: verify method equations through Python and native graph rewrites.

Guarantees:
  - the method suite compares receivers, Python signatures, C3 selection and
    ownership through both notations [tested: extensions/python/tests/ch09_types/test_class_methods.py;
    commit=WORKTREE]
"""

import inspect
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Annotated

import pytest

from metta import MeTTa, S, Space, V, convert
from metta._declare.classes import declaration
from metta._errors.errors import CompileError, MettaResultError
from metta.vocabularies import EffectClass


def test_method_receiver_refusal_names_the_binding_remedy():
    """An ordinary method needs a receiver before the declaration can publish."""
    with MeTTa() as context:
        class MissingMethodReceiver:
            def invalid():
                return 1

        with pytest.raises(CompileError, match=r"explicit receiver.*staticmethod") as caught:
            context.self.define(MissingMethodReceiver)
        assert caught.value.construct == "method receiver"
        assert caught.value.line is not None
        assert declaration(MissingMethodReceiver) is None


def test_class_method_calls_observe_the_live_equation_graph():
    """A native rewrite changes the existing Python receiver's next call."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class MethodPoint:
            x: int
            y: int

            def norm(self) -> int:
                return self.x * self.x + self.y * self.y

        point = MethodPoint(3, 4)
        plan = declaration(MethodPoint)
        assert point.norm() == point.norm.py() == 25
        assert m.eval(S.norm(point)) == [25]
        assert plan.space.effect_plan(S.norm(point)).effect is EffectClass.pureStructural
        assert "MethodPoint-norm" in point.norm.source()
        plan.space.remove(S["="](S["MethodPoint-norm"](V.self), V.body))
        plan.space.add(S["="](S["MethodPoint-norm"](V.self), 81))
        assert point.norm() == 81
        assert m.eval(S.norm(point)) == [81]
        assert point.norm.py() == 25
        assert "81" in point.norm.source()


def test_class_methods_keep_full_python_signatures_and_native_bodies():
    """The common argument layout carries defaults, varargs and keyword data."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class MethodSignature:
            base: int

            def score(this, self: int, /, amount: int = 2, *extra: int, scale: int = 3, **options: int) -> int:  # noqa: N805 -- receiver and positional-only name are the witness
                return this.base + self + amount + sum(extra) * scale + options["bonus"]

            def invoke(self) -> int:
                return self.score(1, 4, 5, 6, scale=2, bonus=7)

        value = MethodSignature(10)
        assert value.score(1, 4, 5, 6, scale=2, bonus=7) == 44
        assert value.score(1, bonus=7) == 20
        assert value.invoke() == 44
        assert inspect.signature(value.score) == inspect.signature(value.score.py)
        assert "_host-" not in value.score.source()
        with pytest.raises(TypeError):
            value.score(self=1, bonus=7)
        with pytest.raises(TypeError):
            value.score(1, 2, amount=3, bonus=7)


def test_class_open_recursion_and_cooperative_super_follow_c3():
    """A diamond retains the original receiver through each qualified body."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class MethodRoot:
            x: int

            def rank(self) -> int:
                return self.x

            def describe(self) -> int:
                return self.rank()

        @m.define
        @dataclass(frozen=True)
        class MethodLeft(MethodRoot):
            def rank(self) -> int:
                return 10 + super().rank()

        @m.define
        @dataclass(frozen=True)
        class MethodRight(MethodRoot):
            def rank(self) -> int:
                return 100 + super().rank()

        @m.define
        @dataclass(frozen=True)
        class MethodDiamond(MethodLeft, MethodRight):
            pass

        for cls, expected in ((MethodRoot, 1), (MethodLeft, 11), (MethodRight, 101), (MethodDiamond, 111)):
            value = cls(1)
            assert value.rank() == value.describe() == expected
            assert m.eval(S.rank(value)) == m.eval(S.describe(value)) == [expected]
            assert m.eval(S["MethodRoot-rank"](value)) == [1]
        root = declaration(MethodRoot)
        assert len(root.space.match(S["="](S["MethodRoot-describe"](V.self), V.body))) == 1


def test_class_bound_methods_keep_the_receiver_and_program_alive():
    """Keeping a callable retains its receiver and the defining graph."""
    with MeTTa() as context:
        m = context.self
        with m.scope():
            with m.scope() as inner:
                @m.define
                @dataclass
                class MethodKept:
                    value: int

                    def plus(self, amount: int = 2) -> int:
                        return self.value + amount

                value = MethodKept(5)
                bound = inner.keep(value.plus)
                image = inner.keep(convert.project(bound).atom)
                plan = declaration(MethodKept)
            assert bound() == 7
            assert bound(4) == 9
            with m._new_space() as other:
                other.run("(= (apply-method $f $x) ($f $x))")
                assert other.eval(S["apply-method"](image, 6)) == [11]
            assert not plan.space.dropped
        assert declaration(MethodKept) is None
        with pytest.raises(ReferenceError):
            bound(3)


def test_class_generator_methods_return_owned_cursors():
    """Yield is a native answer stream with one receiver across suspension."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class MethodStream:
            value: int

            def values(self, stop: int) -> Iterator[int]:
                while self.value < stop:
                    yield self.value
                    self.value += 1

        value = MethodStream(2)
        cursor = value.values(5)
        assert next(cursor) == 2
        assert next(cursor) == 3
        assert list(cursor) == [4]
        assert value.value == 5
        native = MethodStream(2)
        assert m.eval(S.values(native, 5)) == [2, 3, 4]
        assert native.value == 5


def test_refused_class_method_keeps_an_explicit_host_equation(capsys):
    """A refused statement remains visible and reports its reason once."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class MethodRefused:
            value: int

            def increment(self) -> int:
                try:
                    return self.value
                except* ValueError:
                    self.value = 0

        value = MethodRefused(3)
        diagnostic = capsys.readouterr().err
        assert "except*" in diagnostic
        assert diagnostic.count("MethodRefused.increment") == 1
        assert value.increment() == 3
        assert "_host-" in value.increment.source()
        plan = declaration(MethodRefused)
        assert plan.space.effect_plan(S.increment(value)).effect is EffectClass.oracleIO
        assert capsys.readouterr().err == ""


def test_method_overrides_bind_the_selected_signature():
    """A base's positional call binds the override's defaults and varargs."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class SignatureRoot:
            value: int

            def score(self, amount: int) -> int:
                return self.value + amount

            def call(self) -> int:
                return self.score(3)

        @m.define
        @dataclass(frozen=True)
        class SignatureChild(SignatureRoot):
            def score(self, amount: int, scale: int = 4) -> int:
                return self.value + amount * scale

        @m.define
        @dataclass(frozen=True)
        class SignatureMany(SignatureRoot):
            def score(self, *amounts: int) -> int:
                return self.value + sum(amounts)

        assert SignatureRoot(2).call() == 5
        assert SignatureChild(2).call() == 14
        assert SignatureMany(2).call() == 5
        assert SignatureRoot.score(SignatureChild(2), 3) == 5


def test_cooperative_method_provider_can_arrive_after_its_mixin(capsys):
    """The lexical super edge resolves against the concrete receiver's MRO."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class CooperativeMixin:
            def answer(self) -> int:
                return super().answer() + 10

        @m.define
        @dataclass(frozen=True)
        class CooperativeEnd:
            def answer(self) -> int:
                return 2

        @m.define
        @dataclass(frozen=True)
        class CooperativeJoined(CooperativeMixin, CooperativeEnd):
            pass

        assert CooperativeJoined().answer() == 12
        assert m.eval(S.answer(CooperativeJoined())) == [12]
        assert "_host-" not in CooperativeMixin.answer.source()
        assert capsys.readouterr().err == ""


def test_method_generators_compose_in_loops_and_delegation():
    """All loop forms consume the method's declared answer stream."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ComposedStream:
            value: int

            def values(self) -> Iterator[int]:
                yield self.value
                yield self.value + 1

            def delegated(self) -> Iterator[int]:
                yield from self.values()

            def collected(self) -> list[int]:
                return list(self.values())

            def squares(self) -> list[int]:
                return [value * value for value in self.values()]

            def total(self) -> int:
                total = 0
                for value in self.values():
                    total += value
                return total

        value = ComposedStream(3)
        assert list(value.delegated()) == value.collected() == [3, 4]
        assert value.squares() == [9, 16]
        assert value.total() == 7


def test_method_type_queries_follow_native_type_relations():
    """An edited subtype relation changes an already compiled type query."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class TypeRoot:
            value: int

            def accepts(self, value: object) -> bool:
                return isinstance(value, TypeRoot)

            def kind(self) -> type:
                return type(self)

        @m.define
        @dataclass(frozen=True)
        class TypeOther:
            value: int

        root, other = TypeRoot(1), TypeOther(2)
        plan = declaration(TypeRoot)
        plan.space.from_(declaration(TypeOther).space)
        assert root.accepts(root)
        assert not root.accepts(other)
        assert root.kind() is TypeRoot
        plan.space.add(S[":<"](S.TypeOther, S.TypeRoot))
        assert root.accepts(other)


def test_method_field_projection_preserves_captures_and_rebinding():
    """A projected value keeps its complete receiver in closures and loops."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ProjectionCapture:
            x: int
            y: int

            def nested(self) -> int:
                def add(offset: int) -> int:
                    return self.x + self.y + offset
                return add(2)

            def rebound(self) -> int:
                previous = self.x + self.y
                self = ProjectionCapture(self.x + 1, self.y + 2)
                return previous + self.x + self.y

            def closure(self) -> int:
                total = lambda: self.x + self.y  # noqa: E731 -- exercise a lambda capture of the receiver
                return total()

            def repeated(self, count: int) -> int:
                result = 0
                for _index in range(count):
                    result += self.x + self.y
                return result

        point = ProjectionCapture(3, 4)
        assert point.nested() == 9
        assert point.rebound() == 17
        assert point.closure() == 7
        assert point.repeated(3) == 21
        assert "(noeval (ProjectionCapture " in point.rebound.source()
        assert point.x == 3 and point.y == 4


def test_method_projection_preserves_differing_field_contracts():
    """An untaken read keeps its original refinement boundary and timing."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ProjectionRefined:
            x: Annotated[int, S.Gt(0)]
            y: int

            def total(self, enabled: bool) -> int:  # noqa: FBT001 -- boolean method parameters are supported
                if enabled:
                    return self.x + self.y
                return 0

        assert ProjectionRefined(3, 4).total(enabled=True) == 7

        @m.define
        @dataclass(frozen=True)
        class ProjectionWider(ProjectionRefined):
            x: int

        value = ProjectionWider(-3, 4)
        assert value.total(enabled=False) == 0
        assert "ProjectionRefined-x" in value.total.source()
        with pytest.raises(MettaResultError, match="BadReturnValue"):
            value.total(enabled=True)


def test_native_method_rewrite_survives_later_class_declarations():
    """Refreshing descendant layouts does not reclaim a writer's equation."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ProjectionEdited:
            x: int
            y: int

            def total(self) -> int:
                return self.x + self.y

        plan = declaration(ProjectionEdited)
        plan.space.remove(S["="](S["ProjectionEdited-total"](V.self), V.body))
        plan.space.add(S["="](S["ProjectionEdited-total"](V.self), 99))

        @m.define
        @dataclass(frozen=True)
        class ProjectionLater(ProjectionEdited):
            z: int

        assert ProjectionEdited(1, 2).total() == 99
        assert ProjectionLater(1, 2, 3).total() == 99
        assert "99" in ProjectionEdited.total.source()


def test_method_projection_rolls_back_a_descendant_layout():
    """A failed declaration restores the original method occurrence and body."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ProjectionRollback:
            x: int
            y: int

            def total(self) -> int:
                return self.x + self.y

        point = ProjectionRollback(2, 3)
        before = point.total.body

        def fail_declaration():
            @m.define
            @dataclass(frozen=True)
            class ProjectionRolledBack(ProjectionRollback):
                z: int

            assert ProjectionRolledBack(2, 3, 4).total() == 5
            message = "rollback descendant"
            raise ValueError(message)

        with pytest.raises(ValueError, match="rollback descendant"):
            m.transaction(fail_declaration)
        assert point.total() == 5
        assert point.total.body.alpha_eq(before)


def test_methods_return_callable_values_with_native_binding_metadata():
    """Returned bound methods keep defaults, keywords and live native bodies."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ReturnedMethod:
            value: int

            def plus(self, amount: int = 2, *, scale: int = 3) -> int:
                return self.value + amount * scale

            def choose(self) -> Callable[..., int]:
                return self.plus

            def callbacks(self) -> list[Callable[..., int]]:
                return [self.plus]

        receiver = ReturnedMethod(5)
        returned = receiver.choose()
        assert returned() == 11
        assert returned(4, scale=2) == 13
        assert inspect.signature(returned) == inspect.signature(receiver.plus)
        assert receiver.callbacks()[0](amount=3, scale=2) == 11
        plan = declaration(ReturnedMethod)
        plan.space.remove(S["="](S["ReturnedMethod-plus"](V.self, V.amount, V.scale), V.body))
        plan.space.add(S["="](S["ReturnedMethod-plus"](V.self, V.amount, V.scale), 77))
        assert returned(amount=6) == 77
        assert receiver.plus.py(6) == 23


def test_methods_return_lexical_closures_that_keep_their_program():
    """A returned lambda names its native lexical home across storage and keep."""
    with MeTTa() as context:
        m = context.self
        with m.scope():
            with m.scope() as inner:
                @m.define
                @dataclass(frozen=True)
                class ReturnedClosure:
                    value: int

                    def make(self) -> Callable[[int], int]:
                        def helper(amount: int) -> int:
                            return self.value + amount
                        return lambda amount: helper(amount)

                value = inner.keep(ReturnedClosure(5).make())
                image = convert.project(value).atom
            assert value(2) == 7
            assert value(amount=3) == 8
            with m._new_space() as other:
                other.run("(= (invoke-closure $f $x) ($f $x))")
                assert other.eval(S["invoke-closure"](image, 4)) == [9]
                other.add(S.callback(image))
                stored = other.match(S.callback(V.function))[0].function
                assert convert.build(stored, Callable[[int], int])(6) == 11


def test_generator_method_cursor_closes_before_the_next_effect():
    """An explicit close and a scope exit use the existing cursor cleanup."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ClosedMethodStream:
            value: int

            def values(self) -> Iterator[int]:
                yield self.value
                self.value += 1
                yield self.value

        value = ClosedMethodStream(2)
        cursor = value.values()
        assert next(cursor) == 2
        cursor.close()
        assert list(cursor) == []
        assert value.value == 2
        with m.scope():
            unopened = value.values()
            suspended = value.values()
            assert next(suspended) == 2
        assert list(unopened) == list(suspended) == []
        assert value.value == 2


@pytest.mark.parametrize("base", [object, Space])
def test_refused_method_field_write_stops_later_mutations(base):
    """The method propagates its writer's refusal before its next mutation."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class CheckedMethodWrite(base):
            value: int
            after: int = 0

            def reject(self) -> int:
                self.value = "bad"
                self.after += 1
                return 23

        receiver = CheckedMethodWrite(5)
        assert declaration(CheckedMethodWrite).methods["reject"].compiled is not None
        with pytest.raises(MettaResultError, match="BadArgType"):
            receiver.reject()
        assert (receiver.value, receiver.after) == (5, 0)
        answer = m.eval(S.reject(receiver))[0]
        assert answer.head == S.Error
        assert (receiver.value, receiver.after) == (5, 0)


def test_structural_method_projection_and_accessor_are_independent_native_views():
    """A visible constructor pattern reads fields independently of a getter."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class MethodFieldViews:
            x: int
            y: int

            def first(self) -> int:
                return self.x

            def total(self) -> int:
                return self.x + self.y

        receiver = MethodFieldViews(3, 4)
        owner = declaration(MethodFieldViews)
        assert receiver.first() == 3
        assert receiver.total() == 7
        assert "(MethodFieldViews " in receiver.total.source()
        getter = owner.accessor("x")
        owner.space.remove(S["="](getter(V.receiver), V.body))
        owner.space.add(S["="](getter(V.receiver), 30))
        assert receiver.first() == 30
        assert receiver.total() == 7
        owner.space.remove(S["="](S["MethodFieldViews-total"](V.receiver), V.body))
        owner.space.add(S["="](S["MethodFieldViews-total"](V.receiver), 40))
        assert receiver.total() == 40
