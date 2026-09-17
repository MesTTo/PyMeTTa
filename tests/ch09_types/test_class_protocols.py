"""Purpose: verify the special methods and decorators of a declared class through both notations.

Guarantees:
  - syntax Python routes to a special method lowers to the class's own
    dispatch entry when the operand's static type is declared, and Python's
    operators on the instance reach the same equation [tested:
    extensions/python/tests/ch09_types/test_class_protocols.py; commit=WORKTREE]
"""

import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import final

import pytest

from metta import Expression, MeTTa, S, V
from metta._declare.classes import declaration
from metta._errors.errors import CompileError


def _vector(m):
    @m.define
    @dataclass(frozen=True)
    class ProtoVector:
        x: int
        y: int

        def __add__(self, other: "ProtoVector") -> "ProtoVector":
            return ProtoVector(self.x + other.x, self.y + other.y)

        def __sub__(self, other: "ProtoVector") -> "ProtoVector":
            return ProtoVector(self.x - other.x, self.y - other.y)

        def __rmul__(self, scale: int) -> "ProtoVector":
            return ProtoVector(scale * self.x, scale * self.y)

        def __neg__(self) -> "ProtoVector":
            return ProtoVector(0 - self.x, 0 - self.y)

        def __abs__(self) -> int:
            return self.x * self.x + self.y * self.y

        def __repr__(self) -> str:
            return "vector"

    return ProtoVector


def test_operators_on_a_declared_value_lower_to_its_special_methods():
    """Binary, reflected, unary and builtin forms reach the dunder's equation, and Python's operators reach it too."""
    with MeTTa() as context:
        m = context.self
        vector = _vector(m)

        @m.define
        def combine(a: vector, b: vector) -> vector:
            return a + b - vector(1, 1)

        @m.define
        def scaled(k: int, v: vector) -> vector:
            return k * v

        @m.define
        def flipped(v: vector) -> vector:
            return -v

        @m.define
        def size(v: vector) -> int:
            return abs(v)

        @m.define
        def shown(v: vector) -> str:
            return repr(v)

        assert "ProtoVector:dispatch:add" in combine.source() and "py-operator" not in combine.source()
        assert "ProtoVector:dispatch:rmul" in scaled.source()
        assert m.eval(S.combine(vector(1, 2), vector(3, 4))) == [S.ProtoVector(3, 5)]
        assert m.eval(S.scaled(3, vector(1, 2))) == [S.ProtoVector(3, 6)]
        assert m.eval(S.flipped(vector(1, 2))) == [S.ProtoVector(-1, -2)]
        assert m.eval(S.size(vector(3, 4))) == [25]
        assert m.eval(S.shown(vector(3, 4))) == ["vector"]
        # Python's own operator on the instance is the same equation: rewrite it natively.
        assert vector(1, 2) + vector(3, 4) == vector(4, 6)
        owner = declaration(vector)
        owner.space.remove(S["="](S["ProtoVector-add"](V.self, V.other), V.body))
        owner.space.add(S["="](S["ProtoVector-add"](V.self, V.other), S.ProtoVector(0, 0)))
        assert vector(1, 2) + vector(3, 4) == vector(0, 0)
        assert m.eval(S.combine(vector(1, 2), vector(3, 4))) == [S.ProtoVector(-1, -1)]


def test_an_operator_costs_exactly_the_method_call_it_stands_for():
    """`a + b` is `a.__add__(b)`: the same dispatch entry, which costs no more than the canonical equation."""
    with MeTTa() as context:
        m = context.self
        vector = _vector(m)

        @m.define
        def added(a: vector, b: vector) -> vector:
            return a + b

        @m.define
        def called(a: vector, b: vector) -> vector:
            return a.__add__(b)

        left, right = vector(1, 2), vector(3, 4)
        owner = declaration(vector)
        forms = {
            "operator": (m, S.added(left, right)),
            "call": (m, S.called(left, right)),
            "dispatch": (owner.space, S["ProtoVector:dispatch:add"](left, right)),
            "canonical": (owner.space, S["ProtoVector-add"](left, right)),
        }
        costs = {}
        for name, (space, form) in forms.items():
            for _ in range(2):  # warm the entries
                assert space.eval(form) == [S.ProtoVector(4, 6)]
            with m.stats() as spent:
                assert space.eval(form) == [S.ProtoVector(4, 6)]
            costs[name] = spent.inferences
        assert costs["operator"] == costs["call"], costs
        assert costs["dispatch"] <= costs["canonical"], costs


