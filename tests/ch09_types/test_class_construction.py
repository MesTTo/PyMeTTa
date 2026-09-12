"""Purpose: verify constructor arguments, private fields and declaration owners.

Guarantees:
  - constructor defaults and field writes share rollback, while declaration
    references keep their providers alive [tested: sh extensions/python/test.sh
    tests/ch09_types/test_class_construction.py -n 0; commit=WORKTREE]
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from dataclasses import dataclass, field

import pytest

from metta import MeTTa, S, Space, V, convert, lib
from metta._binding.runtime import engine_thread
from metta._catalog.annotations import referenced_classes, type_atoms_for
from metta._declare.classes import declaration
from metta._errors.errors import CompileError, EngineError


def test_concrete_field_annotations_do_not_require_an_imported_module():  # noqa: D103 -- pytest discovers this test; its name states the contract
    @dataclass
    class ConstructionUnimported:
        value: int

    ConstructionUnimported.__module__ = "classes_unimported_module"
    with MeTTa() as context:
        context.self.define(ConstructionUnimported)
        value = ConstructionUnimported(7)
        assert value.value == 7
        assert context.self.eval(S["ConstructionUnimported-value"](value)) == [7]


def test_a_field_name_cannot_become_a_declaration():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ConstructionNames:
            internal: int = 3
            self: int = 4

        value = ConstructionNames()
        assert (value.internal, value.self) == (3, 4)
        value.internal = 7
        term = convert.project(value).atom
        assert m.eval(S["ConstructionNames-internal"](term)) == [7]
        assert m.eval(S["ConstructionNames-self"](term)) == [4]


def test_constructor_receivers_and_private_names_follow_the_defining_class():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        class ConstructionReceiver:
            __value: int

            def __init__(this, self: int, /, *, scale: int = 2):  # noqa: N805 -- the receiver name and a separate self parameter are the case under test
                this.__value = self * scale

        value = ConstructionReceiver(3, scale=4)
        assert value._ConstructionReceiver__value == 12
        with pytest.raises(TypeError):
            ConstructionReceiver(self=3)
        term = m.run("!(make-ConstructionReceiver 5 2)")[0][0]
        assert convert.build(term, ConstructionReceiver)._ConstructionReceiver__value == 10


def test_packed_constructor_parameters_keep_their_container_shapes():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        class ConstructionPacked:
            total: int

            def __init__(self, *values: int, **options: int):
                self.total = sum(values) + options["bonus"]

        @m.define
        def packed_constructor():
            return ConstructionPacked(2, 3, bonus=4)

        assert ConstructionPacked(2, 3, bonus=4).total == 9
        assert convert.build(m.eval(S["packed-constructor"]())[0], ConstructionPacked).total == 9
        plan = declaration(ConstructionPacked)
        native = plan.space.run('!(make-ConstructionPacked (2 3) (dict-space (("bonus" 4))))')[0][0]
        assert convert.build(native, ConstructionPacked).total == 9
        assert S[":"](S["make-ConstructionPacked"], S["->"](S.Expression, S.SpaceType, S.ConstructionPacked)) in plan.space
        assert S.internal(S["dict-space"]) in plan.space
        with pytest.raises(EngineError, match="internal"):
            m.from_(plan.space, S.only((S["dict-space"],)))


def test_constructor_dependencies_survive_a_previous_global_import_leaving():
    """Explicit class imports outlive an unrelated global library reference."""
    with MeTTa() as context:
        shared = Space("&self", _runtime=context.self._rt)
        row = S["from"](lib.dict.form, S.only((S["dict-space"], S["get-value"])))
        shared.add(row)
        try:
            @context.self.define
            class ConstructionWarm:
                total: int

                def __init__(self, **options: int):
                    self.total = options["bonus"]
        finally:
            shared.remove(row)
        assert ConstructionWarm(bonus=4).total == 4
        plan = declaration(ConstructionWarm)
        assert S.internal(S["dict-space"]) in plan.space
        assert S.internal(S["get-value"]) in plan.space


def test_object_setattr_preserves_the_literal_attribute_name():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        class ConstructionLiteralPrivate:
            __value: int

            def __init__(self):
                object.__setattr__(self, "__value", 3)

        with pytest.raises(CompileError, match="__value is not a declared field"):
            context.self.define(ConstructionLiteralPrivate)


def test_concurrent_reconstruction_publishes_one_python_proxy():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ConstructionConcurrent:
            value: int

        rendezvous = threading.Barrier(4)
        term = m.eval(S["make-ConstructionConcurrent"](7))[0]

        def reconstruct(_index):
            with engine_thread():
                rendezvous.wait()
                return convert.build(term, ConstructionConcurrent)

        with ThreadPoolExecutor(max_workers=4) as workers:
            copies = list(workers.map(reconstruct, range(4)))
        assert all(value is copies[0] for value in copies)
        plan = declaration(ConstructionConcurrent)
        assert len(plan.space.eval(S.match(S[plan.space.name], S["_python-proxy"](term, V.proxy), V.proxy))) == 1


def test_overlapping_transactions_cannot_publish_distinct_proxies():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ConstructionSnapshotProxy:
            value: int

        term = m.eval(S["make-ConstructionSnapshotProxy"](7))[0]
        rendezvous = threading.Barrier(2)
        provisional = []

        def reconstruct(_index):
            def body():
                rendezvous.wait()
                value = convert.build(term, ConstructionSnapshotProxy)
                provisional.append(value)
                rendezvous.wait()
                return value

            with engine_thread():
                try:
                    return m.transaction(body)
                except EngineError as error:
                    assert "retry the outer transaction" in str(error)
                    return None

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(reconstruct, range(2)))
        committed = [value for value in results if value is not None]
        assert len(committed) == 1
        assert m.transaction(lambda: convert.build(term, ConstructionSnapshotProxy)) is committed[0]
        discarded = next(value for value in provisional if value is not committed[0])
        with pytest.raises(ReferenceError, match="retired or its construction rolled back"):
            convert.project(discarded)


def test_a_rolled_back_proxy_check_cannot_refuse_the_outer_commit():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ConstructionDiscardedProxy:
            value: int

        term = m.eval(S["make-ConstructionDiscardedProxy"](7))[0]
        discarded = []

        def rejected():
            discarded.append(convert.build(term, ConstructionDiscardedProxy))
            msg = "discard proxy"
            raise ValueError(msg)

        def outer():
            with pytest.raises(ValueError, match="discard proxy"):
                m.transaction(rejected)
            return convert.build(term, ConstructionDiscardedProxy)

        value = m.transaction(outer)
        assert value.value == 7
        assert convert.build(term, ConstructionDiscardedProxy) is value
        assert m._rt.must("aggregate_all(count, metta_py_pending_proxy(_, _, _), Count)")["Count"] == 0
        with pytest.raises(ReferenceError, match="retired or its construction rolled back"):
            convert.project(discarded[0])


def test_a_plain_subclass_retains_its_actual_dataclass_initializer():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ConstructionBase:
            value: int

        @m.define
        class ConstructionDerived(ConstructionBase):
            extra: int = 7

        value = ConstructionDerived(3)
        term = convert.project(value).atom
        assert (value.value, value.extra) == (3, 7)
        assert m.eval(S["ConstructionDerived-extra"](term)) == [7]
        assert m.eval(S["ConstructionBase-value"](term)) == [3]
        with pytest.raises(TypeError):
            ConstructionDerived(3, 8)


def test_empty_container_defaults_use_the_catalog_image():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        @context.self.define
        @dataclass
        class ConstructionContainers:
            sequence: list = field(default_factory=list)
            mapping: dict = field(default_factory=dict)
            members: set = field(default_factory=set)
            fixed: tuple = field(default_factory=tuple)

        value = ConstructionContainers()
        assert (value.sequence, value.mapping, value.members, value.fixed) == ([], {}, set(), ())


@pytest.mark.parametrize("frozen", [False, True])
def test_private_accessors_still_serve_python_and_compiled_fields(frozen):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @dataclass(frozen=frozen)
        class ConstructionPrivateAccessors:
            value: int

        m.define(ConstructionPrivateAccessors, accessors=False)

        @m.define
        def private_value(value: ConstructionPrivateAccessors):
            return value.value

        value = ConstructionPrivateAccessors(5)
        term = convert.project(value).atom
        assert value.value == 5
        assert m.eval(S["ConstructionPrivateAccessors-value"](term)) == [S["ConstructionPrivateAccessors-value"](term)]
        assert m.eval(S["private-value"](term)) == [5]


@pytest.mark.parametrize("frozen", [False, True])
def test_default_factory_allocation_rolls_back_through_every_constructor_door(frozen):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ConstructionPayload:
            value: int = 1

        @m.define
        @dataclass(frozen=frozen)
        class ConstructionFactory:
            payload: ConstructionPayload = field(default_factory=ConstructionPayload)
            status: int = -1

            def __post_init__(self):
                assert self.status >= 0, "rejected default allocation"

        @m.define
        def rejected_factory():
            return ConstructionFactory(status=-1)

        @m.define
        def rejected_supplied_factory():
            return ConstructionFactory(payload=ConstructionPayload(), status=-1)

        homes = [declaration(cls).space for cls in (ConstructionFactory, ConstructionPayload)]
        spaces, rows = set(m.space_names()), [home.digest() for home in homes]
        for name in ("make-ConstructionFactory", "rejected-factory"):
            assert m.eval(S[name]())[0].head == S.Error
            assert set(m.space_names()) == spaces
            assert [home.digest() for home in homes] == rows
        with pytest.raises(EngineError, match="rejected default allocation"):
            ConstructionFactory()
        assert set(m.space_names()) == spaces
        assert [home.digest() for home in homes] == rows
        assert m.eval(S["rejected-supplied-factory"]())[0].head == S.Error
        assert homes[0].digest() == rows[0]
        assert len(homes[1].eval(S.match(S[homes[1].name], S["owned-by"](V.receiver), V.receiver))) == 1
        first, second = ConstructionFactory(status=0), ConstructionFactory(status=0)
        assert first.payload.value == second.payload.value == 1
        assert convert.project(first.payload).atom != convert.project(second.payload).atom


def test_a_declared_prototype_annotation_names_its_constructor_sort():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        class ConstructionPrototype(Space):
            value: int

        @m.define
        def prototype_value(instance: ConstructionPrototype):
            return instance.value

        assert type_atoms_for(ConstructionPrototype) == [S.ConstructionPrototype]
        assert referenced_classes([ConstructionPrototype]) == [ConstructionPrototype]
        assert m.eval(S["prototype-value"](convert.project(ConstructionPrototype(9)).atom)) == [9]


def test_a_referenced_constructor_outlives_its_first_declaring_home():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context, ExitStack() as cleanup:
        m = context.self
        first = Space("&ConstructionFirst", _runtime=m._rt)
        second = Space("&ConstructionSecond", _runtime=m._rt)
        cleanup.callback(first.drop)
        cleanup.callback(second.drop)

        @first.define
        @dataclass
        class ConstructionChild:
            value: int = 5

        @second.define
        @dataclass
        class ConstructionParent:
            child: ConstructionChild = field(default_factory=ConstructionChild)

        first.drop()
        assert declaration(ConstructionChild) is not None
        value = ConstructionParent()
        assert value.child.value == 5
        term = second.eval(S["make-ConstructionParent"]())[0]
        assert convert.build(term, ConstructionParent).child.value == 5
        second.drop()
        assert declaration(ConstructionChild) is None
        assert declaration(ConstructionParent) is None


def test_unowned_cycles_of_class_declarations_retire_together():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context, ExitStack() as cleanup:
        m = context.self
        first = Space("&ConstructionCycleFirst", _runtime=m._rt)
        second = Space("&ConstructionCycleSecond", _runtime=m._rt)
        cleanup.callback(first.drop)
        cleanup.callback(second.drop)

        @dataclass
        class ConstructionCycleLeft:
            peer: ConstructionCycleRight  # noqa: F821 -- Python's deferred class annotations resolve the later sibling

        @dataclass
        class ConstructionCycleRight:
            peer: ConstructionCycleLeft

        first.define(ConstructionCycleLeft)
        second.define(ConstructionCycleRight)
        first.drop()
        assert declaration(ConstructionCycleLeft) is not None
        second.drop()
        assert declaration(ConstructionCycleLeft) is None
        assert declaration(ConstructionCycleRight) is None


@pytest.mark.parametrize("compiled", [False, True])
def test_callable_annotations_reference_the_owned_class_declaration(compiled):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context, ExitStack() as cleanup:
        m = context.self
        first = Space("&ConstructionAnnotationFirst", _runtime=m._rt)
        second = Space("&ConstructionAnnotationSecond", _runtime=m._rt)
        cleanup.callback(first.drop)
        cleanup.callback(second.drop)

        @first.define
        @dataclass
        class ConstructionArgument:
            value: int

        def argument_identity(value: ConstructionArgument) -> ConstructionArgument:
            return value

        name = f"construction-argument-{'compiled' if compiled else 'operation'}"
        if compiled:
            second.define(argument_identity, name=name)
        else:
            second.op(argument_identity, name=name, effect="pureStructural")
            cleanup.callback(m.unregister_op, name)
        term = convert.project(ConstructionArgument(7)).atom
        assert S["from"](S["&ConstructionArgument"]) in second
        local = second._rt.must(
            "findall(_Token, (spaces:metta_space_pair(Space, [':', 'ConstructionArgument', _], _Token, _), "
            "\\+ metta_engine:metta_reference_projection(Space, _, _Token, _)), Tokens)",
            Space=second.name,
        )
        assert local["Tokens"] == []
        first.drop()
        assert declaration(ConstructionArgument) is not None
        assert second.eval(S[name](term)) == [term]
        second.drop()
        assert declaration(ConstructionArgument) is None


def test_scope_cleanup_retires_a_class_even_before_its_borrowers():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self
        with pytest.raises(ValueError, match="scope body"), m.scope():
            @m.define
            @dataclass
            class ConstructionScoped:
                value: int

            ConstructionScoped(4)
            msg = "scope body"
            raise ValueError(msg)
        assert declaration(ConstructionScoped) is None


@pytest.mark.parametrize("grain", ["value", "entity", "prototype"])
@pytest.mark.parametrize("scoped_home", [False, True])
def test_a_kept_receiver_keeps_its_scoped_class_program(grain, scoped_home):  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context, ExitStack() as cleanup:
        m = context.self
        with m.scope():
            with m.scope() as inner:
                home = m.metta.space() if scoped_home else m
                base = Space if grain == "prototype" else object
                # Separate names preserve Scope's revocation of released names.
                @dataclass(frozen=grain == "value")
                class ConstructionKept(base):
                    value: int

                convert.register_type(ConstructionKept, name=f"ConstructionKept{grain}{scoped_home}")
                cleanup.callback(convert.unregister_type, ConstructionKept)
                home.define(ConstructionKept)
                value = ConstructionKept(8)
                inner.keep(value)
            assert value.value == 8
            term = convert.project(value).atom
            plan = declaration(ConstructionKept)
            assert plan is not None
            assert plan.space.eval(plan.accessor("value")(term)) == [8]
        assert declaration(ConstructionKept) is None
