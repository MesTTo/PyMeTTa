"""The Python twin of examples/functions/functionhead3.metta: one `let` per constrained argument.

`in` keeps a value only when it is a member of a list, and `myplus` chains one
`let` per argument, so the constraint runs in BOTH directions: give it two
numbers and it filters, give it variables and it enumerates what is reachable.
The last form runs the whole relation backwards through a guard.

Both definitions take the `@rules` shape of the definitional decorator, and
here neither could take the function shape even in principle.

`in` is a Python KEYWORD, so no Python function can carry that name, and no
Python body can call it either. Its body also names `is-member`, and a compiled
body resolves a free name EXACTLY, so a hyphenated engine function is
unreachable from one. `myplus` calls `in`, so the same wall stops it. In the
equational shape both are ordinary atoms: `S["in"]` and `S["is-member"]` are
the subscript form, which is exactly what the subscript is for, a name Python's
own grammar will not take as an attribute. The residue table records the
keyword gap against P14.4, where the hyphenated-name gap already sits.

The last form's guard is `(> (myplus $x 2) 3)`, and there Python's own
operator builds the term: `S.myplus(V.x, 2) > 3`.
"""

from petta import S, V, equation, rules, val

#: MeTTa's boolean ATOM, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list reads
#: as a Python flag, and this is an answer.
TRUE = val(value=True)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 9283 to 9302, +19 (+0.20%), and the whole of it is
#: the BATCH door rather than the rewrite: `@rules` builds the identical two
#: equation atoms, and `m.add(a, b)` costs 19 more than `m += a` twice, the
#: fixed cost of the many-wire call. The five later runnable forms cost 783,
#: 775, 928, 1109 and 1294 either way, unchanged to the inference. The lane's
#: parity reads 0.60 of the original. Prior: ADDED 2026-08-22 at 9283 by
#: 7f15dc1's wave-3 baseline.
BUDGET = 9302


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """

    # rung: below the function shape: `in` is a Python KEYWORD, so no function can
    #   carry that name and no body can call it, and `is-member` is hyphenated,
    #   which a body cannot name either (residue, P14.4)
    @rules
    def constrained(a, b, x, y, items):
        # (= (in $x $L) (let True (is-member $x $L) $x))
        yield equation(S["in"](x, items)).to(S.let(TRUE, S["is-member"](x, items), x))
        # (= (myplus $A $B)
        #    (let $A (in $X (1 2 3))
        #      (let $B (in $Y (2 3))
        #        (in (+ $X $Y) (3 4 5)))))
        yield equation(S.myplus(a, b)).to(
            S.let(
                a,
                S["in"](x, (1, 2, 3)),
                S.let(
                    b,
                    S["in"](y, (2, 3)),
                    S["in"](x + y, (3, 4, 5)),
                ),
            )
        )

    m.add(*constrained)

    # fine:
    # !(test (collapse (myplus 1 3)) (4))
    yield m.eval(S.test(S.collapse(S.myplus(1, 3)), (4,)))
    # output out of range:
    # !(test (collapse (myplus 3 3)) ())
    yield m.eval(S.test(S.collapse(S.myplus(3, 3)), ()))
    # input out of range:
    # !(test (collapse (myplus 3 4)) ())
    yield m.eval(S.test(S.collapse(S.myplus(3, 4)), ()))
    # what can be reached when adding $X to 3:
    # !(test (collapse (myplus $x 3)) (4 5))
    yield m.eval(S.test(S.collapse(S.myplus(V.x, 3)), (4, 5)))
    # what can be reached when adding $X to $Y:
    # !(test (collapse (myplus $x $y)) (3 4 4 5 5))
    yield m.eval(S.test(S.collapse(S.myplus(V.x, V.y)), (3, 4, 4, 5, 5)))
    # With which $x added to 2 can we reach values above 3 with myplus?
    # !(test (collapse (let True (> (myplus $x 2) 3) $x)) (2 3))
    yield m.eval(
        S.test(S.collapse(S.let(TRUE, S.myplus(V.x, 2) > 3, V.x)), (2, 3))
    )
