"""Purpose: examples/functions/specialize.metta in Python: a call carrying a function specializes on it.

Every shape is here: the function argument first, last, nested one level and
nested two, reached through a wrapper, answered instead of applied, called
recursively with a DIFFERENT function each time, and used twice in one body.

Seven definitions are ordinary Python functions and ten are equations in five
rule bundles, and one classifier decides which: whether the HEAD is a
parameter list or a pattern. `(map-flat $f ())` fixes the empty expression and
`(map-flat2 ((cons $x $xs) $f))` fixes a whole subterm; a stacked `@m.define`
clause fixes a head position with a literal DEFAULT, and a literal is a bool,
int, float or str, so none of those heads has a function-shape spelling and
all four `map-flat` families plus `fold-nested` take the `@m.rules` door,
where the generator's parameters ARE the equations' variables and the bundle
lands in this space as it is written.

The bodies name rule-bundle heads through the underscore map and call bound
decorated functions directly. A `Defined` value mentioned in term position
encodes as its installed MeTTa head, including `higher-order-fun`.

Each recursive list rebuild names the applied head and recursive tail before
calling `cons`, matching the examples' nested `let` sequence.
[source: examples/functions/specialize.metta:9; commit=f053d9d46aa43b9beec360eae30b9016ffbf231f]

Two heads Python's punctuation does not reach. The partial applications
`(+ 1)`, `(* 1)`, `(+ 2)` and `(+ 4)` have no operator spelling, because `+`
needs both operands to be an operator at all, so they are written by CALLING
the word-table symbol: `S.add(1)` is `(+ 1)`. And `trickyspec` tests with `=`, MeTTa's
unification rather than Python's `==`, for which `fn["="]` is the function
namespace's exact spelling.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable;
    commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from typing import Any

from metta import Atom, Expression, S, V, arrow, equation, fn, if_, typed

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=d4e4f9cf0500c00c8f1201a60cbcf54de7c3fa84].
BUDGET = 1

#: The partial application the file maps with. `+` needs both operands to be
#: a Python operator at all, so a partial is written by CALLING the symbol,
#: which is what builds an expression out of a head and its arguments.
ADD_ONE = S.add(1)


def twin(m):
    """Specialize eight functions on the function they carry."""

    @m.rules
    def flat(f, x, xs):
        """The two `map-flat` equations: the function argument comes FIRST."""
        # (= (map-flat $f ()) ())
        yield equation(S.map_flat(f, ())).to(())
        # (= (map-flat $f (cons $x $xs))
        #    (let $head ($f $x)
        #      (let $rest (map-flat $f $xs) (cons $head $rest))))
        yield equation(S.map_flat(f, fn.cons(x, xs))).to(
            S.let(  # rung: this rules generator builds the stored let where no Python statement position exists
                V.head,
                (f, x),
                S.let(  # rung: the recursive value must be named before cons receives its Expression-typed tail
                    V.rest,
                    S.map_flat(f, xs),
                    S.cons(V.head, V.rest),
                ),
            )
        )

    assert m.eval(S.map_flat(ADD_ONE, (1, 2, 3))) == [Expression((2, 3, 4))]

    @m.rules
    def flat2(f, x, xs):
        """The two `map-flat2` equations: the function argument comes LAST, inside a pair."""
        # (= (map-flat2 (() $f)) ())
        yield equation(S.map_flat2(((), f))).to(())
        # (= (map-flat2 ((cons $x $xs) $f))
        #    (let $head ($f $x)
        #      (let $rest (map-flat2 ($xs $f)) (cons $head $rest))))
        yield equation(S.map_flat2((fn.cons(x, xs), f))).to(
            S.let(  # rung: this rules generator builds the stored let where no Python statement position exists
                V.head,
                (f, x),
                S.let(  # rung: the recursive value must be named before cons receives its Expression-typed tail
                    V.rest,
                    S.map_flat2((xs, f)),
                    S.cons(V.head, V.rest),
                ),
            )
        )

    assert m.eval(S.map_flat2(((1, 2, 3), ADD_ONE))) == [Expression((2, 3, 4))]

    # (: map-flat3 (-> Atom %Undefined%))
    # rung: below the ANNOTATION door, which needs a decorated function, and
    #   this head is a pattern (residue, P14.4)
    m += typed(S.map_flat3, arrow(Atom, Any))

    @m.rules
    def flat3(f, x, xs):
        """The two `map-flat3` equations: the function argument leads a pair."""
        # (= (map-flat3 ($f ())) ())
        yield equation(S.map_flat3((f, ()))).to(())
        # (= (map-flat3 ($f (cons $x $xs)))
        #    (let $head ($f $x)
        #      (let $rest (map-flat3 ($f $xs)) (cons $head $rest))))
        yield equation(S.map_flat3((f, fn.cons(x, xs)))).to(
            S.let(  # rung: this rules generator builds the stored let where no Python statement position exists
                V.head,
                (f, x),
                S.let(  # rung: the recursive value must be named before cons receives its Expression-typed tail
                    V.rest,
                    S.map_flat3((f, xs)),
                    S.cons(V.head, V.rest),
                ),
            )
        )

    @m.define
    def p1(x):
        # (= (p1 $x) (+ 1 $x))
        return 1 + x

    assert m.eval(S.map_flat3(S.p1((1, 2)))) == [Expression((2, 3))]

    # (: map-flat4 (-> Atom %Undefined%))
    m += typed(S.map_flat4, arrow(Atom, Any))

    @m.rules
    def flat4(v, f, x, xs):
        """The two `map-flat4` equations: the same pair, nested one level deeper."""
        # (= (map-flat4 ($v ($f ()))) ())
        yield equation(S.map_flat4((v, (f, ())))).to(())
        # (= (map-flat4 ($v ($f (cons $x $xs))))
        #    (let $head ($f $x)
        #      (let $rest (map-flat4 ($v ($f $xs))) (cons $head $rest))))
        yield equation(S.map_flat4((v, (f, fn.cons(x, xs))))).to(
            S.let(  # rung: this rules generator builds the stored let where no Python statement position exists
                V.head,
                (f, x),
                S.let(  # rung: the recursive value must be named before cons receives its Expression-typed tail
                    V.rest,
                    S.map_flat4((v, (f, xs))),
                    S.cons(V.head, V.rest),
                ),
            )
        )

    assert m.eval(S.map_flat4((S.x, S.p1((1, 2))))) == [Expression((2, 3))]

    @m.define
    def wrapper(f, items):
        # (= (wrapper $f $list) (map-flat $f $list))
        return S.map_flat(f, items)

    assert m.eval(S.wrapper(ADD_ONE, (1, 2, 3))) == [Expression((2, 3, 4))]

    @m.define
    def wrapper2(f):
        # (= (wrapper2 $f) (id $f))
        return fn.id(f)

    # `id` answers its argument, and a partial application prints as
    # `(partial + (1))`. The original writes the expected value as `(+ 1)` and
    # lets `test` evaluate both sides down to the same partial; Python names
    # the answer instead.
    assert wrapper2(ADD_ONE) == [S.partial(S.add, (1,))]

    @m.define
    def trickyspec(f):
        # (= (trickyspec $f) (if (= ($f 1) 2) (trickyspec (+ 2)) ($f 1)))
        return trickyspec(S.add(2)) if fn["="]((f, 1), 2) else (f, 1)

    assert trickyspec(S.add(4)) == [5]
    assert trickyspec(ADD_ONE) == [3]

    @m.rules
    def folded(f, init, x, xs):
        """The two `fold-nested` equations: one head fixes `()`, the other a cons."""
        # (= (fold-nested $f $init ()) $init)
        yield equation(S.fold_nested(f, init, ())).to(init)
        # (= (fold-nested $f $init (cons $x $xs))
        #       (if (is-expr $x)
        #         (fold-nested $f (fold-nested $f $init $x) $xs)
        #         (fold-nested $f ($f $init $x) $xs)))
        yield equation(S.fold_nested(f, init, fn.cons(x, xs))).to(
            if_(
                fn.is_expr(x),
                S.fold_nested(f, S.fold_nested(f, init, x), xs),
                S.fold_nested(f, (f, init, x), xs),
            )
        )

    assert m.eval(S.fold_nested(S.add, 0, (1, (2, 3)))) == [6]

    @m.define
    def higher_order_fun(a, b):
        # (= (higher-order-fun $a $b) (($a 1) ($b 1)))
        return (a(1), b(1))

    @m.define
    def fun2():
        # (= (fun2) (higher-order-fun (+ 1) (* 1)))
        return higher_order_fun(S.add(1), S.mul(1))

    @m.define
    def fun3():
        # (= (fun3) (higher-order-fun (* 1) (+ 1)))
        return higher_order_fun(S.mul(1), S.add(1))

    assert fun2() == [Expression((2, 1))]
    assert fun3() == [Expression((1, 2))]
