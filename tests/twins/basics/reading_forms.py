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
BUDGET = 13959

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
