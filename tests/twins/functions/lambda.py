"""The Python twin of examples/functions/lambda.metta: two kinds of lambda.

The first kind is FAKE, and works in any MeTTa: `(lambda $var $body)` is
ordinary data that `apply` takes apart, substituting through `let` and then
evaluating. The second kind is real, `|->`, a first-class compiled function
that can be mapped over a list, applied directly, passed through a `let`,
partially applied, and closed over a `let*` binding.

`myfunc` and `myfunc2` are ordinary Python functions; `myfunc2` applies its own
parameter, which is variable-head application.

The rest take the `@rules` shape of the definitional decorator, because each body
mints variables that are not parameters: `apply`'s head is a PATTERN that takes
`(lambda $var $body)` apart, and `applyL1` and `applyL2` build lambda data
holding `$x` and `$y`, which take their meaning from `apply`'s substitution
rather than from anything in scope. In the `@rules` shape those are simply the
generator's parameters, which is what the language calls them too.

Two operator spellings worth naming. `(or (== 1 $e) $acc)` is
`val(1).eq(V.e) | V.acc`: `|` builds `or` (Python's `or` keyword cannot be
overloaded, so the operator took the job) and `.eq` builds `==` (the `==`
operator itself is taken by Python's own equality). And `$lambda` is
`V["lambda"]`, since `lambda` is a Python keyword, which is exactly what the
subscript form is for.
"""

from petta import S, V, equation, rules, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list reads
#: as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 15085 to 17054, +1969 (+13.05%), and the per-step
#: reading places every inference of it. Installing `myfunc` costs 1814 more
#: decorated than as an equation atom, nearly all of it the one-time setup
#: the FIRST decorated definition in a process pays (2244 against the atom
#: door's 600 for one equation, where every later one costs 793 against 600);
#: `myfunc2`, the second, costs 133 more. The three `apply` equations now
#: enter through one `m.add` instead of three `m +=`, +22, the fixed cost of
#: the many-wire add. The four forms that install nothing cost 833, 1268,
#: 1667 and 1433 either way, unchanged to the inference. 1814 + 133 + 22 =
#: 1969, the whole of it. The lane's parity reads 0.70 of the original.
#: Prior: ADDED 2026-08-22 at 15085 by 7f15dc1's wave-3 baseline.
BUDGET = 17054


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    cons = m.fn("cons")

    # fake lambda (works in H-E MeTTa too):
    # (: apply (-> Atom %Undefined% %Undefined%))
    m += S[":"](S.apply, S["->"](S.Atom, S["%Undefined%"], S["%Undefined%"]))

    # rung: below the function shape: `apply`'s head takes the PATTERN (lambda $var
    #   $body) apart, and applyL1 and applyL2 build lambda data holding $x and $y,
    #   variables no parameter supplies. The declaration above follows from the same
    #   drop, since the annotation door needs a decorated definition (residue, P14.4)
    @rules
    def fake(var, body, arg, x, y):
        # (= (apply (lambda $var $body) $arg) (eval (let $var $arg $body)))
        yield equation(S.apply(S["lambda"](var, body), arg)).to(
            S.eval(S.let(var, arg, body))
        )
        # (= (applyL1) (apply (lambda $x (+ $x 1)) 2))
        yield equation(S.applyL1()).to(S.apply(S["lambda"](x, x + 1), 2))
        # (= (applyL2) (apply (lambda ($x $y) (+ $x $y)) (2 7)))
        yield equation(S.applyL2()).to(S.apply(S["lambda"]((x, y), x + y), (2, 7)))

    m.add(*fake)

    # !(test (applyL1) 3)
    yield m.eval(S.test(S.applyL1(), 3))
    # !(test (applyL2) 9)
    yield m.eval(S.test(S.applyL2(), 9))

    # Proper lambdas that act as first-class compiled functions:
    # !(test (maplist (|-> ($a) (+ 1 $a)) (1 2 3)) (2 3 4))
    yield m.eval(
        S.test(S.maplist(S["|->"]((V.a,), 1 + V.a), (1, 2, 3)), (2, 3, 4))
    )

    # !(test ((|-> ($acc $e) (or (== 1 $e) $acc)) False 1) True)
    yield m.eval(
        S.test(
            (S["|->"]((V.acc, V.e), val(1).eq(V.e) | V.acc), FALSE, 1),
            TRUE,
        )
    )

    @m.define
    def myfunc(a, b):
        # (= (myfunc $a $b) (cons $a $b))
        return cons(a, b)

    # !(test (let $f (myfunc 42) ((|-> ($x) ($f ($x 2 3))) 43)) (42 43 2 3))
    yield m.eval(
        S.test(
            S.let(
                V.f,
                S.myfunc(42),
                (S["|->"]((V.x,), (V.f, (V.x, 2, 3))), 43),
            ),
            (42, 43, 2, 3),
        )
    )

    # !(test (((|-> ($x $y) (42 $x $y)) 43) 44) (42 43 44))
    yield m.eval(
        S.test(
            ((S["|->"]((V.x, V.y), (42, V.x, V.y)), 43), 44),
            (42, 43, 44),
        )
    )

    @m.define
    def myfunc2(mylambda):
        # (= (myfunc2 $mylambda) ($mylambda 43 44))
        return mylambda(43, 44)

    # !(test (let* (($k 45) ($lambda (|-> ($x $y) (42 $x $y $k))))
    #              (myfunc2 $lambda))
    #        (42 43 44 45))
    yield m.eval(
        S.test(
            S["let*"](
                (
                    (V.k, 45),
                    (V["lambda"], S["|->"]((V.x, V.y), (42, V.x, V.y, V.k))),
                ),
                S.myfunc2(V["lambda"]),
            ),
            (42, 43, 44, 45),
        )
    )
