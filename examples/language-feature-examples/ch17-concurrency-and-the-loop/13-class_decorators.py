"""Purpose: examples/ch17-concurrency-and-the-loop/13-class_decorators.metta in Python.

The decorators and special methods of a class are rows the engine already
has: a property is an accessor equation, a class method takes the class
symbol, a static method has no receiver, `functools.total_ordering` derives
the comparisons it wrote from the root and equality, `__add__`, `__len__`,
`__iter__` and `__call__` are the words add, len, iter and call, and an
abstract method is an arrow with no equation. The example writes those rows
by hand; this twin declares the classes and proves the same claims.
"""

import functools
from abc import ABC, abstractmethod
from dataclasses import dataclass

from metta import S, V


def twin(m):
    """Declare the decorated classes and prove the example's twelve claims."""
    @m.define
    @dataclass(frozen=True)
    class Circle:
        r: int

        @property
        def area(self) -> int:
            return 3 * (self.r * self.r)

        @classmethod
        def unit(cls) -> "Circle":
            return Circle(1)

        @staticmethod
        def grow(r: int, by: int) -> int:
            return r + by

    @m.define
    @functools.total_ordering
    @dataclass(frozen=True)
    class Money:
        cents: int

        def __eq__(self, other: "Money") -> bool:
            return self.cents == other.cents

        def __lt__(self, other: "Money") -> bool:
            return self.cents < other.cents

    @m.define
    @dataclass(frozen=True)
    class Vector:
        x: int
        y: int

        def __add__(self, other: "Vector") -> "Vector":
            return Vector(self.x + other.x, self.y + other.y)

    @m.define
    @dataclass(frozen=True)
    class Stack:
        items: tuple[int, ...]

        def __len__(self) -> int:
            return len(self.items)

        def __iter__(self):
            for item in self.items:  # noqa: UP028 -- each yield is one answer, the generator lowering
                yield item

    @m.define
    @dataclass(frozen=True)
    class Adder:
        n: int

        def __call__(self, x: int) -> int:
            return self.n + x

    @m.define
    class Shape(ABC):
        @abstractmethod
        def area(self) -> int: ...

    @m.define
    @dataclass(frozen=True)
    class Square(Shape):
        s: int

        def area(self) -> int:
            return self.s * self.s

    # !(test (Circle-area (Circle 2)) 12)
    assert Circle(2).area == 12
    # !(test (Circle-unit Circle) (Circle 1))
    assert Circle.unit() == Circle(1)
    # !(test (Circle-grow 2 3) 5)
    assert Circle.grow(2, 3) == 5
    # !(test (Money-le (Money 5) (Money 5)) True)
    assert Money(5) <= Money(5)
    # !(test (Money-gt (Money 7) (Money 5)) True)
    assert Money(7) > Money(5)
    # !(test (Money-gt (Money 5) (Money 5)) False)
    assert not Money(5) > Money(5)
    # !(test (Vector-add (Vector 1 2) (Vector 3 4)) (Vector 4 6))
    assert Vector(1, 2) + Vector(3, 4) == Vector(4, 6)
    # !(test (Stack-len (Stack (1 2 3))) 3)
    assert len(Stack((1, 2, 3))) == 3
    # !(test (collapse (Stack-iter (Stack (1 2 3)))) (1 2 3))
    assert list(Stack((1, 2, 3))) == [1, 2, 3]
    # !(test (Adder-call (Adder 10) 4) 14)
    assert Adder(10)(4) == 14
    # !(test (Square-area (Square 3)) 9)
    assert Square(3).area() == 9
    # !(test (collapse (match &Shape (: Shape-area $arrow) $arrow)) ((-> Shape Number)))
    assert [row.arrow for row in m.metta.space(S.Shape)[S[":"](S.Shape_area, V.arrow)]] == [S["->"](S.Shape, S.Number)]


#: The twin declares its classes, whose grains, accessors, method equations,
#: dispatch rows, call contracts and Python proxies the declaration derives,
#: and then proves the example's claims through them; the native example
#: writes only the rows its claims read. The difference is that declaration
#: and crossing work, the OVERRUN declared below.
#: [measured: 13979257 twin and 249305 native inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure
#: examples/ch17-concurrency-and-the-loop/13-class_decorators.metta; fixture=min of three
#: serial fresh processes in a provisioned battery worktree with the .qlf set
#: warm; commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
#: RE-PINNED 2026-09-18, 13979257 to 13952303 (-26954), the branch's landings
#: since the 09-10 pins, re-taken on the tip f06186a96: the compiled call law
#: (e59104ace: an Atom argument enters as written, a Python object crosses as a
#: value, a positional call of a bound callee is the plain application and a
#: compiled lambda is bare where it is applied), the one codec at the grounded
#: call (fd0af38f7, whose read of a call site's written keyword tail costs
#: about six inferences per translated site, read once since 7cc8fb863), the
#: runnable cache's dependency index written by the producer (a9e2c06d3, which
#: takes back the walk of the generated code 5416e741d charged at every miss),
#: the host patches of 09-17 and the class units of 09-13 to 09-16 the ladder
#: in docs/journal/2026-09-14-runnable-artifact-dependencies.md places; serial
#: minimum of three fresh processes through the lane's run_twin with
#: file_search_cache_time=9223372036854775807 set before child boot [measured
#: 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=6944d06ce96fdbcd1faefb640f15dbfa0cf286dd].
#: RE-PINNED 2026-09-18, 13952303 to 13950837 (-1466), 49478d67a landed the
#: polynomial carrier, whose preset row and variable claim every catalog scan
#: reads, the product carriers and the guard read in the fixpoint door, and the
#: binding's five-element rule read: the examples that scan the catalog moved
#: with their twins (restricted_spaces +522, the three pln twins +63 each, the
#: two tabling twins +20 and +10, reflect_lib +6) and the twins that cross the
#: seat's declaration and query paths moved with their examples unmoved (the
#: class twins between -4212 and +2841, the reference twins +208 and +317, the
#: tagged fixpoint twin +610, the documentation twins -22 and -50, types_nondet
#: +5) [measured 2026-09-18: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 13950837
OVERRUN = 13729952

#: DIVERGED 2026-09-18, the example holds 0 atoms the twin does not (none) and
#: the twin holds 113 atoms the example does not (100 :, 13 @doc): The twin's
#: @m.define derives the class's arrows, application and binding contracts and
#: documentation rows into the class space beside the equations the example
#: writes by hand, so the referenced content differs by exactly those derived
#: rows [measured 2026-09-18: the two stored-atom surpluses, one fresh process
#: per side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
DIVERGENCE = "c7ef13de8b97b32596745a6f10048a9c9662d7c32af16a8f3eb96ab6d52f46f2"
