"""Purpose: examples/types/inplace_annotations.metta in Python: a type where it prunes.

`(: $x Person)` in a head or a match pattern matches anything of type Person
and binds `$x` to it. It is not a new relation: it desugars to a plain variable
plus exactly the acceptance the engine already compiles for a declared
parameter, so anyone who knows one knows the other. Rex never reaches `greet`'s
body, `type-of` answers once per declared type, one type variable in two
positions makes them agree, and a METATYPE restriction works for the same
reason with nothing added.

Every clause here selects on a STRUCTURE in its head, so all of them are
written as the equations they are: a compiled parameter list carries plain
names and literal defaults, and `typed(V.x, S.Person)` is neither. A declared
parameter type, `def greet(x: Person)`, is the same acceptance said the other
way round, but it cannot BIND the type to a variable, which is what the three
clauses after `greet` do; the missing compiled head pattern is friction against
P14.4.

A lone equation goes through the write door as the atom it is; the two clauses
of `list-length` are one relation, so they are one `@m.rules` bundle, which is
the same write door taking a whole bundle and freshening its variables from the
parameter list.

The two gates that make the position rule work are claims too. A pattern that
IS a colon expression stays structural, so the knowledge base still answers
with the declarations somebody wrote; and only `(: $variable expected)` is an
annotation, so `(: a tail)` and the tutorial's `::` list stay ordinary data.
"""

import metta
from metta import UNIT, S, V, equation, typed
from metta.vocabularies import NoMatchEnum

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here
#: [assumed: 1 is a placeholder rather than a measurement; commit=e4c861a8c9e8e42b9e5ecb90d9ebf92a946e0163].
#: PRICED 2026-08-25 by the corpus pricing pass: tools/twin_coverage.py --measure min-of-3 on p14-integration at the store-wave merge, pinned exactly under the suite's two-sided +-4 deterministic allowance.
#: RE-PINNED 2026-08-25, 18846 to 18979, at the flat-door
#: typed-dispatch gate and the library import door landing
#: together: every flat call prices one declaration read through
#: type_declaration_in/3, a declared head's flat call routes
#: through the same call-site typed dispatch the engine's own
#: form runs (petta_py_typed_dispatch_applies/2, the P14.9
#: residue retirement), and an import-bearing twin now spells
#: its import as `m += lib.x` on the write door [measured
#: 2026-08-25 through tools/twin_coverage.py --measure min-of-3
#: on the tree carrying both].
#: RE-PINNED 2026-08-25, 18979 to 18930, on the QLF-boot final
#: tree: the engine now boots through engine/qlf_boot.pl, and any
#: boot-content change moves twin counts a few tens through SWI's
#: clause-indexing shape (qlf_boot.pl's header carries the A/B),
#: so the corpus re-pins once on the exact shipping tree
#: [measured 2026-08-25 through tools/twin_coverage.py --measure
#: min-of-3 on the final tree].
#: RE-PINNED 2026-08-25, 18930 to 18944, on the release tree:
#: the typed-dispatch question moved engine-side
#: (metta_typed_dispatch_applies/2, one extra frame per direct
#: call), the conformance kit gained the family, source and
#: round-trip laws, extensions gained the spaces([...]) readying
#: moment, and any boot-content change also moves counts a few
#: tens through SWI's clause-indexing shape (qlf_boot.pl's header
#: carries the A/B), so the corpus re-pins once on the exact
#: shipping tree [measured 2026-08-25 through
#: tools/twin_coverage.py --measure min-of-3 after a canonical
#: single-boot QLF regeneration].
BUDGET = 18944

#: The tutorial's own cons constructor, which means nothing to the engine.
#: `::` is not a Python identifier, so the name takes rung 5's bracket.
CONS = S["::"]


