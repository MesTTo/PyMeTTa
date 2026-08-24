"""Purpose: examples/functions/functionhead2.metta in Python: a relational constraint, chained.

`animal` keeps whatever is living AND a being; `cat` takes what `animal`
produces and keeps whatever is also small. `small` is put under a
`NoMatchFail` dispatch policy first, so asking `small` about something it has
no fact for FAILS the relation instead of answering the unreduced call, which
is what makes `cat` a filter rather than a producer of residual terms.

The ten facts are a TABLE, so they are written as one: a dict from each animal
to the relations that hold of it, and a comprehension turning each pair into
its equation. That preserves the original's own reading order and says the
shape of the knowledge once instead of ten times. They cannot be decorated
functions: each head fixes a SYMBOL (`(living garfield)`), a stacked clause
fixes a head position with a literal DEFAULT, and a literal is a bool, int,
float or str, never a symbol.

The three relations that follow are ordinary decorated functions. `only`
forces its constraint with an ordinary assignment, which the compiler stores
as a `let*`; `cat` uses relational `let`, where `$X` is the hole unification
fills. The fact relations are explicit symbol calls because they are data
heads in this file, not Python definitions.

The claim dissolves twice over: `collapse` is the list an evaluation already
answers, and `msort` is Python's own `sorted`.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import metta
from metta import TRUE, S, V, equation
from metta.vocabularies import NoMatchEnum

#: The knowledge, as the table it is: each animal and what holds of it, in the
#: original's own order.
FACTS = {
    S.garfield: (S.living, S.being, S.small),
    S.snoopy: (S.living, S.being),
    S.roomba: (S.being, S.small),
    S.cat42: (S.living, S.being, S.small),
}

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1


def twin(m):
    """Filter ten facts through two chained relations."""
    metta.reflection += S.dispatch_policy(
        S.small, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail]
    )

    # (= (living garfield) True) ... (= (small cat42) True)
    # rung: each head fixes a SYMBOL, and a stacked clause's literal default is a
    #   bool, int, float or str (residue, P14.4)
    m.add(*(equation(rel(who)).to(TRUE) for who, rels in FACTS.items() for rel in rels))

    @m.define
    def only(c, x):
        # (= (only $C $X) (let* (($constraint $C)) $X))
        _constraint = c
        return x

    @m.define
    def animal(x):
        # (= (animal $X) (only ((living $X) (being $X)) $X))
        return only((S.living(x), S.being(x)), x)

    @m.define
    def cat(a):
        # (= (cat $A) (let $A (animal $X) (only (small $X) $X)))
        return S.let(  # rung: solve(pattern, subject) has no expression-position form inside a compiled body
            a, animal(V.x), only(S.small(V.x), V.x)
        )

    assert sorted(m.eval(S.cat(V.X))) == [S.cat42, S.garfield]
