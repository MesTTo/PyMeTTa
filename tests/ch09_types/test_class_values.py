"""Purpose: check class values through native calls, conversion and scope ownership.

Guarantees:
  - declared classes retain the same constructor program when passed, returned,
    stored or kept [tested: test_class_values_retain_the_native_constructor;
    test_kept_class_values_own_their_constructor_program; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from metta import Atom, Expression, Grounded, MeTTa, S, Space, V, convert
from metta._declare.classes import declaration
from metta._errors.errors import EngineError


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_class_values_retain_the_native_constructor(grain):
    """The carried class uses the same editable constructor and call contract."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value")
        class CarriedClass(base):
            value: int = 2

        @m.define
        def identity(kind: type[CarriedClass]) -> type[CarriedClass]:
            return kind

        @m.define
        def invoke(kind: Callable[..., CarriedClass], values: tuple[int, ...], options: dict[str, int]) -> CarriedClass:
            return kind(*values, **options)

        image = convert.encode(CarriedClass)
        assert isinstance(image, Expression)
        assert convert.project(CarriedClass).atom.alpha_eq(image)
        assert convert.build(image, type) is CarriedClass
        returned = identity(CarriedClass).one()
        assert convert.build(returned, type[CarriedClass]) is CarriedClass
        assert convert.build(returned, type[CarriedClass] | None) is CarriedClass
        native = convert.build(image, Callable[..., CarriedClass])
        assert native().value == 2
        assert native(value=3).value == 3
        assert convert.build(invoke(CarriedClass, (), {"value": 4}).one(), CarriedClass).value == 4
        with m._new_space() as other:
            other.add(S.saved(image))
            stored = other.match(S.saved(V.image))[0].image
            assert convert.build(stored, type[CarriedClass]) is CarriedClass
            assert convert.build(stored)(5).value == 5

        owner = declaration(CarriedClass)
        constructor = S["make-CarriedClass"]
        old = S["="](constructor(V.value), V.body)
        term = convert.project(native(6)).atom
        owner.space.remove(old)
        owner.space.add(S["="](constructor(V.value), S.noeval(term)))
        assert native(value=9).value == 6
        assert convert.build(invoke(CarriedClass, (9,), {}).one(), CarriedClass).value == 6


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
@pytest.mark.parametrize("kept_image", [False, True])
def test_kept_class_values_own_their_constructor_program(grain, kept_image):
    """Keeping either notation transfers the native class cleanup with it."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object
        with m.scope():
            with m.scope() as inner:
                @dataclass(frozen=grain == "value")
                class RetainedClass(base):
                    value: int

                RetainedClass.__qualname__ += f"_{grain}_{kept_image}"
                m.define(RetainedClass)
                owner = declaration(RetainedClass)
                value = convert.encode(RetainedClass) if kept_image else RetainedClass
                kept = inner.keep(value)
            assert not owner.space.dropped
            image = convert.encode(kept)
            assert convert.build(image, type) is RetainedClass
            assert convert.build(image)(7).value == 7
        assert declaration(RetainedClass) is None
        assert isinstance(convert.encode(RetainedClass), Grounded)


def test_class_values_preserve_explicit_host_images():
    """Undeclared classes, explicit grounding and metaclass hooks keep their meaning."""
    class OrdinaryClass:
        pass

    class HookedMeta(type):
        def __metta__(cls):
            return S.metaclass_image

    class RegisteredMeta(type):
        pass

    convert.encode.register(RegisteredMeta, lambda _cls: S.registered_image)
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class HookedClass(metaclass=HookedMeta):
            value: int

        @m.define
        @dataclass(frozen=True)
        class RegisteredClass(metaclass=RegisteredMeta):
            value: int

        assert convert.encode(OrdinaryClass).value is OrdinaryClass
        assert convert.project(OrdinaryClass).atom.value is OrdinaryClass
        assert convert.encode(HookedClass) == convert.project(HookedClass).atom == S.metaclass_image
        assert convert.encode(RegisteredClass) == convert.project(RegisteredClass).atom == S.registered_image
        assert convert.encode(Grounded(HookedClass)).value is HookedClass


def test_constructor_image_is_distinct_from_an_ordinary_factory():
    """A matching return annotation alone does not turn a function into a class."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class FactoryProduct:
            value: int

            def make_other(self, value: int) -> FactoryProduct:  # noqa: F821 -- exercise an unpublished class annotation
                return FactoryProduct(value)

        @m.define
        def factory(value: int) -> FactoryProduct:
            return FactoryProduct(value)

        image = convert.encode(factory)
        assert convert.build(image, type) is not FactoryProduct
        method_image = convert.project(FactoryProduct(3).make_other).atom
        native_factory = convert.build(method_image)
        assert native_factory.__signature__.return_annotation is FactoryProduct
        assert convert.build(method_image, type) is not FactoryProduct
        assert convert.build(convert.encode(FactoryProduct), type) is FactoryProduct


