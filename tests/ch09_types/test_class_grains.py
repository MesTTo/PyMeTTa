"""Purpose: verify class grains against the engine's actual storage and lifetime.

Guarantees:
  - each test observes public answers and stored facts, including rolled-back
    allocation and Python aliases [tested: sh extensions/python/test.sh
    tests/ch09_types/test_class_grains.py -n 0; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
"""

from dataclasses import InitVar, dataclass, field
from enum import Enum
from typing import NamedTuple

import pytest

from metta import Expression, MeTTa, S, Space, V, convert
from metta._declare.classes import declaration
from metta._errors.errors import CompileError, EngineError


def test_a_retired_receiver_cannot_regain_fields_through_a_native_writer():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class GrainRetired:
            value: int

        term = m.eval(S["make-GrainRetired"](3))[0]
        m.eval(S["retire-GrainRetired"](term))
        home = declaration(GrainRetired).space
        before = home.digest()
        result = m.eval(S["GrainRetired-value!"](term, 4))
        assert home.digest() == before
        assert len(result) == 1 and result[0].head == S.Error
        assert "retired" in str(result[0])


def test_class_values_are_sorted_terms():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True, slots=True)
        class GrainPoint:
            x: int
            y: int = 4

        assert convert.project(GrainPoint(3)).atom == S.GrainPoint(3, 4)
        assert convert.build(S.GrainPoint(5, 6), GrainPoint) == GrainPoint(5, 6)
        assert m.run("!(make-GrainPoint 3)") == [[S.GrainPoint(3, 4)]]
        assert m.run("!(GrainPoint-x (GrainPoint 3 4))") == [[3]]
        assert S["from"](S["&GrainPoint"]) in m
        assert not m.is_function("GrainPoint")

        @m.define
        class GrainPair(NamedTuple):
            first: int
            second: int = 2

        assert m.run("!(make-GrainPair 1)") == [[S.GrainPair(1, 2)]]
        assert convert.build(S.GrainPair(1, 2), GrainPair) == GrainPair(1)

        @m.define
        class GrainColour(Enum):
            red = 1
            blue = 2

        assert convert.project(GrainColour.red).atom == S.GrainColour(S.red)
        assert convert.build(S.GrainColour(S.red), GrainColour) is GrainColour.red


def test_class_proxies_share_engine_fields():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(slots=True)
        class GrainAccount:
            balance: int = 0

        a, b = GrainAccount(10), GrainAccount(10)
        left, right = convert.project(a).atom, convert.project(b).atom
        assert left != right
        assert left.head == S.GrainAccount and left.args[0].head == S.t
        assert a.balance == b.balance == 10
        a.balance = 12
        assert m.eval(S["GrainAccount-balance"](left)) == [12]
        assert m.eval(S["GrainAccount-balance!"](left, 15)) == [True]
        assert a.balance == 15 and b.balance == 10
        assert convert.build(left, GrainAccount) is a
        home = declaration(GrainAccount).space
        assert home.eval(S.match(S[home.name], S["_field-balance"](left, V.value), V.value)) == [15]
        assert home.eval(S.match(S[home.name], S["owned-by"](V.self), V.self)) == [left, right]
        assert m.run("!(make-GrainAccount 3)")[0][0].head == S.GrainAccount


def test_class_constructors_compile_fields():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        class GrainCounter:
            count: int

            def __init__(self, start: int = 2):
                self.count = start
                self.count += 3

        @m.define
        def make_counter(start: int):
            counter = GrainCounter(start)
            return counter.count

        assert GrainCounter().count == 5
        assert m.run("!(make-counter 7)") == [[10]]
        assert "GrainCounter-count!" in str(declaration(GrainCounter).space.atoms())
        assert "py-" not in make_counter.source()


def test_class_value_post_init_and_write_refusal():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True, slots=True)
        class GrainDerived:
            x: int
            scale: InitVar[int] = 2
            doubled: int = field(init=False)

            def __post_init__(self, scale):
                object.__setattr__(self, "doubled", self.x * scale)

        assert m.run("!(make-GrainDerived 3)") == [[S.GrainDerived(3, 6)]]
        assert convert.build(S.GrainDerived(3, 6), GrainDerived) == GrainDerived(3)

        def change(value: GrainDerived):
            value.x = 9
            return value

        with pytest.raises(CompileError, match=r"dataclasses\.replace"):
            m.define(change)


def test_class_constructor_rollback():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        class GrainChecked:
            value: int

            def __init__(self, value: int):
                self.value = value
                assert value >= 0, "negative construction"

        home = declaration(GrainChecked).space
        before = home.digest()
        assert m.run("!(make-GrainChecked -1)")[0][0].head == S.Error
        assert home.digest() == before
        with pytest.raises(EngineError, match="negative construction"):
            GrainChecked(-1)
        assert home.digest() == before


def test_class_prototype_fields_live_in_private_spaces():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        class GrainAgent(Space):
            energy: int

            def __init__(self, energy: int):
                self.energy = energy

        a, b = GrainAgent(4), GrainAgent(9)
        left, right = convert.project(a).atom, convert.project(b).atom
        assert left.head == right.head == S.GrainAgent
        assert convert.encode(a) == left
        assert Expression([S.receiver, a]) == S.receiver(left)
        assert m.eval(a) == [left]
        assert left != right and a.name != b.name
        assert S["_field-energy"](4) in a
        assert S["_field-energy"](9) in b
        assert S["from"](S["&GrainAgent"]) in a
        assert a.eval(S["GrainAgent-energy"](left)) == [4]
        a.energy = 7
        assert b.energy == 9 and a.energy == 7
        assert convert.build(left, GrainAgent) is a
        a.drop()
        with pytest.raises(ReferenceError):
            convert.build(left, GrainAgent)
        assert b.energy == 9


def test_class_declaration_rollback():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @dataclass(slots=True)
        class GrainRolledBack:
            value: int

        original = GrainRolledBack.__init__

        def fail():
            m.define(GrainRolledBack)
            msg = "rollback declaration"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="rollback declaration"):
            m.transaction(fail)
        assert GrainRolledBack.__init__ is original
        assert declaration(GrainRolledBack) is None
        assert "&GrainRolledBack" not in m.space_names()
        m.define(GrainRolledBack)
        assert GrainRolledBack(4).value == 4


def test_class_grain_lifetimes():  # noqa: D103 -- pytest discovers this test; its name states the contract
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class GrainOwned:
            x: int

        @m.define
        def transient(x: int):
            instance = GrainOwned(x)
            result = instance.x
            del instance
            return result

        assert m.run("!(transient 6)") == [[6]]
        home = declaration(GrainOwned).space
        assert home.eval(S.match(S[home.name], S["owned-by"](V.self), V.self)) == []
        with m.scope():
            instance = GrainOwned(8)
            assert instance.x == 8
        with pytest.raises(ReferenceError):
            convert.project(instance)
    assert declaration(GrainOwned) is None
