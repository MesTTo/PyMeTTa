"""The Python twin of examples/types/types_dependent.metta: a computed type.

`get-type` is an ordinary function, so a program may add equations to it and
give itself types no declaration states: an even number is an `EvenNumber`,
and a list whose elements are all even is an `EvenNumberList`. The declared
signatures of `f` and `g` then accept exactly those values, without the engine
learning a new rule.

The two `get-type` extensions are written at the container door. `get-type` is
hyphenated and a compiled body resolves a free name EXACTLY, so it cannot be
reached from one (wave one recorded that against P14.4 for `fibsmart`); the
second extension also matches a CONSTRUCTOR in its head, `(get-type (cons
$head $tail))`, where a compiled head takes plain parameters. `=alpha` is not
a Python identifier either, so no alias reaches it.

`f` and `g` are computations and are written as ones, with their declarations
as atoms written first: `@m.define` writes an annotation's declaration AFTER
the equation, which types/outputtype.py reproduces and the residue table
routes to P14.9.
"""

from petta import S, V, expr, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
BUDGET = 18937


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    kind = S["get-type"]
    alpha = S["=alpha"]

    # =alpha throughout, not ==: each comparison crosses KNOWN and different
    # types, which == refuses by name.
    # (= (get-type $x) (catch (if (=alpha (% $x 2) 0) EvenNumber)))
    m += S["="](
        kind(V.x),
        S["catch"](
            S["if"](
                alpha(S["%"](V.x, 2), 0), S.EvenNumber
            )
        ),
    )

    # (: f (-> EvenNumber EvenNumber EvenNumber))
    m += S[":"](
        S.f,
        S["->"](S.EvenNumber, S.EvenNumber, S.EvenNumber),
    )

    @m.define
    def f(x, y):
        # (= (f $x $y) (+ $x $y))
        return x + y

    # !(test (f 2 4) 6)
    yield m.eval(S.test(f(2, 4), 6))

    # (= (get-type (cons $head $tail))
    #    (if (=alpha (get-type $head) EvenNumber)
    #        (if (=alpha $tail ())
    #            EvenNumberList
    #            (get-type $tail))))
    m += S["="](
        kind(S.cons(V.head, V.tail)),
        S["if"](
            alpha(kind(V.head), S.EvenNumber),
            S["if"](
                alpha(V.tail, expr()),
                S.EvenNumberList,
                kind(V.tail),
            ),
        ),
    )

    # (: g (-> EvenNumberList Bool))
    m += S[":"](S.g, S["->"](S.EvenNumberList, S.Bool))

    @m.define
    def g(_li):
        # (= (g $L) True)
        # The parameter is a head variable the body never reads, and the
        # underscore says so to a Python reader.
        return True

    # !(test (g (2 4 6)) True)
    yield m.eval(S.test(g(expr(2, 4, 6)), TRUE))
