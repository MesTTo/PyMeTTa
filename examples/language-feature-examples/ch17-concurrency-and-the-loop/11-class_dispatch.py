"""Purpose: examples/ch17-concurrency-and-the-loop/11-class_dispatch.metta in Python.

Inheritance is a head pattern: a base method is one equation over `self`, a
subclass that redefines the name adds an equation over its own constructor,
`super().describe()` is the base's qualified spelling, and `get-type` with the
`:<` edges is what `isinstance` means. The example writes those rows by
hand; this twin declares the classes and proves the same claims.
"""

from dataclasses import dataclass

from metta import S, V


def twin(m):
    """Declare the shape hierarchy and prove the example's six claims."""
    @m.define
    @dataclass(frozen=True)
    class Shape:
        def area(self) -> int:
            return 0

        def describe(self):
            return S.area_of(self.area())

    @m.define
    @dataclass(frozen=True)
    class Circle(Shape):
        r: int

        def area(self) -> int:
            return 3 * (self.r * self.r)

        def describe(self):
            return S.circle(super().describe())

    @m.define
    @dataclass(frozen=True)
    class Square(Shape):
        s: int

        def area(self) -> int:
            return self.s * self.s

    # !(test (area (Circle 2)) 12)
    assert Circle(2).area() == 12
    # !(test (area (Square 3)) 9)
    assert Square(3).area() == 9
    # !(test (describe (Square 3)) (area-of 9))
    assert Square(3).describe() == S.area_of(9)
    # !(test (describe (Circle 2)) (circle (area-of 12)))
    assert Circle(2).describe() == S.circle(S.area_of(12))
    # !(test (collapse (get-type (Circle 2))) (quote (Circle Shape)))
    assert m.eval(S.get_type(Circle(2))) == [S.Circle, S.Shape]
    # !(test (collapse (match &Circle (:< Circle $base) $base)) (Shape))
    assert [row.base for row in m.metta.space(S.Circle)[S[":<"](S.Circle, V.base)]] == [S.Shape]


#: The twin declares its classes, whose grains, accessors, method equations,
#: dispatch rows, call contracts and Python proxies the declaration derives,
#: and then proves the example's claims through them; the native example
#: writes only the rows its claims read. The difference is that declaration
#: and crossing work, the OVERRUN declared below.
#: [measured: 10770478 twin and 311841 native inferences; command=python
#: extensions/python/tools/twin_coverage.py --measure
#: examples/ch17-concurrency-and-the-loop/11-class_dispatch.metta; fixture=min of three
#: serial fresh processes in a provisioned battery worktree with the .qlf set
#: warm; commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
#: RE-PINNED 2026-09-18, 10770478 to 10757553 (-12925), the branch's landings
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
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 10757553
OVERRUN = 10458637

#: DIVERGED 2026-09-18, the example holds 0 atoms the twin does not (none) and
#: the twin holds 70 atoms the example does not (67 :, 3 @doc): The twin's
#: @m.define derives the class's arrows, application and binding contracts and
#: documentation rows into the class space beside the equations the example
#: writes by hand, so the referenced content differs by exactly those derived
#: rows [measured 2026-09-18: the two stored-atom surpluses, one fresh process
#: per side; command=python extensions/python/tools/twin_coverage.py --repin;
#: commit=a8cfae1f5c0be628bc40eb7c18b07749d995e9a0].
DIVERGENCE = "23cfb7805396602395cdd90b0e1bac4fcf32796361eb120f9fb55f7e53b7d98f"
