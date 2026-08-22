"""The Python twin of examples/functions/specialize.metta: a call carrying a function specializes on it.

Every shape is here: the function argument first, last, nested one level and
nested two, reached through a wrapper, answered instead of applied, called
recursively with a DIFFERENT function each time, and used twice in one body.

Three definitions are ordinary Python functions: `p1` is arithmetic,
`wrapper2` answers its argument through `id`, and `higher-order-fun` applies
both of its parameters and pairs the results, which a Python tuple spells.

The rest take the `@rules` shape of the definitional decorator, for three reasons
the file makes unavoidable.

Most heads are PATTERNS rather than parameters: `(map-flat $f ())` fixes the
empty expression, `(map-flat2 ((cons $x $xs) $f))` fixes a whole subterm. A
stacked `@m.define` clause fixes a head position with a literal DEFAULT, and a
literal is a bool, int, float or str, so none of these heads has a
function-shape spelling.

`wrapper` names `map-flat` in its body, and a compiled body resolves a free
name EXACTLY, so a hyphenated engine function is unreachable from one.

And the partial applications `(+ 1)`, `(* 1)`, `(+ 2)` and `(+ 4)` have no
operator spelling, because `+` needs both operands to be an operator at all. A
tuple IS an expression, so `(S["+"], 1)` is `(+ 1)`. `trickyspec` also tests
with `=`, MeTTa's unification rather than Python's `==`, and
`equation(lhs).to(rhs)` is the builder for exactly that atom.

The residue table records the head-pattern and hyphenated-name gaps against
P14.4.
"""

from petta import S, equation, rules

#: The four `map-flat` variants, which are one algorithm at four argument
#: shapes: the file's own lesson is the variation, so they read together.
#: They are laws rather than computations, so they take the `@rules`
#: shape of the definitional decorator, and they build atoms out of nothing
#: but their own parameters, so they need no engine and live at module
#: level. `twin` adds each one where the original defines it.

# rung: below the function shape, all four of them: every head fixes `()` or
#   `(cons $x $xs)`, and a stacked clause's literal default is a bool, int,
#   float or str. The two (: ...) declarations below follow from the same drop,
#   since the annotation door needs a decorated definition (residue, P14.4)
@rules
def flat(f, x, xs):
    """The two `map-flat` equations: the function argument comes FIRST."""
    # (= (map-flat $f ()) ())
    yield equation(S["map-flat"](f, ())).to(())
    # (= (map-flat $f (cons $x $xs)) (cons ($f $x) (map-flat $f $xs)))
    yield equation(S["map-flat"](f, S.cons(x, xs))).to(
        S.cons((f, x), S["map-flat"](f, xs))
    )


@rules
def flat2(f, x, xs):
    """The two `map-flat2` equations: the function argument comes LAST, inside a pair."""
    # (= (map-flat2 (() $f)) ())
    yield equation(S["map-flat2"](((), f))).to(())
    # (= (map-flat2 ((cons $x $xs) $f)) (cons ($f $x) (map-flat2 ($xs $f))))
    yield equation(S["map-flat2"]((S.cons(x, xs), f))).to(
        S.cons((f, x), S["map-flat2"]((xs, f)))
    )


@rules
def flat3(f, x, xs):
    """The two `map-flat3` equations: the function argument leads a pair."""
    # (= (map-flat3 ($f ())) ())
    yield equation(S["map-flat3"]((f, ()))).to(())
    # (= (map-flat3 ($f (cons $x $xs))) (cons ($f $x) (map-flat3 ($f $xs))))
    yield equation(S["map-flat3"]((f, S.cons(x, xs)))).to(
        S.cons((f, x), S["map-flat3"]((f, xs)))
    )


@rules
def flat4(v, f, x, xs):
    """The two `map-flat4` equations: the same pair, nested one level deeper."""
    # (= (map-flat4 ($v ($f ()))) ())
    yield equation(S["map-flat4"]((v, (f, ())))).to(())
    # (= (map-flat4 ($v ($f (cons $x $xs))))
    #    (cons ($f $x) (map-flat4 ($v ($f $xs)))))
    yield equation(S["map-flat4"]((v, (f, S.cons(x, xs))))).to(
        S.cons((f, x), S["map-flat4"]((v, (f, xs))))
    )


