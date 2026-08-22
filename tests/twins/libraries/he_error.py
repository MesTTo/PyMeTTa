"""The Python twin of examples/libraries/he_error.metta.

Error atoms are ordinary answers, `catch` is for the host errors the language
has no atom for, and `if-error`/`return-on-error` are the railway combinators
over both.

`(+ 40 a)` and `(+ $left $right)` are built by Python's own `+`, because an
operand that is a symbol or a variable makes the operator a builder. `(+ 40 2)`
and `(/ 40 0)` are over ground numbers, where the same operators are arithmetic
and one of them raises ZeroDivisionError before a term could exist, so those two
name their heads instead.

The twins lane reports a named operator head as a dropped rung, which is a
false positive it cannot see past; the residue table records the refinement
against P14.1.
"""

from petta import S, V, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17863 to 17863, +0 (+0.00%), by the P14 twin-style
#: rewrite: no cost moved: this file states no equations of its own, so the
#: rewrite only changed how its terms are SPELLED and the atoms handed to the
#: engine are identical. Prior: ADDED 2026-08-22 at 17863 by the wave-3
#: libraries baseline, which recorded no cause.
BUDGET = 17863

def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`.
    """
    # !(import! &self (library lib_he))
    yield m.eval(S["import!"](S["&self"], S.library(S.lib_he)))

    # !(test (let $result (catch (+ 40 2))
    #        (if-error $result
    #            Error
    #            $result))
    #        42)
    yield m.eval(
        S.test(
            S.let(
                V.result,
                S.catch(S["+"](40, 2)),
                S["if-error"](V.result, S.Error, V.result),
            ),
            42,
        )
    )

    # An operand whose type RULES THE CALL OUT is an error atom already, so
    # if-error sees one with no catch in between: `a` here is declared a String
    # and the arrow says Number.
    # (: a String)
    m += S[":"](S.a, S.String)
    # !(test (if-error (+ 40 a) Error fine) Error)
    yield m.eval(S.test(S["if-error"](40 + S.a, S.Error, S.fine), S.Error))

    # An operand whose type merely does not DECIDE is not an error. The call is
    # left as written, which is what upstream's NoReduce does.
    # !(test (if-error (+ 40 undeclared-operand) Error fine) fine)
    yield m.eval(
        S.test(
            S["if-error"](40 + S["undeclared-operand"], S.Error, S.fine), S.fine
        )
    )

    # catch is for a HOST error, the kind the language has no atom for. Two
    # unbound arithmetic operands are one.
    # !(test (let $result (catch (+ $left $right))
    #             (if-error $result
    #                 Error
    #                 $result))
    #        Error)
    yield m.eval(
        S.test(
            S.let(
                V.result,
                S.catch(V.left + V.right),
                S["if-error"](V.result, S.Error, V.result),
            ),
            S.Error,
        )
    )

    # Integer division by zero already is Error data, so it needs no catch.
    # !(test (if-error (/ 40 0) Error fine) Error)
    yield m.eval(S.test(S["if-error"](S["/"](40, 0), S.Error, S.fine), S.Error))

    # !(test (if-error (Error 5 BadType) "Error!" "No error") "Error!")
    yield m.eval(
        S.test(
            S["if-error"](S.Error(5, S.BadType), val("Error!"), val("No error")),
            val("Error!"),
        )
    )

    # !(test (return-on-error (Error 5 BadType) 6) (Error 5 BadType))
    yield m.eval(
        S.test(
            S["return-on-error"](S.Error(5, S.BadType), 6), S.Error(5, S.BadType)
        )
    )

    # !(test (return-on-error 5 6) 6)
    yield m.eval(S.test(S["return-on-error"](5, 6), 6))
