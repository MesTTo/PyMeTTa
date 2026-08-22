"""The Python twin of examples/basics/reading_forms.metta: reading a form.

Telling "still typing" apart from "that is wrong".

This is the example where s-expression text is the SUBJECT, not the spelling.
`sread-command` reads text and answers `(complete $term)`, `incomplete`, or
raises; the text it reads is a datum, so the twin writes it the way the
original writes it, as a string literal, marked `val(...)` so that reading
the twin says which strings are data and which would have been programs.
Nothing here reaches the engine through source text: every form is a term.
"""

from petta import S, expr, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 14319 to 14305, -14, by reading the fuel
#: balance with the deterministic b_getval/2 instead of the nondeterministic
#: nb_current/2. The saving is TWO INFERENCES PER RUNNABLE FORM, not per
#: reduction, which is what the spread says: this lane's one-form twins move by
#: two and fib moves by two as well across 2.69 million charged reductions,
#: while math moves by 32 over its sixteen forms. A step costs six inferences
#: either way, measured against a loop with the step removed; the change is
#: worth 2.71% of let-heavy's instructions:u, which the inference counter
#: cannot see. Prior: #: RE-PINNED 2026-08-22, 13959 to 14319, +360 (+2.58%), by P14.8, and the
#: larger part is that m.eval now opens the FUEL SCOPE a runnable form opens,
#: so max-stack-depth applies through it and petta_fuel_step/2 charges every
#: reduction here exactly as it charges one under `!`. The lane's earlier
#: 0.6558x parity was measuring a bound the Python door was not paying, which
#: is why fib now reads a ratio of 1.00 against its original. Three smaller
#: parts are already in this figure: merging the fuel scope's two globals into
#: one took a step inside a scope from seven inferences to six, the error
#: short circuit tests a call's computed operands for an error atom, and the
#: prelude gained throw beside if-error.
#: RE-PINNED 2026-08-22, 14305 to 14295, at P14.17 automatic tabling: the
#: imported-library decision and lazy handler layout lowers this floor by 10;
#: re-measured min-of-three fresh-process.
BUDGET = 14295

READ = S["sread-command"]


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    # !(test (sread-command "(f a)") (complete (f a)))
    yield m.eval(S.test(READ(val("(f a)")), S.complete(S.f(S.a))))

    # Still typing. More text could finish any of these.
    # !(test (sread-command "(f a") incomplete)
    yield m.eval(S.test(READ(val("(f a")), S.incomplete))
    # !(test (sread-command "(a (b (c") incomplete)
    yield m.eval(S.test(READ(val("(a (b (c")), S.incomplete))
    # !(test (sread-command "(= (f $x)") incomplete)
    yield m.eval(S.test(READ(val("(= (f $x)")), S.incomplete))

    # An empty line re-prompts rather than erroring.
    # !(test (sread-command "") incomplete)
    yield m.eval(S.test(READ(val("")), S.incomplete))
    # !(test (sread-command "   ") incomplete)
    yield m.eval(S.test(READ(val("   ")), S.incomplete))
    # !(test (sread-command "; only a comment") incomplete)
    yield m.eval(S.test(READ(val("; only a comment")), S.incomplete))

    # A bare atom is a whole form.
    # !(test (sread-command "hello") (complete hello))
    yield m.eval(S.test(READ(val("hello")), S.complete(S.hello)))

    # Not "just count parens": a bracket inside a string or a comment must
    # not count.
    # !(test (sread-command "(f \"a)b\")") (complete (f "a)b")))
    yield m.eval(S.test(READ(val('(f "a)b")')), S.complete(S.f(val("a)b")))))
    # !(test (sread-command "(f a) ; )))") (complete (f a)))
    yield m.eval(S.test(READ(val("(f a) ; )))")), S.complete(S.f(S.a))))

    # An unterminated string IS incomplete, because a MeTTa string may span
    # lines.
    # !(test (sread-command "(f \"a") incomplete)
    yield m.eval(S.test(READ(val('(f "a')), S.incomplete))

    # One bracket too many is not incomplete: no further typing repairs it.
    # !(import! &self (library lib_he)) answers (())
    yield m.eval(S["import!"](S["&self"], expr(S.library, S.lib_he)))
    # !(test (if-error (catch (sread-command "(f a))")) Error NoError) Error)
    yield m.eval(
        S.test(
            S["if-error"](S["catch"](READ(val("(f a))"))), S.Error, S.NoError),
            S.Error,
        )
    )
