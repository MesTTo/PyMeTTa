"""The Python twin of examples/functions/functionhead2.metta: a relational constraint, chained.

`animal` keeps whatever is living AND a being; `cat` takes what `animal`
produces and keeps whatever is also small. `small` is put under a
`NoMatchFail` dispatch policy first, so asking `small` about something it has
no fact for FAILS the relation instead of answering the unreduced call, which
is what makes `cat` a filter rather than a producer of residual terms.

The ten facts are a TABLE, so they are written as one: a Python dict from each
animal to the relations that hold of it, and a comprehension turning each pair
into its equation. That preserves the original's own reading order (every fact
about garfield, then snoopy, then roomba, then cat42) and says the shape of the
knowledge once instead of ten times. They cannot be decorated functions: each
head fixes a SYMBOL (`(living garfield)`), a stacked clause fixes a head
position with a literal DEFAULT, and a literal is a bool, int, float or str,
never a symbol. The residue table records that against P14.4.

`animal` is an ordinary Python function whose constraint is a Python tuple:
`(living(x), being(x))` compiles to `((living $X) (being $X))`, one expression
of two calls.

`only` and `cat` take the `@rules` shape of the definitional decorator, because both
bodies mint a variable that is not a parameter. `only` binds the constraint's
result to `$constraint` and never reads it, which is how it forces evaluation;
`cat` unifies its own argument against what `animal` produces, and `$X` is the
hole that unification fills. A compiled body cannot introduce either: an
assignment binds a fresh name to a VALUE rather than leaving a hole, and it
would store a `let*` around a minted name instead of the original's `let`.
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
#: RE-PINNED 2026-08-22, 11639 to 13518, +1879 (+16.14%), all of it
#: definition installation and split in two. `animal` costs 2437 as an
#: equation atom and 4273 through `@m.define`, +1836, and it is the FIRST
#: decorated definition in this process so it carries the one-time setup as
#: well as its own compile (2244 against the atom door's 600 for one equation
#: the first time, 793 against 600 after). The ten facts now enter through
#: one `m.add` instead of ten `m +=`, 3664 to 3707, +43, the fixed cost of
#: the many-wire add. `only` costs 453 and `cat` 2194 either way, and both
#: runnable forms are unchanged, because both doors land the same thirteen
#: equations. The lane's parity reads 0.65 of the original. Prior: ADDED
#: 2026-08-22 at 11639 by 7f15dc1's wave-3 baseline.
BUDGET = 13518


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(add-atom &petta (dispatch-policy small NoMatchEnum NoMatchFail))
    yield m.eval(
        S["add-atom"](
            S["&petta"],
            S["dispatch-policy"](S.small, S.NoMatchEnum, S.NoMatchFail),
        )
    )

    # (= (living garfield) True) ... (= (small cat42) True)
    m.add(*(equation(rel(who)).to(TRUE) for who, rels in FACTS.items() for rel in rels))

    @rules
    def constrained(c, x, constraint):
        # (= (only $C $X) (let $constraint $C $X))
        yield equation(S.only(c, x)).to(S.let(constraint, c, x))

    m.add(*constrained)

    # The three names `animal`'s body reaches, bound so the Python side of the
    # twin runs them too, the way `basics/xor` binds `xor`.
    living, being, only = m.fn("living"), m.fn("being"), m.fn("only")

    @m.define
    def animal(x):
        # (= (animal $X) (only ((living $X) (being $X)) $X))
        return only((living(x), being(x)), x)

    @rules
    def cat(a, x):
        # (= (cat $A) (let $A (animal $X) (only (small $X) $X)))
        yield equation(S.cat(a)).to(S.let(a, S.animal(x), S.only(S.small(x), x)))

    m.add(*cat)

    # !(test (msort (collapse (cat $X))) (cat42 garfield))
    yield m.eval(
        S.test(S.msort(S.collapse(S.cat(V.X))), (S.cat42, S.garfield))
    )