def test_comparisons_derive_from_dataclass_order_and_total_ordering():
    """order=True is lexicographic on the fields; total_ordering derives the rest from the root and eq."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True, order=True)
        class ProtoVersion:
            major: int
            minor: int

        @m.define
        @functools.total_ordering
        @dataclass
        class ProtoMoney:
            cents: int

            def __eq__(self, other: "ProtoMoney") -> bool:
                return self.cents == other.cents

            def __lt__(self, other: "ProtoMoney") -> bool:
                return self.cents < other.cents

        @m.define
        def newer(a: ProtoVersion, b: ProtoVersion) -> bool:
            return a > b

        @m.define
        def at_most(a: ProtoMoney, b: ProtoMoney) -> bool:
            return a <= b

        @m.define
        def differ(a: ProtoMoney, b: ProtoMoney) -> bool:
            return a != b

        assert m.eval(S.newer(ProtoVersion(2, 0), ProtoVersion(1, 9))) == [True]
        assert m.eval(S.newer(ProtoVersion(1, 9), ProtoVersion(2, 0))) == [False]
        assert m.eval(S.newer(ProtoVersion(1, 9), ProtoVersion(1, 9))) == [False]
        assert set(m.eval(S["ProtoVersion-le"](ProtoVersion(1, 9), ProtoVersion(1, 9)))) == {True}
        cheap, dear = ProtoMoney(5), ProtoMoney(7)
        assert m.eval(S.at_most(cheap, dear)) == [True]
        assert m.eval(S.at_most(dear, cheap)) == [False]
        assert m.eval(S.at_most(cheap, ProtoMoney(5))) == [True]
        assert m.eval(S.differ(cheap, dear)) == [True]
        assert ProtoMoney(5) <= ProtoMoney(5) and not ProtoMoney(7) <= ProtoMoney(5)
        assert ProtoVersion(2, 0) > ProtoVersion(1, 9)


def test_containers_iterate_index_contain_and_truth_test_through_their_methods():
    """len, for, [], in and if reach __len__, a generator __iter__, __getitem__, __contains__ and __bool__."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ProtoStack:
            items: tuple[int, ...]

            def __len__(self) -> int:
                return len(self.items)

            def __iter__(self):
                for item in self.items:  # noqa: UP028 -- the loop over a field read is the lowering under test
                    yield item

            def __getitem__(self, index: int) -> int:
                return self.items[index]

            def __contains__(self, item: int) -> bool:
                return item in self.items

            def __bool__(self) -> bool:
                return len(self.items) > 0

        @m.define
        def total(s: ProtoStack) -> int:
            acc = 0
            for item in s:
                acc += item
            return acc

        @m.define
        def summary(s: ProtoStack) -> tuple[int, int, bool, bool]:
            if s:
                return (len(s), s[0], 2 in s, True)
            return (0, 0, False, False)

        @m.define
        def doubled(s: ProtoStack) -> list[int]:
            return [item * 2 for item in s]

        full, empty = ProtoStack((1, 2, 3)), ProtoStack(())
        assert m.eval(S.total(full)) == [6]
        assert m.eval(S.summary(full)) == [(3, 1, True, True)]
        assert m.eval(S.summary(empty)) == [(0, 0, False, False)]
        assert m.eval(S.doubled(full)) == [Expression([2, 4, 6])]
        assert "ProtoStack:dispatch:len" in summary.source() and "py-len" not in summary.source()
        assert len(full) == 3 and list(full) == [1, 2, 3] and full[1] == 2 and (2 in full) and bool(empty) is False


def test_calls_context_managers_and_augmented_assignment_reach_their_methods():
    """a(x), with a as v and a += b lower to __call__, __enter__/__exit__ and __iadd__ or __add__."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class ProtoAdder:
            n: int

            def __call__(self, x: int) -> int:
                return self.n + x

            def __add__(self, other: "ProtoAdder") -> "ProtoAdder":
                return ProtoAdder(self.n + other.n)

        @m.define
        @dataclass
        class ProtoSession:
            depth: int
            log: list[str] = field(default_factory=list)

            def __enter__(self) -> "ProtoSession":  # noqa: PYI034 -- the compiler reads the class name, not Self
                self.depth = self.depth + 1
                return self

            def __exit__(self, _kind, _value, _trace) -> None:
                self.depth = self.depth - 1

        @m.define
        def applied(a: ProtoAdder) -> int:
            b = a
            b += ProtoAdder(10)
            return b(4)

        @m.define
        def inside(s: ProtoSession) -> int:
            with s as opened:
                seen = opened.depth
            return seen  # noqa: RET504 -- the binding inside the with block is the subject

        assert m.eval(S.applied(ProtoAdder(1))) == [15]
        session = ProtoSession(0)
        assert m.eval(S.inside(session)) == [1]
        assert session.depth == 0
        with session as opened:
            assert opened.depth == 1
        assert session.depth == 0
        assert ProtoAdder(2)(3) == 5


def test_keyword_class_patterns_place_fields_through_match_args():
    """A keyword class pattern is the positional term through __match_args__ on a value; an entity refuses."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass(frozen=True)
        class PatternPoint:
            x: int
            y: int

        @m.define
        @dataclass
        class PatternCell:
            row: int

        @m.define
        def where(p: PatternPoint) -> str:
            match p:
                case PatternPoint(x=0, y=0):
                    return "origin"
                case PatternPoint(0, y=_):
                    return "axis"
                case PatternPoint(x=_):
                    return "plane"
            return "nowhere"

        assert m.eval(S.where(PatternPoint(0, 0))) == ["origin"]
        assert m.eval(S.where(PatternPoint(0, 4))) == ["axis"]
        assert m.eval(S.where(PatternPoint(3, 4))) == ["plane"]
        with pytest.raises(CompileError, match="declared value class") as caught:
            @m.define
            def which(c: PatternCell) -> str:
                match c:
                    case PatternCell(row=0):
                        return "top"
                return "below"
        assert caught.value.construct == "class pattern"


