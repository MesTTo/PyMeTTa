"""examples/ch07-control-flow/07-03-let-and-sequencing/11-nop.metta in Python: the step whose answer you do not want.

`nop` evaluates every argument and answers the unit. `UNIT` is the package's
own value for `()`, so the claims compare against it rather than against a
rebuilt empty expression.

What it discards is the ANSWERS, not the work, so the writes inside one still
land. They go into spaces of their own through the ordinary write door, which
is what `add-atom` is.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import UNIT, S, V, fn


def twin(m):
    """Discard answers, keep effects, and stay one answer per branch."""
    nop = m.fn.nop
    assert nop() == [UNIT]
    assert nop(1) == [UNIT]
    assert nop(1, 2, 3) == [UNIT]

    log = m.metta.space(S.log)
    assert m.answers(fn.nop(fn.add_atom(log, S.seen(1)), fn.add_atom(log, S.seen(2)))) == [UNIT]
    assert [row.n for row in log[S.seen(V.n)]] == [1, 2]

    # The difference from `empty`: `empty` answers nothing at all, so the
    # answer LIST is empty, while `nop` answers exactly one thing and that
    # thing is the unit.
    assert nop(1) == [UNIT]
    assert m.answers(fn.empty()) == []

    # It is not a collapse. An argument with three answers is three calls of
    # `nop`, so three units come back and all three writes land.
    drained = m.metta.space(S.drained)
    written = fn.let(  # rung: let as a binder over a generator, which `for` cannot build as data
        V.x, fn.superpose((1, 2, 3)), fn.add_atom(drained, S.x(V.x))
    )
    assert m.answers(fn.nop(written)) == [UNIT, UNIT, UNIT]
    assert len(drained[S.x(V.n)]) == 3

    # The unit is the same value every runnable that exists for its effect
    # answers, which is why a `nop` composes with them without a special case.
    assert nop(1) != m.fn.add_atom(log, S.seen(3))
    assert nop(1) == nop(2)


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 3246 inferences, 0.8178x the example's 3969; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 3246
