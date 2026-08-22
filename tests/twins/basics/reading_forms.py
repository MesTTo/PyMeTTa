"""examples/basics/reading_forms.metta in Python: still typing, or wrong?

This is the example where s-expression text is the SUBJECT rather than the
spelling. `sread-command` reads text and answers `(complete $term)`,
`incomplete`, or refuses; the text it reads is a datum, so it is written the
way the original writes it, marked `val(...)` so that reading this file says
which strings are data and which would have been programs. The expected terms
are built at the `S.` door, because a twin may not reach the engine through
`parse` either.

The last claim is where Python's own vocabulary takes over. One bracket too
many cannot be repaired by more typing, so the reader refuses, and a refusal
crosses into Python as an EXCEPTION rather than as an atom: the original's
`(if-error (catch ...) Error NoError)` is a try/except here, and the `lib_he`
import that form needed goes with it.
"""

from petta import EngineError, S, val

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-23, 3782 to 3730, -52, by the p14-tabling merge, the sole
#: change between the two readings: the define-path saving seen corpus-wide.
#: Ratio 3730/22552 = 0.1654 [measured 2026-08-23 min-of-3 via
#: tools/twin_coverage.py --measure]. Prior:
#: RE-PINNED 2026-08-22, 14305 to 3782, -10523 (-73.6%), by the twin
#: contract change: twelve `test` wrappers left the engine for `assert`,
#: and the last claim dropped the `lib_he` import with its
#: `if-error`/`catch` pair: a refusal crosses into Python as an exception,
#: so a try/except says it. Against the example's 22567 the ratio is 0.1676
#: [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The old
#: figure priced a different program.
BUDGET = 3730


def twin(m):
    """Read eleven fragments, and refuse the twelfth."""
    read = m.fn("sread-command")

    assert read(val("(f a)")) == S.complete(S.f(S.a))

    # Still typing. More text could finish any of these.
    assert read(val("(f a")) == S.incomplete
    assert read(val("(a (b (c")) == S.incomplete
    assert read(val("(= (f $x)")) == S.incomplete

    # An empty line re-prompts rather than erroring, which is the commonest
    # input in any console.
    assert read(val("")) == S.incomplete
    assert read(val("   ")) == S.incomplete
    assert read(val("; only a comment")) == S.incomplete

    # A bare atom is a whole form.
    assert read(val("hello")) == S.complete(S.hello)

    # Not "just count parens": a bracket inside a string or a comment must
    # not count.
    assert read(val('(f "a)b")')) == S.complete(S.f(val("a)b")))
    assert read(val("(f a) ; )))")) == S.complete(S.f(S.a))

    # An unterminated string IS incomplete, because a MeTTa string may span
    # lines.
    assert read(val('(f "a')) == S.incomplete

    # One bracket too many is not incomplete: no amount of further typing
    # repairs it, so the reader refuses and Python sees an exception.
    refused = False
    try:
        read(val("(f a))"))
    except EngineError:
        refused = True
    assert refused
