"""examples/basics/reading_forms.metta in Python: still typing, or wrong?

This is the example where s-expression text is the SUBJECT rather than the
spelling. `sread-command` reads text and answers `(complete $term)`,
`incomplete`, or refuses; the text it reads is a datum, so it is written the
way the original writes it, marked `ground(...)` so that reading this file
says which strings are data and which would have been programs. The expected
terms are built at the `S.` door, because a twin may not reach the engine
through `parse` either.

The last claim is where Python's own vocabulary takes over. One bracket too
many cannot be repaired by more typing, so the reader refuses, and a refusal
crosses into Python as an EXCEPTION rather than as an atom: the original's
`(if-error (catch ...) Error NoError)` is a try/except here, and the `lib_he`
import that form needed goes with it. `EngineError` is a detailed error, so it
arrives from the errors satellite rather than from the narrow root.
"""

from metta import S, ground
from metta.errors import EngineError

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Read eleven fragments, and refuse the twelfth."""
    read = m.fn.sread_command

    assert read(ground("(f a)")).one() == S.complete(S.f(S.a))

    # Still typing. More text could finish any of these.
    assert read(ground("(f a")).one() == S.incomplete
    assert read(ground("(a (b (c")).one() == S.incomplete
    assert read(ground("(= (f $x)")).one() == S.incomplete

    # An empty line re-prompts rather than erroring, which is the commonest
    # input in any console.
    assert read(ground("")).one() == S.incomplete
    assert read(ground("   ")).one() == S.incomplete
    assert read(ground("; only a comment")).one() == S.incomplete

    # A bare atom is a whole form.
    assert read(ground("hello")).one() == S.complete(S.hello)

    # Not "just count parens": a bracket inside a string or a comment must
    # not count.
    assert read(ground('(f "a)b")')).one() == S.complete(S.f(ground("a)b")))
    assert read(ground("(f a) ; )))")).one() == S.complete(S.f(S.a))

    # An unterminated string IS incomplete, because a MeTTa string may span
    # lines.
    assert read(ground('(f "a')).one() == S.incomplete

    # One bracket too many is not incomplete: no amount of further typing
    # repairs it, so the reader refuses and Python sees an exception.
    refused = False
    try:
        read(ground("(f a))")).one()
    except EngineError:
        refused = True
    assert refused
