"""The Python twin of examples/types/types.metta: what get-type answers.

Concrete types, then function types, then nondeterministic ones. A symbol with
two declarations has two types; a symbol with none has `%Undefined%`; an
expression has the expression of its parts' types; and a grounded value has the
type its own kind carries.

Every declaration is an atom, because these are claims about SYMBOLS and there
is no Python signature to carry one: `(: a A)` says nothing about a function.
The two equations are written at the container door as well. `mid`'s body is
`(let (a b) $x $x)`, a `let` whose pattern is an expression, and `testf`'s head
fixes a SYMBOL, `(= (testf at) t)`, where a compiled head takes plain
parameters or literal defaults; Python's construct for a structural head is
the `match` statement, which the compiled subset has no lowering for yet
(P14.4).
"""

from petta import S, V, equation, val

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: two drops. The `(: ...)` claims are about bare SYMBOLS with no `typed(x, T)` builder to
#: write them. And `mid`'s body is a `let` whose pattern is an expression while `testf`'s head fixes
#: a SYMBOL, neither of which a compiled body or head spells.
RUNG = "declarations as atoms plus a container door for mid's let pattern and testf's symbol head"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 10603 to 10954, +351, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 10603 by 47554fc's control/types twin baseline.
BUDGET = 10954


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    kind = S["get-type"]
    undefined = S["%Undefined%"]

    # Concrete types.
    # (: a A)
    m += S[":"](S.a, S.A)
    # (: b B)
    m += S[":"](S.b, S.B)
    # (: A Type)
    m += S[":"](S.A, S.Type)
    # (: x Letter)
    m += S[":"](S.x, S.Letter)
    # (: x Buchstabe)
    m += S[":"](S.x, S.Buchstabe)

    # !(test (get-type $a) $z)
    yield m.eval(S.test(kind(V.a), V.z))
    # !(test (get-type a) A)
    yield m.eval(S.test(kind(S.a), S.A))
    # !(test (get-type b) B)
    yield m.eval(S.test(kind(S.b), S.B))
    # !(test (get-type c) %Undefined%)
    yield m.eval(S.test(kind(S.c), undefined))
    # !(test (get-type A) Type)
    yield m.eval(S.test(kind(S.A), S.Type))
    # !(test (get-type B) %Undefined%)
    yield m.eval(S.test(kind(S.B), undefined))
    # !(test (get-type (a b)) (A B))
    yield m.eval(S.test(kind((S.a, S.b)), (S.A, S.B)))
    # !(test (get-type 42) Number)
    yield m.eval(S.test(kind(42), S.Number))
    # !(test (get-type "42") String)
    yield m.eval(S.test(kind(val("42")), S.String))
    # !(test (collapse (get-type x)) (Letter Buchstabe))
    yield m.eval(
        S.test(
            S.collapse(kind(S.x)),
            (S.Letter, S.Buchstabe),
        )
    )

    # Function types.
    # (: mid (-> $a $a))
    m += S[":"](S.mid, S["->"](V.a, V.a))
    # (= (mid $x) (let (a b) $x $x))
    m += equation(S.mid(V.x)).to(S.let((S.a, S.b), V.x, V.x))

    # !(test (mid ($a b)) (a b))
    yield m.eval(S.test(S.mid((V.a, S.b)), (S.a, S.b)))

    # (: testx (-> $a $b $a))
    m += S[":"](S.testx, S["->"](V.a, V.b, V.a))
    # !(test (get-type (testx 1 "f")) Number)
    yield m.eval(S.test(kind(S.testx(1, val("f"))), S.Number))

    # Non-deterministic types.
    # (: at A)
    m += S[":"](S.at, S.A)
    # (: at T)
    m += S[":"](S.at, S.T)
    # (: t T)
    m += S[":"](S.t, S.T)
    # (: testf (-> $a $a))
    m += S[":"](S.testf, S["->"](V.a, V.a))
    # (= (testf at) t)
    m += equation(S.testf(S.at)).to(S.t)

    # !(test (testf at) t)
    yield m.eval(S.test(S.testf(S.at), S.t))