@pytest.mark.parametrize("annotated", [False, True])
def test_operation_results_carry_declared_class_values(annotated):
    """The annotated projection and ordinary encoder preserve the class program."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class OperationClass:
            value: int

        def result() -> Any:
            return OperationClass

        result.__annotations__["return"] = type[OperationClass] if annotated else Any
        m.op(result, effect="readOnlyLookup")
        try:
            image = m.eval(S.result())[0]
            assert isinstance(image, Atom)
            assert convert.build(image, type) is OperationClass
            assert convert.build(image)(8).value == 8
        finally:
            m.unregister_op("result")


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
def test_class_values_bind_positional_and_keyword_segments(grain):
    """Class values bind both variadic dimensions through their native signature."""
    with MeTTa() as context:
        m = context.self
        base = Space if grain == "prototype" else object

        @m.define
        @dataclass(frozen=grain == "value", init=False)
        class SegmentClass(base):
            value: int

            def __init__(self, first: int, /, *values: int, offset: int = 1, **options: int):
                object.__setattr__(self, "value", first + sum(values) + offset + options.get("bonus", 0))

        native = convert.build(convert.encode(SegmentClass))
        assert native(1).value == 2
        assert native(1, 2, 3, offset=4, bonus=5).value == 15
        assert native(1, first=9).value == 2
        with pytest.raises(TypeError, match=r"missing.*first|positional only"):
            native(first=1)


def test_an_explicit_type_encoder_owns_declared_class_values():
    """The open encoding registry can replace the builtin class image."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ExplicitTypeImage:
            value: int

        previous = convert.encode.dispatch(type)
        try:
            convert.encode.register(type, lambda _cls: S.explicit_type_image)
            assert convert.encode(ExplicitTypeImage) == S.explicit_type_image
            assert convert.project(ExplicitTypeImage).atom == S.explicit_type_image
        finally:
            convert.encode.register(type, previous)
        assert convert.build(convert.encode(ExplicitTypeImage), type) is ExplicitTypeImage


def test_class_declaration_resolves_its_deferred_annotation_namespace():
    """Fields, constructors and methods can name their completed class at decoration."""
    with MeTTa() as context:
        m = context.self

        @m.define
        class DeferredClass:
            parent: DeferredClass | None  # noqa: F821 -- exercise an unpublished class annotation

            def __init__(self, parent: DeferredClass | None = None):  # noqa: F821 -- exercise an unpublished class annotation
                self.parent = parent

            def choose(self, value: DeferredClass) -> DeferredClass:  # noqa: F821 -- exercise an unpublished class annotation
                return value

        root = DeferredClass()
        child = DeferredClass(root)
        assert child.parent is root
        assert child.choose(root) is root
        assert child.choose.__signature__.return_annotation is DeferredClass


def test_retired_class_names_keep_the_native_scope_revocation():
    """Redeclaration cannot revive an escaped native name or partial registry."""
    with MeTTa() as context:
        m = context.self
        with m.scope():
            @m.define
            @dataclass
            class RetiredMethodClass:
                value: int

                def read(self) -> int:
                    return self.value

            owner = declaration(RetiredMethodClass)
            escaped = owner.space
        assert escaped.dropped
        assert declaration(RetiredMethodClass) is None
        with pytest.raises(EngineError, match="released_scope_space"):
            with m.scope():
                m.define(RetiredMethodClass)
        assert escaped.dropped
        assert declaration(RetiredMethodClass) is None
