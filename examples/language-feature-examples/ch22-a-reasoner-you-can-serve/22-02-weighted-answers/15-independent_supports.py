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
BUDGET = 56825
