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

`apply` takes the `@m.rules` shape of the definitional decorator, because its
HEAD is a pattern that takes `(lambda $var $body)` apart, which no parameter
list spells. `applyL1` and `applyL2` are ordinary decorated functions whose
bodies build lambda DATA holding `$x` and `$y`: those variables take their
meaning from `apply`'s substitution rather than from anything in scope, and
`V.x` is how a compiled body mints one.

Two operator spellings worth naming, both in the fold that is applied where
it stands. `(or (== 1 $e) $acc)` is `G(1).eq(V.e) | V.acc`: `|` builds `or`,
because Python's `or` keyword cannot be overloaded, and `.eq` builds `==`,
because the `==` operator is taken by Python's own structural equality.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, Expression, G, S, V, equation, fn

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Apply a lambda that is data, then five that are functions."""
    # (: apply (-> Atom %Undefined% %Undefined%))
    # rung: below the ANNOTATION door: the annotation door needs a decorated
    #   function, and `apply`'s head is a pattern (residue, P14.4)
    m += S[":"](S.apply, S["->"](S.Atom, S["%Undefined%"], S["%Undefined%"]))

    @m.rules
    def fake(var, body, arg):
        # (= (apply (lambda $var $body) $arg) (eval (let $var $arg $body)))
        yield equation(S.apply(S["lambda"](var, body), arg)).to(
            S.eval(S.let(var, arg, body))  # rung: let as substitution
        )

    # The MeTTa names are camel-cased and Python's are not, so `name=` carries
    # the example's own spelling and the Python side stays PEP 8.
    @m.define(name="applyL1")
    def apply_l1():
        # (= (applyL1) (apply (lambda $x (+ $x 1)) 2))
        return S.apply(S["lambda"](V.x, V.x + 1), 2)

    @m.define(name="applyL2")
    def apply_l2():
        # (= (applyL2) (apply (lambda ($x $y) (+ $x $y)) (2 7)))
        return S.apply(S["lambda"]((V.x, V.y), V.x + V.y), (2, 7))

    assert apply_l1() == [3]
    assert apply_l2() == [9]

    # A real lambda, mapped over a list: Python's own lambda IS `|->`.
    @m.define(name="increment-all")
    def increment_all(items):
        # (= (increment-all $items) (maplist (|-> ($a) (+ 1 $a)) $items))
        return fn.maplist(lambda a: 1 + a, items)

    assert increment_all((1, 2, 3)) == [Expression((2, 3, 4))]

    # Applied where it stands, which a compiled body will not do.
    folding = S["|->"]((V.acc, V.e), G(1).eq(V.e) | V.acc)
    assert m.eval((folding, FALSE, 1)) == [True]

    @m.define
    def myfunc(a, b):
        # (= (myfunc $a $b) (cons $a $b))
        return fn.cons(a, b)

    # A lambda over a PARTIAL application bound above it.
    @m.define(name="through-partial")
    def through_partial():
        # (let $f (myfunc 42) ((|-> ($x) ($f ($x 2 3))) 43))
        f = myfunc(42)
        g = lambda x: f((x, 2, 3))  # noqa: E731  -- the binding IS the point: it stores (|-> ($x) ...)
        return g(43)

    assert through_partial() == [Expression((42, 43, 2, 3))]

    # Partially applied: one argument now, the other later.
    assert m.eval(((S["|->"]((V.x, V.y), (42, V.x, V.y)), 43), 44)) == [
        Expression((42, 43, 44))
    ]

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
