"""Purpose: clingo's multi-shot solving on the lingua-franca reading
(Gebser et al., "Multi-shot ASP solving with clingo", arXiv 1705.09811),
built HERE, on the core surface alone: the program changes between solves
without rebuilding the world. A Part is a parameterized program template
grounded once per instantiation, clingo's #program; an External is a truth
toggled between solves and ended by release, clingo's #external, which on
an engine with no grounding step is exactly a togglable fact. The two
classes below are the whole translation; the solve side is the query
surface the space already has.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from petta import MeTTa, S, V


class External:
    """A truth toggled between solves: present while True, gone while
    False, finished by release(). The handle owns its atom."""

    def __init__(self, m, atom) -> None:
        self._m, self._atom = m, atom
        self.released = False

    @property
    def value(self) -> bool:
        """Read the space, do not remember it.

        A cached truth diverges the moment anything else touches the same
        atom, and both directions were wrong: a MeTTa program removing the
        fact left the handle saying True, and one adding it left release()
        with nothing to take back out. The space owns the truth, which is
        also clingo's own arrangement, where a #external's assignment lives
        in the solver and not in the caller.
        """
        return bool(self._m.query(self._atom))

    def assign(self, value: bool) -> None:
        if self.released:
            raise RuntimeError(f"{self._atom} was released")
        if value:
            if not self.value:
                self._m.add(self._atom)
        else:
            while self.value:
                self._m.remove(self._atom)

    def release(self) -> None:
        if not self.released:
            self.assign(False)
            self.released = True


class Part:
    """A named program template, grounded once per instantiation: the
    template answers MeTTa source for its parameters, and grounding the
    same instantiation twice would duplicate its rules, so it refuses."""

    def __init__(self, m, name: str, template) -> None:
        self._m, self.name, self._template = m, name, template
        self.grounded: set[tuple] = set()

    def ground(self, *args) -> None:
        if args in self.grounded:
            raise RuntimeError(f"part {self.name!r} already grounded for {args!r}")
        # atomic=True, so a template that writes and then raises leaves
        # nothing behind. Without it the writes it managed stayed while
        # `grounded` stayed empty, and the retry the caller was invited to
        # make duplicated them.
        self._m.run(self._template(*args), atomic=True)
        self.grounded.add(args)


m = MeTTa().new_space()

# The base part: a graph as tabular facts, and step zero of reachability.
m.add_table("edge", [(S.a, S.b), (S.b, S.c), (S.c, S.d)])
m.run("(= (reach a 0) True)")

# The step part, clingo's #program step(t): reach $x at t if some edge
# reaches it from a node already reached at t-1.
step = Part(
    m,
    "step",
    lambda t: f"(= (reach $x {t}) (match (context-space) (edge $y $x) "
              f"(once (reach $y {t - 1}))))",
)


def proved(goal: str, t: int) -> bool:
    return any(m.eval(m.parse(f"(reach {goal} {t})")))


# The multi-shot loop: solve, and if the goal is not yet proved, ground
# one more step and solve again. The world persists between shots.
horizon = 0
while not proved("d", horizon):
    horizon += 1
    step.ground(horizon)
check("the goal proves at the shortest horizon", horizon, 3)
check("grounded instantiations are tracked", step.grounded, {(1,), (2,), (3,)})

# Externals: truths toggled between solves. A blocked node cuts routes in
# the NEXT shot without regrounding anything.
blocked = External(m, S.blocked(S.c))
blocked.assign(True)
check(
    "the external is a fact while assigned",
    [str(r.x) for r in m.query(S.blocked(V.x))],
    ["c"],
)
blocked.assign(False)
check("and gone when withdrawn", m.query(S.blocked(V.x)), [])

# The truth is the space's, not the handle's. A MeTTa program adding the same
# fact is visible to the handle, and release() takes it back out; a handle
# remembering its own last assignment would have disagreed with the space in
# both directions.
m.run("!(add-atom (context-space) (blocked c))")
check("the handle reads the space", blocked.value, True)
blocked.release()
check("release takes back out what it finds", m.query(S.blocked(V.x)), [])

# Grounding is all or nothing. A template that writes and then raises leaves
# nothing behind, so the retry the caller is invited to make cannot duplicate
# the rules the first attempt managed. The raise has to be a HOST error:
# arithmetic on a wrongly typed operand and integer division by zero ANSWER
# `(Error ...)` and would leave the write standing, a successful grounding.
broken = Part(m, "broken", lambda: "(kept one)\n!(+ $left $right)")
try:
    broken.ground()
    check("a failed grounding raises", "did not raise", "raised")
except Exception:  # noqa: BLE001 - any failure inside the template
    check("a failed grounding leaves nothing", m.query(S.kept(V.x)), [])
    check("and is not recorded as grounded", broken.grounded, set())

done("multishot_solving")
