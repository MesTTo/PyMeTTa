"""Purpose: examples/functions/lambda.metta in Python: two kinds of lambda.

The first kind is FAKE, and works in any MeTTa: `(lambda $var $body)` is
ordinary data that `apply` takes apart, substituting through `let` and then
evaluating. The second kind is real, `|->`, a first-class compiled function
that can be mapped over a list, applied directly, passed through a binding,
partially applied, and closed over a preceding binding.

Python's own `lambda` IS the second kind. Inside a compiled body it lowers
straight to `|->`, so `lambda a: 1 + a` stores `(|-> ($a) (+ 1 $a))`, and a
`lambda` that reads a name bound above it closes over that name exactly as the
original's `let*` does. Three of the seven claims are written that way.

What a compiled body will not do is apply a lambda WHERE IT STANDS: `(lambda
...)(arg)` is refused, "a compiled body calls a plain name". So the two forms
that apply an anonymous lambda immediately are built at the term door, where
`|->` is an ordinary head, and the two claims that only bind one are compiled.

`myfunc` and `myfunc2` are ordinary Python functions; `myfunc2` applies its
own parameter, which is variable-head application.

The `apply` family takes the `@rules` shape of the definitional decorator,
because each body mints variables that are not parameters: `apply`'s head is a
PATTERN that takes `(lambda $var $body)` apart, and `applyL1` and `applyL2`
build lambda DATA holding `$x` and `$y`, which take their meaning from
`apply`'s substitution rather than from anything in scope.

Two operator spellings worth naming. `(or (== 1 $e) $acc)` is
`val(1).eq(V.e) | V.acc`: `|` builds `or`, because Python's `or` keyword
cannot be overloaded, and `.eq` builds `==`, because the `==` operator is
taken by Python's own structural equality. And `$lambda` is `V["lambda"]`,
since `lambda` is a Python keyword, which is exactly what the subscript is
for.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, Expression, S, V, equation, rules, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 17054 to 17056, +2 (+0.0%), by the twin contract
#: change: seven `test` wrappers left the engine for `assert`, and three of
#: the seven claims ENTERED the compiled subset instead of the term door:
#: Python's own `lambda` lowers to `|->`, so `maplist`, the
#: partial-application binding and the closing lambda are now decorated
#: definitions. The three registrations cost almost exactly what the seven
#: wrappers saved, which is why this is the one twin in the two folders
#: that did not get cheaper. Against the example's 24199 the ratio is
#: 0.7048 [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The
#: old figure priced a different program.
BUDGET = 17056


def twin(m):
    """Apply a lambda that is data, then five that are functions."""
    cons, maplist = m.fn("cons"), m.fn("maplist")

    # (: apply (-> Atom %Undefined% %Undefined%))
    # rung: below the ANNOTATION door: the annotation door needs a decorated
    #   definition, and `apply` cannot be one (residue, P14.4)
    m += S[":"](S.apply, S["->"](S.Atom, S["%Undefined%"], S["%Undefined%"]))

    # rung: `apply`'s head takes the PATTERN (lambda $var $body) apart, and
    #   applyL1 and applyL2 build lambda data holding $x and $y, variables no
    #   parameter supplies (residue, P14.4)
    @rules
    def fake(var, body, arg, x, y):
        # (= (apply (lambda $var $body) $arg) (eval (let $var $arg $body)))
        yield equation(S.apply(S["lambda"](var, body), arg)).to(
            S.eval(S.let(var, arg, body))  # rung: let as substitution
        )
        # (= (applyL1) (apply (lambda $x (+ $x 1)) 2))
        yield equation(S.applyL1()).to(S.apply(S["lambda"](x, x + 1), 2))
        # (= (applyL2) (apply (lambda ($x $y) (+ $x $y)) (2 7)))
        yield equation(S.applyL2()).to(S.apply(S["lambda"]((x, y), x + y), (2, 7)))

    m.add(*fake)

    assert m.eval(S.applyL1()) == [3]
    assert m.eval(S.applyL2()) == [9]

    # A real lambda, mapped over a list: Python's own lambda IS `|->`.
    @m.define
    def increment_all(items):
        # (= (increment-all $items) (maplist (|-> ($a) (+ 1 $a)) $items))
        return maplist(lambda a: 1 + a, items)

    assert increment_all((1, 2, 3)) == [Expression((2, 3, 4))]

    # Applied where it stands, which a compiled body will not do.
    folding = S["|->"]((V.acc, V.e), val(1).eq(V.e) | V.acc)
    assert m.eval((folding, FALSE, 1)) == [True]

    @m.define
    def myfunc(a, b):
        # (= (myfunc $a $b) (cons $a $b))
        return cons(a, b)

    # A lambda over a PARTIAL application bound above it.
    @m.define
    def through_partial():
        # (let $f (myfunc 42) ((|-> ($x) ($f ($x 2 3))) 43))
        f = myfunc(42)
        g = lambda x: f((x, 2, 3))  # noqa: E731  -- the binding IS the point: it stores (|-> ($x) ...)
        return g(43)

    assert through_partial() == [Expression((42, 43, 2, 3))]

    # Partially applied: one argument now, the other later.
    assert m.eval(((S["|->"]((V.x, V.y), (42, V.x, V.y)), 43), 44)) == [Expression((42, 43, 44))]

    @m.define
    def myfunc2(mylambda):
        # (= (myfunc2 $mylambda) ($mylambda 43 44))
        return mylambda(43, 44)

    # A lambda CLOSING over a binding above it, which is the original's let*.
    @m.define
    def closed():
        # (let* (($k 45) ($lambda (|-> ($x $y) (42 $x $y $k)))) (myfunc2 $lambda))
        k = 45
        return myfunc2(lambda x, y: (42, x, y, k))

    assert closed() == [Expression((42, 43, 44, 45))]
