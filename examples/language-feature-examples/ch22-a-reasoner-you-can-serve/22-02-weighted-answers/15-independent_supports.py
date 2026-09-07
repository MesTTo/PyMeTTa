"""examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/15-independent_supports.metta in Python: the check every independence formula runs first.

`pln2-require-independent-supports` answers True or RAISES, so the refusals
read through `except` rather than through `catch` and `unify`: the ball's
own text carries the shared ID, and the context carries the remedy.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, lib
from metta.errors import MettaError

REMEDY = (
    "factor shared support in an owned reasoner with stable signed evidence "
    "IDs, then combine only disjoint residual supports"
)


def refused(call, argument):
    """The error one overlapping pair raises, or None where it held."""
    try:
        list(call(argument))
    except MettaError as failure:
        return failure
    return None


def twin(m):
    """Disjoint sets pass, nothing to compare passes, an overlap refuses."""
    m += lib.pln2
    independent = m.fn["pln2-require-independent-supports"]

    assert independent(((S.sensor_a,), (S.sensor_b,))) == [True]
    assert independent(((S.sensor_a, S.sensor_b), (S.sensor_c,))) == [True]

    # Nothing to compare is independent too, which keeps the check total.
    assert independent(()) == [True]
    assert independent(((S.sensor_a,),)) == [True]
    assert independent(((S.sensor_a,), ())) == [True]

    # One shared ID is a refusal, and it names the ID rather than the pair.
    first = refused(independent, ((S.sensor_a,), (S.sensor_a,)))
    assert "the evidence ID 'sensor-a'" in str(first)
    second = refused(independent, ((S.sensor_a, S.sensor_b), (S.sensor_b,)))
    assert "the evidence ID 'sensor-b'" in str(second)

    # And the refusal ends in the remedy, because the library's position is
    # that a formula assuming independence either gets disjoint evidence or
    # says so.
    assert REMEDY in str(refused(independent, ((S.s,), (S.s,))))


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 56825 inferences, 1.0096x the example's 56283; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
#: RE-PINNED 2026-09-08, 56825 to 56820 (-5), metta_substitute_self/3 probes
#: the term for the text &self before walking it, one C write and one C
#: substring probe, where the twins-lane merge's one-equation door (08f6f4df)
#: walked every natively added equation in a named space unconditionally, so
#: every twin that adds or defines an equation in a named space drops by about
#: that equation's size in inferences; the same probe now guards the reader's
#: per-form door (record_translated_from/4), the deferred door's fallback
#: (stored_equation_source/4), a batch's arriving equations
#: (mark_or_translate_equation/5) and the removal probe (remove_equation/6),
#: where the walk is new and skipped for a term that never says &self, and a
#: twin that only removes or re-adds such equations pays the two-inference
#: probe per door crossing instead. Every twin here re-reads its budget on this
#: tree, minimum of three fresh processes [measured 2026-09-08: min-of-3 serial
#: fresh processes; command=python extensions/python/tools/twin_coverage.py
#: --repin; commit=856434d7c1d381b3f3d7cbbd008f46c0d41b61aa].
#: RE-PINNED 2026-09-08, 56820 to 56808 (-12), the evaluation-fuel scope marker
#: is a trailed write (fix/every-intermittent-root-caused, f6e05ca9):
#: `$metta_fuel_scope` is written open with b_setval/2 at scope open and read
#: with b_getval/2 where nb_current/2 used to answer, so an abandoned scope
#: closes itself when an exception unwinds the trail and the cleanup is the
#: fast ordinary exit, and every runnable form pays fewer inferences per scope;
#: a twin drops by about the count of its runnables, and the engine bench reads
#: evaluate and translate 1642 lower each on the same tree. Every twin here re-
#: reads its budget on the merged tree, minimum of three fresh processes
#: [measured 2026-09-08: min-of-3 serial fresh processes; command=python
#: extensions/python/tools/twin_coverage.py --repin; commit=3fc65f02ce807c359f1a52026f950f345da2a9af].
BUDGET = 56808
