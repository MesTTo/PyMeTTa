"""The Python twin of examples/data/atomops.metta: the structural operations.

Every form is one call over data, so the whole twin is the term door: a symbol
calls to build, and a plain Python tuple is the expression it is called on.
`(1 2 3)` reads `(1, 2, 3)` and `()` reads `()`.

The hyphenated names are subscripted because `cons-atom` is not a Python
identifier; `S.cons_atom` would name a different symbol, so the subscript is
the only spelling and not a drop from a shorter one.

The second half is about REFUSAL. Until 2026-08-19 a structural operation
handed an unbound variable unified it with a fresh cell and answered from it;
now it refuses, and the forms below read that refusal through
`(if-error (catch ...) refused answered)`. The refusal is narrow: a bound
argument is untouched, and `index-atom`'s second argument stays relational, so
an unbound index still enumerates every position.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: The example's own phrasing of what a structural operation says when it is
#: handed something that is not an expression.
NOT_AN_EXPRESSION = val("Atom is not an ExpressionAtom")

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17624 to 17624, +0, by the wave-4 idiom rewrite: the
#: forms are the same terms built at the same door, so the rewrite is a
#: SPELLING change and the counter says so.
BUDGET = 17624


def refuses(call):
    """`(test (if-error (catch call) refused answered) refused)`: the shape the
    refusal half of this example takes, named once so each case reads as the
    call it makes.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return S.test(
        S["if-error"](S.catch(call), S.refused, S.answered), S.refused
    )


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(test (cons-atom 0 (1 2 3)) (0 1 2 3))
    yield m.eval(S.test(S["cons-atom"](0, (1, 2, 3)), (0, 1, 2, 3)))
    # !(test (car-atom (1 2 3)) 1)
    yield m.eval(S.test(S["car-atom"]((1, 2, 3)), 1))
    # !(test (cdr-atom (1 2 3)) (2 3))
    yield m.eval(S.test(S["cdr-atom"]((1, 2, 3)), (2, 3)))
    # !(test (index-atom (1 2 3) 1) 2)
    yield m.eval(S.test(S["index-atom"]((1, 2, 3), 1), 2))

    # !(test (id 5) 5)
    yield m.eval(S.test(S.id(5), 5))

    # !(test (=alpha (Father $X) (Father $Y)) True)
    yield m.eval(S.test(S["=alpha"](S.Father(V.X), S.Father(V.Y)), TRUE))
    # !(test (=alpha (Father $X) (Son $X)) False)
    yield m.eval(S.test(S["=alpha"](S.Father(V.X), S.Son(V.X)), FALSE))

    # !(test (first-from-pair (A B)) A)
    yield m.eval(S.test(S["first-from-pair"]((S.A, S.B)), S.A))
    # !(test (second-from-pair (A B)) B)
    yield m.eval(S.test(S["second-from-pair"]((S.A, S.B)), S.B))

    # An index past the end, and one that is not a number, have no answer.
    # !(test (index-atom (1 2 3) 5) ())
    yield m.eval(S.test(S["index-atom"]((1, 2, 3), 5), ()))
    # !(test (index-atom (1 2 3) a) ())
    yield m.eval(S.test(S["index-atom"]((1, 2, 3), S.a), ()))

    # A non-expression has no size, order or unique children.
    # !(test (size-atom 5) ())
    yield m.eval(S.test(S["size-atom"](5), ()))
    # !(test (sort-atom 5) ())
    yield m.eval(S.test(S["sort-atom"](5), ()))
    # !(test (unique-atom 5) ())
    yield m.eval(S.test(S["unique-atom"](5), ()))
    # !(test (alpha-unique-atom 5) ())
    yield m.eval(S.test(S["alpha-unique-atom"](5), ()))

    # min and max say so with an error atom instead, which is an ordinary
    # answer built the same way as any other.
    # !(test (min-atom 5) (Error (min-atom 5) "Atom is not an ExpressionAtom"))
    yield m.eval(
        S.test(S["min-atom"](5), S.Error(S["min-atom"](5), NOT_AN_EXPRESSION))
    )
    # !(test (max-atom 5) (Error (max-atom 5) "Atom is not an ExpressionAtom"))
    yield m.eval(
        S.test(S["max-atom"](5), S.Error(S["max-atom"](5), NOT_AN_EXPRESSION))
    )

    # !(test (intersection-atom 5 (a)) ())
    yield m.eval(S.test(S["intersection-atom"](5, (S.a,)), ()))

    # An UNBOUND VARIABLE is a program error, not a pattern to solve for.
    # !(test (if-error (catch (car-atom $unbound)) refused answered) refused)
    yield m.eval(refuses(S["car-atom"](V.unbound)))
    # !(test (if-error (catch (size-atom $unbound)) refused answered) refused)
    yield m.eval(refuses(S["size-atom"](V.unbound)))
    # !(test (if-error (catch (sort-atom $unbound)) refused answered) refused)
    yield m.eval(refuses(S["sort-atom"](V.unbound)))
    # !(test (if-error (catch (index-atom $unbound 0)) refused answered) refused)
    yield m.eval(refuses(S["index-atom"](V.unbound, 0)))
    # !(test (if-error (catch (subtraction-atom $unbound (a b))) refused answered)
    #        refused)
    yield m.eval(refuses(S["subtraction-atom"](V.unbound, (S.a, S.b))))

    # A bound argument is untouched, which is the half that makes the refusal
    # worth anything.
    # !(test (if-error (catch (car-atom (1 2))) refused answered) answered)
    yield m.eval(
        S.test(
            S["if-error"](S.catch(S["car-atom"]((1, 2))), S.refused, S.answered),
            S.answered,
        )
    )
    # !(test (car-atom (1 2)) 1)
    yield m.eval(S.test(S["car-atom"]((1, 2)), 1))

    # index-atom's SECOND argument is relational by design.
    # !(test (collapse (index-atom (a b c) $i)) (a b c))
    yield m.eval(
        S.test(
            S.collapse(S["index-atom"]((S.a, S.b, S.c), V.i)), (S.a, S.b, S.c)
        )
    )