#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 65533 to 67671, +2138 (+3.26%), and the per-step
#: reading places every inference of it. Three definitions moved onto the
#: decorator: `p1` costs about 1629 more, nearly all of it the one-time setup
#: the FIRST decorated definition in a process pays (2244 against the atom
#: door's 600 for one equation, where every later one costs 793 against 600),
#: `wrapper2` costs 278 more and `higher-order-fun` 140 more. Four pairs of
#: equations now enter through one `m.add` each instead of two `m +=`,
#: 19 + 18 + 18 + 18, the fixed cost of the many-wire add; the single-atom
#: `m.add` for `wrapper` costs nothing extra, since one wire takes the same
#: path `m +=` takes. The five steps that install nothing are unchanged to
#: the inference. The lane's parity reads 0.81 of the original. Prior: ADDED
#: 2026-08-22 at 65533 by 7f15dc1's wave-3 baseline.
BUDGET = 67671


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # (= (map-flat $f ()) ()) and (= (map-flat $f (cons $x $xs)) ...)
    m.add(*flat)

    # !(test (map-flat (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(S.test(S["map-flat"]((S["+"], 1), (1, 2, 3)), (2, 3, 4)))

    # (= (map-flat2 (() $f)) ()) and (= (map-flat2 ((cons $x $xs) $f)) ...)
    m.add(*flat2)

    # !(test (map-flat2 ((1 2 3) (+ 1))) (2 3 4))
    yield m.eval(
        S.test(S["map-flat2"](((1, 2, 3), (S["+"], 1))), (2, 3, 4))
    )

    # (: map-flat3 (-> Atom %Undefined%))
    m += S[":"](S["map-flat3"], S["->"](S.Atom, S["%Undefined%"]))

    # (= (map-flat3 ($f ())) ()) and (= (map-flat3 ($f (cons $x $xs))) ...)
    m.add(*flat3)

    @m.define
    def p1(x):
        # (= (p1 $x) (+ 1 $x))
        return 1 + x

    # !(test (map-flat3 (p1 (1 2))) (2 3))
    yield m.eval(S.test(S["map-flat3"](S.p1((1, 2))), (2, 3)))

    # (: map-flat4 (-> Atom %Undefined%))
    m += S[":"](S["map-flat4"], S["->"](S.Atom, S["%Undefined%"]))

    # (= (map-flat4 ($v ($f ()))) ()) and (= (map-flat4 ($v ($f (cons $x $xs)))) ...)
    m.add(*flat4)

    # !(test (map-flat4 (x (p1 (1 2)))) (2 3))
    yield m.eval(S.test(S["map-flat4"]((S.x, S.p1((1, 2)))), (2, 3)))

    # rung: below the function shape: the body names `map-flat`, and a compiled body
    #   resolves a free name EXACTLY (residue, P14.4)
    @rules
    def wrapper(f, items):
        # (= (wrapper $f $list) (map-flat $f $list))
        yield equation(S.wrapper(f, items)).to(S["map-flat"](f, items))

    m.add(*wrapper)

    # !(test (wrapper (+ 1) (1 2 3)) (2 3 4))
    yield m.eval(S.test(S.wrapper((S["+"], 1), (1, 2, 3)), (2, 3, 4)))

    @m.define
    def wrapper2(f):
        # (= (wrapper2 $f) (id $f))
        return id(f)

    # !(test (wrapper2 (+ 1)) (+ 1))
    yield m.eval(S.test(S.wrapper2((S["+"], 1)), (S["+"], 1)))

    # rung: below the function shape: the body tests with `=`, MeTTa's unification,
    #   for which Python's `==` is not a spelling, and calls the operator partial
    #   `(+ 2)` (residue, P14.4)
    @rules
    def tricky(f):
        # (= (trickyspec $f) (if (= ($f 1) 2) (trickyspec (+ 2)) ($f 1)))
        yield equation(S.trickyspec(f)).to(
            S["if"](
                equation((f, 1)).to(2),
                S.trickyspec((S["+"], 2)),
                (f, 1),
            )
        )

    m.add(*tricky)

    # !(test (trickyspec (+ 4)) 5)
    yield m.eval(S.test(S.trickyspec((S["+"], 4)), 5))
    # !(test (trickyspec (+ 1)) 3)
    yield m.eval(S.test(S.trickyspec((S["+"], 1)), 3))

    # rung: below the function shape: one head fixes `()` and the other `(cons $x
    #   $xs)`, neither of which a literal default can be (residue, P14.4)
    @rules
    def folded(f, init, x, xs):
        # (= (fold-nested $f $init ()) $init)
        yield equation(S["fold-nested"](f, init, ())).to(init)
        # (= (fold-nested $f $init (cons $x $xs))
        #       (if (is-expr $x)
        #         (fold-nested $f (fold-nested $f $init $x) $xs)
        #         (fold-nested $f ($f $init $x) $xs)))
        yield equation(S["fold-nested"](f, init, S.cons(x, xs))).to(
            S["if"](
                S["is-expr"](x),
                S["fold-nested"](f, S["fold-nested"](f, init, x), xs),
                S["fold-nested"](f, (f, init, x), xs),
            )
        )

    m.add(*folded)

    # !(test (fold-nested + 0 (1 (2 3))) 6)
    yield m.eval(S.test(S["fold-nested"](S["+"], 0, (1, (2, 3))), 6))

    @m.define(name="higher-order-fun")
    def higher_order_fun(a, b):
        # (= (higher-order-fun $a $b) (($a 1) ($b 1)))
        return (a(1), b(1))

    # (= (fun2) (higher-order-fun (+ 1) (* 1)))
    # rung: below the function shape, both of them: each body holds two operator
    #   partials, `(+ 1)` and `(* 1)`, which no Python operator spells (residue,
    #   P14.4)
    m += equation(S.fun2()).to(S["higher-order-fun"]((S["+"], 1), (S["*"], 1)))
    # (= (fun3) (higher-order-fun (* 1) (+ 1)))
    m += equation(S.fun3()).to(S["higher-order-fun"]((S["*"], 1), (S["+"], 1)))

    # !(test (fun2) (2 1))
    yield m.eval(S.test(S.fun2(), (2, 1)))
    # !(test (fun3) (1 2))
    yield m.eval(S.test(S.fun3(), (1, 2)))