def test_properties_static_and_class_methods_and_memoised_members():
    """Property reads and writes, staticmethod, classmethod, cached_property and cache lower and bind."""
    with MeTTa() as context:
        m = context.self

        @m.define
        @dataclass
        class ProtoAccount:
            cents: int
            reads: int = 0

            @property
            def balance(self) -> int:
                return self.cents

            @balance.setter
            def balance(self, value: int) -> None:
                self.cents = value

            @staticmethod
            def fee(amount: int) -> int:
                return amount // 10

            @classmethod
            def empty(cls) -> "ProtoAccount":
                return ProtoAccount(0)

            @functools.cached_property
            def digest(self) -> int:
                return self.cents * 7

            @functools.cache  # noqa: B019 -- the memoised method is the subject
            def doubled(self) -> int:
                return self.cents * 2

        @m.define
        def deposit(a: ProtoAccount, amount: int) -> int:
            a.balance = a.balance + amount - ProtoAccount.fee(amount)
            return a.balance

        @m.define
        def fresh() -> ProtoAccount:
            return ProtoAccount.empty()

        @m.define
        def summarize(a: ProtoAccount) -> tuple[int, int]:
            return (a.digest, a.doubled())

        account = ProtoAccount(100)
        assert m.eval(S.deposit(account, 50)) == [145]
        assert account.balance == 145
        account.balance = 10
        assert account.cents == 10
        assert ProtoAccount.fee(30) == 3
        assert str(fresh().one()).startswith("(ProtoAccount ")
        assert ProtoAccount.empty().cents == 0
        assert m.eval(S.summarize(account)) == [(70, 20)]
        owner = declaration(ProtoAccount)
        assert owner.space.eval(S["ProtoAccount-fee"](30)) == [3]
        assert str(owner.space.eval(S["ProtoAccount-empty"](S.ProtoAccount))[0]).startswith("(ProtoAccount ")
        with m.stats() as first:
            assert account.doubled() == 20
        with m.stats() as second:
            assert account.doubled() == 20
        assert second.inferences < first.inferences


def test_abstract_final_override_dispatch_and_partial_members():
    """Abstract arrows conform at declaration, final seals, override checks, singledispatch and partial derive."""
    with MeTTa() as context:
        m = context.self

        @m.define
        class ProtoShape(ABC):
            @abstractmethod
            def area(self) -> int: ...

            @final
            def name(self) -> str:
                return "shape"

        owner = declaration(ProtoShape)
        assert S.abstract(S["ProtoShape-area"]) in owner.space

        with pytest.raises(CompileError, match="abstract") as missing:
            @m.define
            @dataclass
            class ProtoBlob(ProtoShape):
                pass
        assert missing.value.construct == "abstract method"

        with pytest.raises(CompileError, match="final") as sealed:
            @m.define
            @dataclass
            class ProtoNamed(ProtoShape):
                def area(self) -> int:
                    return 1

                def name(self) -> str:
                    return "named"
        assert sealed.value.construct == "final method"

        @m.define
        @dataclass
        class ProtoSquare(ProtoShape):
            side: int

            def area(self) -> int:
                return self.side * self.side

        assert ProtoSquare(3).area() == 9 and m.eval(S.area(ProtoSquare(3))) == [9]

        @m.define
        class ProtoFormatter:
            @functools.singledispatchmethod
            def show(self, _value) -> str:
                return "other"

            @show.register
            def _(self, _value: int) -> str:
                return "number"

            def scale(self, factor: int, value: int) -> int:
                return factor * value

            twice = functools.partialmethod(scale, 2)

        @m.define
        def shown(f: ProtoFormatter, value: int) -> str:
            return f.show(value)

        formatter = ProtoFormatter()
        assert formatter.show(3) == "number" and formatter.show("s") == "other"
        assert m.eval(S.shown(formatter, 3)) == ["number"]
        assert formatter.twice(5) == 10

        with pytest.raises(CompileError, match="__del__") as finaliser:
            @m.define
            class ProtoDoomed:
                def __del__(self) -> None:
                    pass
        assert finaliser.value.construct == "del method"
