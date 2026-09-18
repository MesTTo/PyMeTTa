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
#: warm; commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
#: RE-PINNED 2026-09-18, 4656825 to 4638229 (-18596), the branch's landings
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
#: RE-PINNED 2026-09-18, 4638229 to 4640297 (+2068), 49478d67a landed the
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
BUDGET = 4640297
OVERRUN = 4624437

#: DIVERGED 2026-09-18, the example holds 0 atoms the twin does not (none) and
#: the twin holds 25 atoms the example does not (24 :, 1 @doc): The twin's
#: @m.define derives the class's arrows, application and binding contracts and
#: documentation rows into the class space beside the equations the example
#: writes by hand, so the referenced content differs by exactly those derived
#: rows [measured 2026-09-18: the two stored-atom surpluses, one fresh process
#: per side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
DIVERGENCE = "0af119ddab683b19d470b30e1d26c37a54052ddb0c5cd3e1ac2cbfa7b65c0ab4"
