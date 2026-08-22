"""The Python twin of examples/translation/translatorrule_for.metta.

A user-defined `for` as a translator rule: the rule rewrites `(for $var $coll
$body)` into `(let $var (superpose $coll) $body)` at compile time, so `myfun`
compiles to a superposition and its answers come back as a collapse.

Both definitions stay at the container door, each for a reason the compiled
subset states itself. `for`'s body binds the variable HELD IN a parameter,
`(let $var ...)`, and assignment in a compiled body binds a plain Python NAME,
so there is no position to spell that in; `for` is a Python keyword besides.
`myfun`'s body passes `$x`, a variable that is not one of its parameters, and
names `even` and `odd`, which are lowercase symbols the engine knows no
function for, so a compiled body refuses both. The residue table records them
against P14.4.

The runnable form is the term door, and its condition builds through the
operators: `(V.x % 2).eq(0)` is `(== (% $x 2) 0)`, with `eq` the method
because Python's `==` on atoms is structural equality.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4111 to 4111, +0, by the wave-4 idiom rewrite: every
#: form is the same term built at the same door, so the rewrite is a SPELLING
#: change and the counter says so.
BUDGET = 4111


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    the `add-translator-rule!` form answers the rule it registered.
    """
    # (: for (-> Atom Atom Atom %Undefined%))
    m += S[":"](
        S["for"], S["->"](S.Atom, S.Atom, S.Atom, S["%Undefined%"])
    )

    # (= (for $var $collection $body)
    #    (noeval (let $var (superpose $collection) $body)))
    m += equation(S["for"](V.var, V.collection, V.body)).to(
        S.noeval(S.let(V.var, S.superpose(V.collection), V.body))
    )

    # !(add-translator-rule! for)
    yield m.eval(S["add-translator-rule!"](S["for"]))

    # (= (myfun $L)
    #    (for $x $L (if (== (% $x 2) 0) (even $x) (odd $x))))
    m += equation(S.myfun(V.L)).to(
        S["for"](
            V.x,
            V.L,
            S["if"]((V.x % 2).eq(0), S.even(V.x), S.odd(V.x)),
        )
    )

    # !(test (collapse (myfun (3 4))) ((odd 3) (even 4)))
    yield m.eval(
        S.test(
            S.collapse(S.myfun((3, 4))),
            (S.odd(3), S.even(4)),
        )
    )