def twin(m):
    """Declare types, then prune with them in heads and in queries."""
    # Reaching either relation's unmatched boundary must FAIL the search rather
    # than answering the P3 residual-call dispatch value.
    # !(add-atom &petta (dispatch-policy shape-of NoMatchEnum NoMatchFail))
    reflection = metta.reflection
    reflection += S.dispatch_policy(
        S.shape_of, S.NoMatchEnum, S[NoMatchEnum.NoMatchFail]
    )

    # (: Ann Person) (: Ann Employee) (: Bob Person) (: Rex Dog)
    m += typed(S.Ann, S.Person)
    m += typed(S.Ann, S.Employee)
    m += typed(S.Bob, S.Person)
    m += typed(S.Rex, S.Dog)

    # Restrict a head parameter. Rex never reaches the body.
    # (= (greet (: $x Person)) (hello $x))
    m += equation(S.greet(typed(V.x, S.Person))).to(S.hello(V.x))
    # !(test (collapse (greet Ann)) ((hello Ann)))
    assert m.fn.greet(S.Ann) == [S.hello(S.Ann)]
    # !(test (collapse (greet Rex)) ())
    assert m.fn.greet(S.Rex) == []

    # Bind the type to a variable instead, and a symbol with two declared
    # types gives a branch each, because nondeterminism is native.
    # (= (type-of (: $x $t)) $t)
    m += equation(S.type_of(typed(V.x, V.t))).to(V.t)
    # !(test (collapse (type-of Ann)) (Person Employee))
    assert m.fn.type_of(S.Ann) == [S.Person, S.Employee]
    # !(test (collapse (type-of Rex)) (Dog))
    assert m.fn.type_of(S.Rex) == [S.Dog]

    # One type variable in two positions constrains them to agree.
    # (= (same-kind (: $x $t) (: $y $t)) ($x $y))
    m += equation(S.same_kind(typed(V.x, V.t), typed(V.y, V.t))).to((V.x, V.y))
    # !(test (collapse (same-kind Ann Bob)) ((Ann Bob)))
    assert m.fn.same_kind(S.Ann, S.Bob) == [S.Ann(S.Bob)]
    # !(test (collapse (same-kind Ann Rex)) ())
    assert m.fn.same_kind(S.Ann, S.Rex) == []

    # A METATYPE restriction works for the same reason and needs nothing
    # extra: the acceptance falls through to the metatype when nobody
    # declared the symbol.
    # (= (fmap $f (: $c Symbol)) ($f $c))
    m += equation(S.fmap(V.f, typed(V.c, S.Symbol))).to((V.f, V.c))
    # !(test (collapse (fmap g sym)) ((g sym)))
    assert m.fn.fmap(S.g, S.sym) == [S.g(S.sym)]
    # !(test (collapse (fmap g 42)) ())
    assert m.fn.fmap(S.g, 42) == []

    # And in a match query, which is where it prunes the search rather than
    # the call. Zeus is a God, so the restricted query does not reach him.
    # (: Plato Human) (: Socrates Human) (: Zeus God)
    # !(add-atom &self (knows Plato Socrates))
    # !(add-atom &self (knows Plato Zeus))
    m += typed(S.Plato, S.Human)
    m += typed(S.Socrates, S.Human)
    m += typed(S.Zeus, S.God)
    m += S.knows(S.Plato, S.Socrates)
    m += S.knows(S.Plato, S.Zeus)

    # !(test (collapse (match &self (knows (: $x Human) (: $y Human)) ($x $y)))
    #        ((Plato Socrates)))
    humans = m[S.knows(typed(V.x, S.Human), typed(V.y, S.Human))]
    assert [(row.x, row.y) for row in humans] == [(S.Plato, S.Socrates)]
    # !(test (collapse (match &self (knows (: $x $t) (: $y $t)) ($x $y $t)))
    #        ((Plato Socrates Human)))
    agreeing = m[S.knows(typed(V.x, V.t), typed(V.y, V.t))]
    assert [(row.x, row.y, row.t) for row in agreeing] == [(S.Plato, S.Socrates, S.Human)]

    # GATE 1: the whole pattern is a colon expression, so this retrieves the
    # stored declaration rather than annotating anything.
    # !(test (collapse (match &self (: Zeus $t) $t)) (God))
    assert m[typed(S.Zeus, V.t)].t == [S.God]

    # `::` means nothing special to the engine, which is the point of not
    # having taken it. Here is the tutorial's own list program, verbatim: two
    # coexisting clauses of one relation, so they are one `@m.rules` bundle
    # and its parameters are their variables.
    @m.rules
    def length(x, rest):
        """(= (list-length ()) 0) and (= (list-length (:: $x $xs)) ...)."""
        yield equation(S.list_length(UNIT)).to(0)
        yield equation(S.list_length(CONS(x, rest))).to(1 + S.list_length(rest))

    # !(test (list-length (:: A (:: B (:: C ())))) 3)
    assert m.fn.list_length(CONS(S.A, CONS(S.B, CONS(S.C, UNIT)))) == [3]

    # GATE 2: the annotation position must hold a VARIABLE, or the form stays
    # structural and nothing looks inside it.
    # (= (shape-of (: a $rest)) $rest)
    m += equation(S.shape_of(typed(S.a, V.rest))).to(V.rest)
    # !(test (collapse (shape-of (: a tail))) (tail))
    assert m.fn.shape_of(typed(S.a, S.tail)) == [S.tail]
    # !(test (collapse (shape-of (: z tail))) ())
    assert m.fn.shape_of(typed(S.z, S.tail)) == []
