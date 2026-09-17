"""Purpose: examples/ch17-concurrency-and-the-loop/09-class_values.metta in Python.

A frozen dataclass is a constructor term: `@m.define` derives the arrow and
the accessors, compiles each method with `self` as its first parameter,
routes `a + b` to the class's `__add__`, and places the keyword patterns of
`case Point(x=0, y=y)` through `__match_args__`. The example writes those
rows by hand; this twin declares the class and proves the same claims.
"""

from dataclasses import dataclass

from metta import S, Symbol


def twin(m):
    """Declare the value class and prove the example's six claims."""
    @m.define
    @dataclass(frozen=True)
    class Point:
        x: int
        y: int

        def norm(self) -> float:
            return (self.x * self.x + self.y * self.y) ** 0.5

        def __add__(self, other: "Point") -> "Point":
            return Point(self.x + other.x, self.y + other.y)

        def quadrant(self) -> Symbol:
            match self:
                case Point(x=0, y=0):
                    return S.origin
                case Point(0, y=_):
                    return S.axis
                case Point(x=_):
                    return S.plane
            return S.nowhere

    # !(test (Point-norm (Point 3 4)) 5.0)
    assert Point(3, 4).norm() == 5.0
    # !(test (Point-add (Point 1 2) (Point 3 4)) (Point 4 6)): Python's + is the same equation.
    assert Point(1, 2) + Point(3, 4) == Point(4, 6)
    # !(test (Point-quadrant (Point 0 0)) origin) and its two siblings
    assert Point(0, 0).quadrant() == S.origin
    assert Point(0, 4).quadrant() == S.axis
    assert Point(3, 4).quadrant() == S.plane
    # !(test (== (Point-add (Point 1 2) (Point 3 4)) (Point 4 6)) True)
    assert m.eval(S.eq(S.Point_add(Point(1, 2), Point(3, 4)), S.Point(4, 6))) == [True]


#: The twin declares its classes, whose grains, accessors, method equations,
#: dispatch rows, call contracts and Python proxies the declaration derives,
#: and then proves the example's claims through them; the native example
#: writes only the rows its claims read. The difference is that declaration
#: and crossing work, the OVERRUN declared below.
#: [measured: 4656825 twin and 32388 native inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure
#: examples/ch17-concurrency-and-the-loop/09-class_values.metta; fixture=min of three
#: serial fresh processes in a provisioned battery worktree with the .qlf set
#: warm; commit=WORKTREE].
BUDGET = 4656825
OVERRUN = 4624437

#: DIVERGED 2026-09-18, the example holds 0 atoms the twin does not (none) and
#: the twin holds 25 atoms the example does not (24 :, 1 @doc): The twin's
#: @m.define derives the class's arrows, application and binding contracts and
#: documentation rows into the class space beside the equations the example
#: writes by hand, so the referenced content differs by exactly those derived
#: rows [measured 2026-09-18: the two stored-atom surpluses, one fresh process
#: per side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=WORKTREE].
DIVERGENCE = "0af119ddab683b19d470b30e1d26c37a54052ddb0c5cd3e1ac2cbfa7b65c0ab4"
