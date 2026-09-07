"""Purpose: EXPLAIN over this engine's own decisions.

A query says which join the matcher will run before it runs, an explanation is
ordinary atoms a space stores and matches back, analyze= measures the query it
describes, and an analysis that would mutate refuses until it is told to.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from metta import MeTTa, S, V

m = MeTTa().space()
m.add(S.edge(1, 2), S.edge(2, 3), S.edge(3, 1))

# Cyclic-join planning is a declared choice, so a triangle keeps the retained
# nested loop until a program asks for the trie plan.
m.run("!(pragma! plan-cyclic-joins True)")

e = m.explain("(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))")
check("the plan names the join that will run", str(e.plan.children[1]), "generic-join")
check("the route names the seam entry", str(e.route.children[1]), "none")
check("writes is an ordinary item", str(e["writes"]), "(writes undeclared)")

# The plan follows the ROUTE, not the query's shape: one stored row with a
# variable in it declines the trie plan, and the item says nested-loop.
with m._new_space() as loose:
    loose.add(S.edge(1, 2), S.edge(2, 3), S.edge(3, 1), S.edge(V.a, V.b))
    declined = loose.explain(
        f"(match {loose.name} (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))"
    )
    check("a non-ground row declines the plan", str(declined.plan.children[1]), "nested-loop")

# An explanation is data like anything else, so a space stores it and matches
# it back. The mapping is keyed by each item's head; .atoms is every item.
with m._new_space() as store:
    store.add(*e.atoms)
    (mode,) = store.match(S.plan(V.mode, V.order, V.relations)).mode
    check("the stored plan is queryable", str(mode), "generic-join")

# analyze= is EXPLAIN ANALYZE: the same items, plus what running the query cost.
measured = m.explain(
    "(match &self (, (edge $x $y) (edge $y $z) (edge $z $x)) ($x $y $z))", analyze=True
)
check("analyze counts the answers", measured["answers"].children[1].value, 3)
check("analyze counts the inferences", measured["inferences"].children[1].value > 0)

# A match TEMPLATE is evaluated once per answer, so a template that writes is a
# query that writes, and measuring it is refused until allow_writes says so.
try:
    m.explain("(match &self (edge $x $y) (add-atom &self (seen $x)))", analyze=True)
    refusal = "it did not refuse"
except ValueError as exc:
    refusal = "add-atom is writesState" in str(exc)
check("an analysis that mutates refuses", refusal)

# A query result explains the match it came from, pulling nothing to do it.
rows = m.match(S.edge(V.x, V.y), S.edge(V.y, V.z), S.edge(V.z, V.x))
check("rows explain themselves", str(rows.explain().plan.children[1]), "generic-join")

m.run("!(pragma! plan-cyclic-joins False)")
done("explaining_a_query")
