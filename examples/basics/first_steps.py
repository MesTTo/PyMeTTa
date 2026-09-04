"""Purpose: the five-minute surface: run MeTTa source, build atoms in Python,
query with joins, evaluate, and see why an answer holds.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from metta import MeTTa, S, V, Expression, in_, not_

m = MeTTa().space()

# Source runs through the engine's own reader and compiler; one answer list
# per ! directive, grounded values arriving as Python values.
check("run", m.run("(= (double $x) (* $x 2))\n!(double 21)"), [[42]])

# Atoms are Python values: S mints symbols, V variables, application builds
# expressions, and none of it costs an engine call.
m.add(S.Parent(S.Tom, S.Bob), S.Parent(S.Bob, S.Ann), S.Parent(S.Ann, S.Zoe))
rows = m.match(S.Parent(V.gp, V.p), S.Parent(V.p, V.gc))
check("join count", len(rows), 2)
check("first grandparent", (rows[0].gp, rows[0].gc), (S.Tom, S.Ann))

# A unifier is already the substitution currency Atom.subs accepts, so a
# template can consume it directly without a recursive walk or string keys.
pattern = S.Parent(V.parent, V.child)
bindings = pattern.unify(S.Parent(S.Tom, S.Bob))
check("unification succeeds", bindings is not None)
check(
    "substitution consumes the unifier",
    S.Cares(V.parent, V.child).subs(bindings),
    S.Cares(S.Tom, S.Bob),
)
check("not_ spells Python's keyword safely", str(not_(S.ready)), "(not ready)")
check("in_ spells Python's keyword safely", str(in_(S.Ada, S.Team)), "(in Ada Team)")

# Evaluation is what ! runs, nondeterminism included.
check("eval", m.eval(S.superpose(Expression(1, 2, 3))), [1, 2, 3])

# And an answer can explain itself: the proof names equations and facts.
m.run("(= (anc $x $y) (match (context-space) (Parent $x $y) $y))\n"
      "(= (anc $x $y) (let $m (match (context-space) (Parent $x $m0) $m0) (anc $m $y)))")
(proof,) = m.derivation(S.anc(S.Tom, S.Zoe))
check("proof facts", len(proof.facts) >= 2)
done("first_steps")
