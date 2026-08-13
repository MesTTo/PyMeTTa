"""Purpose: clingo's multi-shot solving on the lingua-franca reading
(Gebser et al., "Multi-shot ASP solving with clingo", arXiv 1705.09811):
the program changes between solves without rebuilding the world. Parts are
parameterized program templates grounded once per instantiation, externals
are truths toggled between solves, and the solve side is the query surface
the space already has. The loop below is clingo's incremental deepening:
ground one more step until the goal proves.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from petta import MeTTa, S, V, multishot

m = MeTTa().fresh_space()

# The base part: a graph as tabular facts, and step zero of reachability.
m.add_table("edge", [(S.a, S.b), (S.b, S.c), (S.c, S.d)])
m.run("(= (reach a 0) True)")

# The step part, clingo's #program step(t): reach $x at t if some edge
# reaches it from a node already reached at t-1.
step = multishot.part(
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
check("grounded instantiations are tracked", step.grounded(), {(1,), (2,), (3,)})

# Externals: truths toggled between solves. A blocked node cuts routes in
# the NEXT shot without regrounding anything.
blocked = multishot.external(m, S.blocked(S.c))
blocked.assign(True)
check(
    "the external is a fact while assigned",
    [str(r.x) for r in m.query(S.blocked(V.x))],
    ["c"],
)
blocked.assign(False)
check("and gone when withdrawn", m.query(S.blocked(V.x)), [])
blocked.release()
done("16_multishot_solving")
