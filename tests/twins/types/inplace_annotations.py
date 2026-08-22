"""The Python twin of examples/types/inplace_annotations.metta: types that prune.

`(: $x T)` matches anything of type T and binds `$x` to it, in a HEAD or in a
match query rather than only in a top-level declaration. It is not a new type
relation: it desugars to a plain variable plus exactly the acceptance the
engine already compiles for a declared parameter of type T. So Rex never
reaches `greet`'s body, a symbol with two declared types gives a branch each,
one type variable in two positions constrains them to agree, and a query
prunes rather than filtering afterwards.

Every equation here matches a structural head, `(= (greet (: $x Person))
...)`, so none of them compiles: a compiled head takes plain parameters or
literal defaults, and Python's own construct for a structural head is the
`match` statement, which the compiled subset has no lowering for yet. The
residue table records that against P14.4. `list-length`'s two clauses are one
definition, so `@rules` writes them as a group with its variables scoped to
its parameters; the single equations stay at the container door.

The colon expressions are ordinary terms, `S[":"](V.x, S.Person)`, which is
what makes the file's two gates demonstrable from Python at all: gate 1 is a
pattern that IS a colon expression and stays structural, gate 2 is a colon
whose value slot is not a variable and is data nothing looks inside.
"""

from petta import S, V, equation, rules

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: every head here matches a structural pattern, `(= (greet (: $x Person)) ...)`, and a
#: compiled head takes plain parameters or literal defaults. Python's own construct for a
#: structural head is the `match` statement, which the compiled subset has no lowering for.
#: `list-length`'s two clauses are one definition, so `@rules` writes them as a group.
RUNG = "container door and @rules: every head matches a structural pattern, which a compiled head has no spelling for"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 21908 to 21927, +19, by lifting the 2-clause equation set from
#: repeated `m += equation(...).to(...)` to `@rules` plus one `m.add(*group)`. The whole of the
#: increase is the multi-atom add path, not the decorator: `rules` builds its equations in
#: Python and spends nothing on the engine, and one `m.add` of n atoms costs 13 + 3n inferences
#: more than n separate `m +=` calls (measured over three fresh processes each: 673 against 692
#: at two atoms, 1042 against 1064 at three, 0.0000% spread). Prior: #: RE-PINNED 2026-08-22, 21315 to 21908, +593, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 21315 by 47554fc's control/types twin baseline.
BUDGET = 21927


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    of = S[":"]

    # !(add-atom &petta (dispatch-policy shape-of NoMatchEnum NoMatchFail))
    # answers (())
    yield m.eval(
        S["add-atom"](
            S["&petta"],
            S["dispatch-policy"](S["shape-of"], S.NoMatchEnum, S.NoMatchFail),
        )
    )

    # (: Ann Person)
    m += of(S.Ann, S.Person)
    # (: Ann Employee)
    m += of(S.Ann, S.Employee)
    # (: Bob Person)
    m += of(S.Bob, S.Person)
    # (: Rex Dog)
    m += of(S.Rex, S.Dog)

    # Restrict a head parameter. Rex never reaches the body.
    # (= (greet (: $x Person)) (hello $x))
    m += equation(S.greet(of(V.x, S.Person))).to(S.hello(V.x))
    # !(test (collapse (greet Ann)) ((hello Ann)))
    yield m.eval(
        S.test(
            S.collapse(S.greet(S.Ann)),
            (S.hello(S.Ann),),
        )
    )
    # !(test (collapse (greet Rex)) ())
    yield m.eval(S.test(S.collapse(S.greet(S.Rex)), ()))

    # Bind the type to a variable instead, and a symbol with two declared
    # types gives a branch each, because nondeterminism is native rather
    # than added.
    # (= (type-of (: $x $t)) $t)
    m += equation(S["type-of"](of(V.x, V.t))).to(V.t)
    # !(test (collapse (type-of Ann)) (Person Employee))
    yield m.eval(
        S.test(
            S.collapse(S["type-of"](S.Ann)),
            (S.Person, S.Employee),
        )
    )
    # !(test (collapse (type-of Rex)) (Dog))
    yield m.eval(S.test(S.collapse(S["type-of"](S.Rex)), (S.Dog,)))

    # One type variable in two positions constrains them to agree.
    # (= (same-kind (: $x $t) (: $y $t)) ($x $y))
    m += equation(S["same-kind"](of(V.x, V.t), of(V.y, V.t))).to((V.x, V.y))
    # !(test (collapse (same-kind Ann Bob)) ((Ann Bob)))
    yield m.eval(
        S.test(
            S.collapse(S["same-kind"](S.Ann, S.Bob)),
            ((S.Ann, S.Bob),),
        )
    )
    # !(test (collapse (same-kind Ann Rex)) ())
    yield m.eval(S.test(S.collapse(S["same-kind"](S.Ann, S.Rex)), ()))

    # A METATYPE restriction works for the same reason and needs nothing
    # extra: has_type fails on a symbol nobody declared, so the acceptance
    # falls through to get-metatype.
    # (= (fmap $f (: $c Symbol)) ($f $c))
    m += equation(S.fmap(V.f, of(V.c, S.Symbol))).to((V.f, V.c))
    # !(test (collapse (fmap g sym)) ((g sym)))
    yield m.eval(
        S.test(
            S.collapse(S.fmap(S.g, S.sym)),
            ((S.g, S.sym),),
        )
    )
    # !(test (collapse (fmap g 42)) ())
    yield m.eval(S.test(S.collapse(S.fmap(S.g, 42)), ()))

    # And in a match query, which is where it prunes the search rather than
    # the call. Zeus is a God, so the restricted query does not reach him.
    # (: Plato Human)
    m += of(S.Plato, S.Human)
    # (: Socrates Human)
    m += of(S.Socrates, S.Human)
    # (: Zeus God)
    m += of(S.Zeus, S.God)
    # !(add-atom &self (knows Plato Socrates)) answers (())
    yield m.eval(S["add-atom"](S["&self"], S.knows(S.Plato, S.Socrates)))
    # !(add-atom &self (knows Plato Zeus)) answers (())
    yield m.eval(S["add-atom"](S["&self"], S.knows(S.Plato, S.Zeus)))
    # !(test (collapse (match &self (knows (: $x Human) (: $y Human)) ($x $y)))
    #        ((Plato Socrates)))
    yield m.eval(
        S.test(
            S.collapse(
                S.match(
                    S["&self"],
                    S.knows(of(V.x, S.Human), of(V.y, S.Human)),
                    (V.x, V.y),
                )
            ),
            ((S.Plato, S.Socrates),),
        )
    )
    # !(test (collapse (match &self (knows (: $x $t) (: $y $t)) ($x $y $t)))
    #        ((Plato Socrates Human)))
    yield m.eval(
        S.test(
            S.collapse(
                S.match(
                    S["&self"],
                    S.knows(of(V.x, V.t), of(V.y, V.t)),
                    (V.x, V.y, V.t),
                )
            ),
            ((S.Plato, S.Socrates, S.Human),),
        )
    )

    # GATE 1: the whole pattern is a colon expression, so this retrieves the
    # stored declaration rather than annotating anything.
    # !(test (collapse (match &self (: Zeus $t) $t)) (God))
    yield m.eval(
        S.test(
            S.collapse(S.match(S["&self"], of(S.Zeus, V.t), V.t)),
            (S.God,),
        )
    )

    # `::` means nothing special to the engine, which is the point of not
    # having taken it. Here is the tutorial's own list program, verbatim.
    cons = S["::"]

    @rules
    def list_length(x, xs):
        # (= (list-length ()) 0)
        yield equation(S["list-length"](())).to(0)
        # (= (list-length (:: $x $xs)) (+ 1 (list-length $xs)))
        yield equation(S["list-length"](cons(x, xs))).to(1 + S["list-length"](xs))

    m.add(*list_length)
    # !(test (list-length (:: A (:: B (:: C ())))) 3)
    yield m.eval(
        S.test(
            S["list-length"](cons(S.A, cons(S.B, cons(S.C, ())))),
            3,
        )
    )

    # GATE 2: the annotation position must hold a VARIABLE, or the form
    # stays structural and nothing looks inside it.
    # (= (shape-of (: a $rest)) $rest)
    m += equation(S["shape-of"](of(S.a, V.rest))).to(V.rest)
    # !(test (collapse (shape-of (: a tail))) (tail))
    yield m.eval(
        S.test(
            S.collapse(S["shape-of"](of(S.a, S.tail))),
            (S.tail,),
        )
    )
    # !(test (collapse (shape-of (: z tail))) ())
    yield m.eval(
        S.test(
            S.collapse(S["shape-of"](of(S.z, S.tail))),
            (),
        )
    )
