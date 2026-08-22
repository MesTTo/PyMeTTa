"""Purpose: examples/functions/specialize.metta in Python: a call carrying a function specializes on it.

Every shape is here: the function argument first, last, nested one level and
nested two, reached through a wrapper, answered instead of applied, called
recursively with a DIFFERENT function each time, and used twice in one body.

Three definitions are ordinary Python functions: `p1` is arithmetic,
`wrapper2` answers its argument through `id`, and `higher-order-fun` applies
both of its parameters and pairs the results, which a Python tuple spells.

The rest take the `@rules` shape of the definitional decorator, for three
reasons the file makes unavoidable.

Most heads are PATTERNS rather than parameters: `(map-flat $f ())` fixes the
empty expression, `(map-flat2 ((cons $x $xs) $f))` fixes a whole subterm. A
stacked `@m.define` clause fixes a head position with a literal DEFAULT, and a
literal is a bool, int, float or str, so none of these heads has a
function-shape spelling.

`wrapper` names `map-flat` in its body, and a compiled body resolves a free
name EXACTLY, so a hyphenated engine function is unreachable from one.

And the partial applications `(+ 1)`, `(* 1)`, `(+ 2)` and `(+ 4)` have no
operator spelling, because `+` needs both operands to be an operator at all;
they are written by CALLING the symbol, so `S["+"](1)` is `(+ 1)`.
`trickyspec` also tests
with `=`, MeTTa's unification rather than Python's `==`, and
`equation(lhs).to(rhs)` is the builder for exactly that atom.

The residue table records the head-pattern and hyphenated-name gaps against
P14.4.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import Expression, S, equation, rules

#: The four `map-flat` variants, which are one algorithm at four argument
#: shapes: the file's own lesson is the variation, so they read together.
#: They are laws rather than computations, and they build atoms out of nothing
#: but their own parameters, so they need no engine and live at module level.
#: `twin` adds each one where the original defines it.

# rung: all four of them: every head fixes `()` or `(cons $x $xs)`, and a
#   stacked clause's literal default is a bool, int, float or str. The two
#   (: ...) declarations below follow from the same drop, since the annotation
#   door needs a decorated definition (residue, P14.4)
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
#: RE-PINNED 2026-08-22, 67671 to 64377, -3294 (-4.9%), by the twin
#: contract change: eleven `test` wrappers left the engine for `assert`,
#: and every partial application is built by CALLING the symbol rather than
#: as a tuple; the twenty equations and every specialization stayed.
#: Against the example's 83773 the ratio is 0.7685 [measured 2026-08-22
#: min-of-3, `twin_coverage.py --measure`]. The old figure priced a
#: different program.
BUDGET = 64377

#: The partial application the file maps with. `+` needs both operands to be
#: a Python operator at all, so a partial is written by CALLING the symbol,
#: which is what builds an expression out of a head and its arguments.
ADD_ONE = S["+"](1)


def twin(m):
    """Specialize eight functions on the function they carry."""
    m.add(*flat)
    assert m.eval(S["map-flat"](ADD_ONE, (1, 2, 3))) == [Expression((2, 3, 4))]

    m.add(*flat2)
    assert m.eval(S["map-flat2"](((1, 2, 3), ADD_ONE))) == [Expression((2, 3, 4))]

    # (: map-flat3 (-> Atom %Undefined%))
    m += S[":"](S["map-flat3"], S["->"](S.Atom, S["%Undefined%"]))
    m.add(*flat3)

    @m.define
    def p1(x):
        # (= (p1 $x) (+ 1 $x))
        return 1 + x

    assert m.eval(S["map-flat3"](S.p1((1, 2)))) == [Expression((2, 3))]

    # (: map-flat4 (-> Atom %Undefined%))
    m += S[":"](S["map-flat4"], S["->"](S.Atom, S["%Undefined%"]))
    m.add(*flat4)
    assert m.eval(S["map-flat4"]((S.x, S.p1((1, 2))))) == [Expression((2, 3))]

    # rung: the body names `map-flat`, and a compiled body resolves a free name
    #   EXACTLY (residue, P14.4)
    @rules
    def wrapper(f, items):
        # (= (wrapper $f $list) (map-flat $f $list))
        yield equation(S.wrapper(f, items)).to(S["map-flat"](f, items))

    m.add(*wrapper)
    assert m.eval(S.wrapper(ADD_ONE, (1, 2, 3))) == [Expression((2, 3, 4))]

    @m.define
    def wrapper2(f):
        # (= (wrapper2 $f) (id $f))
        return id(f)

    # `id` answers its argument, and a partial application prints as
    # `(partial + (1))`. The original writes the expected value as `(+ 1)` and
    # lets `test` evaluate both sides down to the same partial; Python names
    # the answer instead.
    assert m.eval(S.wrapper2(ADD_ONE)) == [S.partial(S["+"], (1,))]

    # rung: the body tests with `=`, MeTTa's unification, for which Python's `==`
    #   is not a spelling, and calls the operator partial `(+ 2)` (residue, P14.4)
    @rules
    def tricky(f):
        # (= (trickyspec $f) (if (= ($f 1) 2) (trickyspec (+ 2)) ($f 1)))
        yield equation(S.trickyspec(f)).to(
            S["if"](  # rung: MeTTa's if over a unification
                equation((f, 1)).to(2),
                S.trickyspec(S["+"](2)),
                (f, 1),
            )
        )

    m.add(*tricky)
    assert m.eval(S.trickyspec(S["+"](4))) == [5]
    assert m.eval(S.trickyspec(ADD_ONE)) == [3]

    # rung: one head fixes `()` and the other `(cons $x $xs)`, neither of which a
    #   literal default can be (residue, P14.4)
    @rules
    def folded(f, init, x, xs):
        # (= (fold-nested $f $init ()) $init)
        yield equation(S["fold-nested"](f, init, ())).to(init)
        # (= (fold-nested $f $init (cons $x $xs))
        #       (if (is-expr $x)
        #         (fold-nested $f (fold-nested $f $init $x) $xs)
        #         (fold-nested $f ($f $init $x) $xs)))
        yield equation(S["fold-nested"](f, init, S.cons(x, xs))).to(
            S["if"](  # rung: MeTTa's if inside a stored equation
                S["is-expr"](x),
                S["fold-nested"](f, S["fold-nested"](f, init, x), xs),
                S["fold-nested"](f, (f, init, x), xs),
            )
        )

    m.add(*folded)
    assert m.eval(S["fold-nested"](S["+"], 0, (1, (2, 3)))) == [6]

    @m.define(name="higher-order-fun")
    def higher_order_fun(a, b):
        # (= (higher-order-fun $a $b) (($a 1) ($b 1)))
        return (a(1), b(1))

    # (= (fun2) (higher-order-fun (+ 1) (* 1))) and its mirror
    # rung: each body holds two operator partials, `(+ 1)` and `(* 1)`, which no
    #   Python operator spells (residue, P14.4)
    m += equation(S.fun2()).to(S["higher-order-fun"](ADD_ONE, S["*"](1)))
    m += equation(S.fun3()).to(S["higher-order-fun"](S["*"](1), ADD_ONE))

    assert m.eval(S.fun2()) == [Expression((2, 1))]
    assert m.eval(S.fun3()) == [Expression((1, 2))]
