"""The Python twin of examples/types/types_nondet.metta: one name, two signatures.

`f` is declared for `Type1` AND for `Type2`, so an argument arrives as either
and the OUTPUT type has to agree with the branch that ran. `T3in` is a `Type1`
whose branch answers a `Type2`, so the call has no answer at all; declaring
`T3in` a `Type2` as well makes the same call answer.

The comparison is `=alpha` rather than `==` and the reason is the file's own
subject: `(== T2in T1in)` compares two KNOWN and different types, which `==`
refuses by name. Both references refuse the `==` spelling too.

`f` is written at the container door: `=alpha` is not a Python identifier, so
no compiled body can name it, and no alias reaches it either, since a body
resolves a free name EXACTLY and an alias would store the alias.
"""

from petta import S, V, equation

#: Why this twin sits below the top rung, in the form the lane's idiom check reads:
#: `f`'s body names `=alpha`, which is not a Python identifier, and a compiled body
#: resolves a free name EXACTLY so no alias reaches it; the `(: ...)` declarations have no
#: `typed(x, T)` builder.
RUNG = "container door for f, whose body names =alpha, which is not a Python identifier"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 8674 to 9449, +775, by P14.8's
#: m.eval fuel-scope alignment: petta_fuel_step/2 now charges every
#: reduction as it does under `!`, less the two-inference-per-runnable-form
#: saving from the deterministic b_getval/2 fuel-balance read. Prior: ADDED
#: 2026-08-22 at 8674 by 47554fc's control/types twin baseline.
BUDGET = 9449


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    alpha = S["=alpha"]

    # (: f (-> Type1 Type1))
    m += S[":"](S.f, S["->"](S.Type1, S.Type1))
    # (: f (-> Type2 Type2))
    m += S[":"](S.f, S["->"](S.Type2, S.Type2))

    # (= (f $a)
    #    (if (=alpha $a T1in)
    #        T1out
    #        (if (=alpha $a T2in)
    #            T2out
    #            Tdefault)))
    m += equation(S.f(V.a)).to(
        S["if"](
            alpha(V.a, S.T1in),
            S.T1out,
            S["if"](alpha(V.a, S.T2in), S.T2out, S.Tdefault),
        )
    )

    # (: T1in Type1)
    m += S[":"](S.T1in, S.Type1)
    # (: T1out Type1)
    m += S[":"](S.T1out, S.Type1)
    # (: T2in Type2)
    m += S[":"](S.T2in, S.Type2)
    # (: T2out Type2)
    m += S[":"](S.T2out, S.Type2)

    # (: T3in Type1)
    m += S[":"](S.T3in, S.Type1)
    # (: Tdefault Type2)
    m += S[":"](S.Tdefault, S.Type2)

    # !(test (f T1in) T1out)
    yield m.eval(S.test(S.f(S.T1in), S.T1out))
    # !(test (f T2in) T2out)
    yield m.eval(S.test(S.f(S.T2in), S.T2out))
    # Type1 of T3in does not go along with Type2 output.
    # !(test-no-answer (f T3in)) answers (True)
    yield m.eval(S["test-no-answer"](S.f(S.T3in)))

    # But if we make T3in also of Type2 then it is fine if output is Type2.
    # (: T3in Type2)
    m += S[":"](S.T3in, S.Type2)
    # !(test (f T3in) Tdefault)
    yield m.eval(S.test(S.f(S.T3in), S.Tdefault))
