"""Purpose: spell the two-stage definition-order example in pure Python.

Assumes:
  - f is stored before g while h is stored after it
    [source: examples/translation/twostage.metta lines 1-9; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Guarantees:
  - both early and late references reduce through g to 42
    [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/twostage.metta; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import S, equation

#: Inferences this twin spends, its own tripwire. PLACEHOLDER rather than a
#: measurement: the twins wave prices the whole corpus in one re-pin pass on
#: the merged tree, and a number measured in this worktree would pin a cost
#: the merge moves [assumed 2026-08-23: unpriced placeholder, re-pinned by the
#: integrator; commit=b5991d9d4c20f3459fae529e13e0d26331b82ee2].
BUDGET = 1


def twin(m):
    """Install the three nullary equations in their original order."""
    m += equation(S.f()).to(S.g())
    m += equation(S.g()).to(42)
    m += equation(S.h()).to(S.g())

    assert m.eval(S.f()) == [42]
    assert m.eval(S.h()) == [42]
