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
        self.value = False
        self.released = False

    def assign(self, value: bool) -> None:
        if self.released:
            raise RuntimeError(f"{self._atom} was released")
        if value and not self.value:
            self._m.add(self._atom)
        elif not value and self.value:
            self._m.remove(self._atom)
        self.value = bool(value)

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
        self._m.run(self._template(*args))
        self.grounded.add(args)


m = MeTTa().fresh_space()

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
    return any(a == True for a in m.eval(m.parse(f"(reach {goal} {t})")))  # noqa: E712


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
blocked.release()
done("multishot_solving")
