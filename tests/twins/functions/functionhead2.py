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

The three relations that follow are ordinary decorated functions. Two of them
mint a variable no parameter supplies, which `V.` says inside a body:
`only` binds the constraint's result to `$constraint` and never reads it,
which is how it forces evaluation, and `cat` unifies its own argument against
what `animal` produces, where `$X` is the hole unification fills. `living` and
`being` are named as bare calls, the descent ladder's rung 4, because nothing
in Python binds those spellings and a compiled body resolves a free name
against the engine's own registry.

The claim dissolves twice over: `collapse` is the list an evaluation already
answers, and `msort` is Python's own `sorted`.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import petta
from petta import TRUE, S, V, equation

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
#: [assumed: unmeasured here, deliberately; commit=WORKTREE].
BUDGET = 1


def twin(m):
    """Filter ten facts through two chained relations."""
    petta.reflection += S["dispatch-policy"](S.small, S.NoMatchEnum, S.NoMatchFail)

    # (= (living garfield) True) ... (= (small cat42) True)
    # rung: each head fixes a SYMBOL, and a stacked clause's literal default is a
    #   bool, int, float or str (residue, P14.4)
    m.add(*(equation(rel(who)).to(TRUE) for who, rels in FACTS.items() for rel in rels))

    @m.define
    def only(c, x):
        # (= (only $C $X) (let $constraint $C $X)): the body binds $constraint,
        # a variable it never reads, which is how it forces evaluation. An
        # assignment would mint the name and store `let*` instead.
        return S.let(V.constraint, c, x)  # rung: let as a force

    @m.define
    def animal(x):
        # (= (animal $X) (only ((living $X) (being $X)) $X))
        return only((living(x), being(x)), x)  # noqa: F821  -- `living` and `being` are engine relations, and a compiled body resolves a free name against the engine's registry

    @m.define
    def cat(a):
        # (= (cat $A) (let $A (animal $X) (only (small $X) $X)))
        return S.let(a, animal(V.x),  # rung: relational let
                     only(small(V.x), V.x))  # noqa: F821  -- `small` is an engine relation, the same way

    assert sorted(m.eval(S.cat(V.X)), key=str) == [S.cat42, S.garfield]
