"""Purpose: soft unification, the thing this substrate does that attention
alone cannot: match quality as a measure over TERMS. Structure stays crisp,
symbols are close to a degree (declared, or materialized from embeddings),
variables bind as ever, and soft-match's answers feed the measure algebra,
so ws-softmax over terms IS attention over expressions. Sessa's weak
unification (TCS 2002), running.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

from petta import MeTTa, S, V, expr, soft

m = MeTTa().fresh_space()
soft.install(m)

# Declared closeness; identity is 1.0, unrelated is 0.0, min aggregates.
soft.similar(m, "cat", "feline", 0.8)
(degree,) = m.run("!(soft-score (likes feline fish) (likes cat fish))")[0]
check("symbols soft, structure crisp", degree, 0.8)
check("arity mismatch is zero", m.run("!(soft-score (a b) (a b c))")[0][0], 0.0)

# The pattern's variables BIND while scoring: soft matching is unification.
(pair,) = m.run(
    "!(let $probe (soft-score (likes $who fish) (likes cat fish)) ($probe $who))"
)[0]
check("variables bind through the soft match", pair, expr(1.0, S.cat))

# A space of facts, softly matched, measured, decided.
m.add(S.likes(S.cat, S.fish), S.likes(S.dog, S.bones), S.likes(S.bird, S.seeds))
(best,) = m.run("!(soft-best (context-space) (likes feline $food))")[0]
check("the closest fact wins", best, expr(S.likes, S.cat, S.fish))

# The Python scorer mirrors the equations exactly (a differential fuzz in
# the test suite holds them equal); use it where a million scores would be
# a million engine calls.
table = {("cat", "feline"): 0.8}
check(
    "python mirror agrees",
    soft.score(m.parse("(likes feline fish)"), m.parse("(likes cat fish)"), table),
    0.8,
)
done("14_soft_unification")
