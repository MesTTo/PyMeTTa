"""examples/ch08-data/08-02-sequence-variables/04-the-two-sided-fragments.metta in Python: how far a written ask reaches.

The example asks through `unify`, because that is the one MeTTa form whose two
operands are both syntax; every other MeTTa door faces a value. Python has no
such restriction, so `solve(pattern, subject)` takes the same two written terms
and lands in the same place: measured 2026-09-07, all eight asks answer here
what they answer there, refusal included.

What either door does with a gap on the right is the measurement. The right
side is read the way stored atoms are read, so a marker there is ordinary data
and every ask a program can write is the one-sided fragment. The shapes the
last-position and linear-shallow calculi are for therefore answer as one-sided
matches that fail, and the calculus's own trivial identity refuses. That
refusal reaches Python as an EngineError message; the structured payload the
MeTTa side reads apart with `index-atom` has no attribute on the exception.
"""

from metta import S, V, seg, solve
from metta.errors import EngineError


def twin(m):  # noqa: ARG001  -- the engine is ambient here: solve is the one door this example asks through
    """Ask each two-sided shape and pin what the one-sided reading answers."""
    # A marker on the right is data: a gap on the left consumes it as one
    # child, and a named gap answers a run that still holds the marker.
    assert len(list(solve((S.f, ...), S.f(seg(V.v))))) == 1
    open_run = solve((S.f, seg(V.u)), S.f(seg(V.v))).one().u
    assert open_run.alpha_eq(S.f(seg(V.v))[1:])

    # So a gap written on the right alone is matched literally, and an
    # ordinary child does not match it.
    assert list(solve((S.f, S.a, S.b), S.f(S.a, seg(V.v)))) == []

    # Those two readings are the whole story. The four shapes below are the
    # ones the last-position and linear-shallow calculi are for, and each
    # answers here as a one-sided match that fails.
    assert list(solve((S.f, S.a, S.b), S.f(S.a, S.b, seg(V.v)))) == []
    assert list(
        solve((S.f, (S.g, seg(V.x)), (S.h, seg(V.x))), S.f(S.g(seg(V.y)), S.h(S.b)))
    ) == []
    assert list(solve((S.f, seg(V.u), S.b), S.f(S.a, seg(V.v)))) == []
    assert list(
        solve((S.f, seg(V.u), (S.g, S.a)), S.f(S.g(S.b), seg(V.v)))
    ) == []

    # And the same cause turns the calculus's own trivial identity into a
    # refusal: `(f (:seg $u))` against itself has no mixed role at all, but the
    # unparsed right side puts the name in the classifier's ordinary list.
    refusal = None
    try:
        list(solve((S.f, seg(V.u)), S.f(seg(V.u))))
    except EngineError as error:
        refusal = error
    assert "mixed_roles" in str(refusal)


#: What this twin spends, its own tripwire, taken on the tree that
#: introduced it with the engine's .qlf set built, which is what the
#: gate leaves behind and what ships.
#: [measured: 8469, 8469, 8469 inferences; command=PYTHONPATH=extensions/python:extensions/python/tools $VENV/bin/python -c "from pathlib import Path; from twin_coverage import run_twin; print(run_twin(Path('extensions/python/examples/language-feature-examples/ch08-data/08-02-sequence-variables/04-the-two-sided-fragments.py').resolve()).cost)"; fixture=three independent fresh harness processes at loadavg 46; commit=a403e56b4f33828834823338eb1fc316e3fea2a4]
#: RE-PINNED 2026-09-07, 8469 to 8629 (+160), trunk's own movement since each
#: twin's pin was taken on the base its own branch had: twenty-two first-parent
#: steps between the 0.8.0 release re-pin and this tree, the prelude's move
#: into Prolog the largest of them at +39 to +115 a twin and -65,806 on the
#: error algebra, the live-views merge -45 on every twin that writes, the
#: catalog and get-type repairs +169 on the types chapter, and the rest SWI
#: clause-indexing layout as the boot image grew; this tree also stores the
#: compiled default space operand as &self rather than a (context-space) call
#: [measured 2026-09-07: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=WORKTREE].
BUDGET = 8629

#: OVERRUN 2026-09-07, 4500: it asks through `solve`, the pattern door, where
#: the example asks through `unify`, the one MeTTa form whose operands are both
#: syntax; the door costs 367 inferences an ask against the form's 259.
#: Measured 8629 against a ceiling of 4164; a MINIMAL twin of this example --
#: its own forms stored and asked through the structured door, nothing else --
#: costs 6467 against the ceiling's 4164, so no twin of it fits the band at all
#: [measured 2026-09-07: one fresh process per side; command=python
#: extensions/python/benchmarks/probes/twin_floor.py; commit=WORKTREE].
OVERRUN = 4500
