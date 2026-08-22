"""examples/functions/functionhead2.metta in Python: a relational constraint, chained.

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

`only` and `cat` take the `@rules` shape of the definitional decorator,
because both bodies mint a variable that is not a parameter. `only` binds the
constraint's result to `$constraint` and never reads it, which is how it
forces evaluation; `cat` unifies its own argument against what `animal`
produces, and `$X` is the hole that unification fills. A compiled body can
introduce neither.

The claim dissolves twice over: `collapse` is the list an evaluation already
answers, and `msort` is Python's own `sorted`.
"""

from petta import S, V, equation, rules, val

#: MeTTa's boolean ATOM, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list reads
#: as a Python flag, and this is an answer.
TRUE = val(value=True)

#: The knowledge, as the table it is: each animal and what holds of it, in the
#: original's own order.
FACTS = {
    S.garfield: (S.living, S.being, S.small),
    S.snoopy: (S.living, S.being),
    S.roomba: (S.being, S.small),
    S.cat42: (S.living, S.being, S.small),
}

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13518 to 12730, -788 (-5.8%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`, `collapse`
#: became the answer list and `msort` became Python's own `sorted`; the ten
#: facts, three relations and the whole filter stayed in the engine.
#: Against the example's 20721 the ratio is 0.6144 [measured 2026-08-22
#: min-of-3, `twin_coverage.py --measure`]. The old figure priced a
#: different program.
BUDGET = 12730


def twin(m):
    """Filter ten facts through two chained relations."""
    reflection = m.space("&petta")
    reflection += S["dispatch-policy"](S.small, S.NoMatchEnum, S.NoMatchFail)

    # (= (living garfield) True) ... (= (small cat42) True)
    # rung: each head fixes a SYMBOL, and a stacked clause's literal default is a
    #   bool, int, float or str (residue, P14.4)
    m.add(*(equation(rel(who)).to(TRUE) for who, rels in FACTS.items() for rel in rels))

    @rules
    def constrained(c, x, constraint):
        # (= (only $C $X) (let $constraint $C $X)): the body binds $constraint,
        # a variable it never reads, which is how it forces evaluation. An
        # assignment would mint the name and store `let*` instead.
        yield equation(S.only(c, x)).to(S.let(constraint, c, x))  # rung: let as a force

    m.add(*constrained)

    # The three names `animal`'s body reaches, bound so the Python side of the
    # twin runs them too, the way basics/xor binds `xor`.
    living, being, only = m.fn("living"), m.fn("being"), m.fn("only")

    @m.define
    def animal(x):
        # (= (animal $X) (only ((living $X) (being $X)) $X))
        return only((living(x), being(x)), x)

    @rules
    def cat(a, x):
        # (= (cat $A) (let $A (animal $X) (only (small $X) $X))): the body mints
        # $X, a hole for unification to fill, which a compiled body cannot
        # introduce (residue, P14.4).
        body = S.let(a, S.animal(x), S.only(S.small(x), x))  # rung: relational let
        yield equation(S.cat(a)).to(body)

    m.add(*cat)

    assert sorted(m.eval(S.cat(V.X)), key=str) == [S.cat42, S.garfield]
