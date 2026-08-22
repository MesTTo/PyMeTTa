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

`f` and `g` are computations and are written as ones. Their declarations stay
atoms because `EvenNumber` and `EvenNumberList` are computed MeTTa refinement
types, not sound Python annotations for the host functions. Annotation-derived
declarations now publish before their equations; outputtype.py exercises that
door directly.
"""

from petta import S, V, equation, val

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: the `get-type` extensions name a hyphenated function and one matches a CONSTRUCTOR
#: head, and the `(: f ...)` declarations are about computed refinement types with no `typed(x, T)`
#: builder to write them.
RUNG = "container door: the get-type extensions name a hyphenated function and match a constructor head"

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 18937 to 20711, +1774, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 18937 by 47554fc's control/types twin baseline.
BUDGET = 20711


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
    m += equation(kind(V.x)).to(S.catch(S["if"](alpha(V.x % 2, 0), S.EvenNumber)))

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
    yield m.eval(S.test(S.f(2, 4), 6))

    # (= (get-type (cons $head $tail))
    #    (if (=alpha (get-type $head) EvenNumber)
    #        (if (=alpha $tail ())
    #            EvenNumberList
    #            (get-type $tail))))
    m += equation(kind(S.cons(V.head, V.tail))).to(
        S["if"](
            alpha(kind(V.head), S.EvenNumber),
            S["if"](
                alpha(V.tail, ()),
                S.EvenNumberList,
                kind(V.tail),
            ),
        )
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
    yield m.eval(S.test(S.g((2, 4, 6)), TRUE))
