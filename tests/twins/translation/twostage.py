"""Purpose: spell the two-stage definition-order example in pure Python.

Assumes:
  - f is stored before g while h is stored after it
    [source: examples/translation/twostage.metta lines 1-9; commit=WORKTREE]
Guarantees:
  - both early and late references reduce through g to 42
    [measured: twin completed; command=python bindings/python/tools/twin_coverage.py --measure --rounds 1 examples/translation/twostage.metta; fixture=fresh isolated process; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S, equation

#: Successful costs from two complete concurrent ten-round observations
#: The next complete lane falsified the first envelope at 3118, so this pin was
#: explicitly widened only after that finding; seven later complete lanes stayed
#: inside it
#: [measured: 3118..3158 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=WORKTREE].
BUDGET = {
    "minimum": 3118,
    "maximum": 3158,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def twin(m):
    """Install the three nullary equations in their original order."""
    m += equation(S.f()).to(S.g())
    m += equation(S.g()).to(42)
    m += equation(S.h()).to(S.g())

    assert m.eval(S.f()) == [42]
    assert m.eval(S.h()) == [42]
