"""Purpose: examples/basics/and_or.metta in Python: the boolean connectives.

`(and true false)` is False, so `(or ... true)` is True and the original's
`if` takes its first branch. The connectives are the engine's here and Python
cannot spell them in a compiled body three ways over: `and` and `or` are
Python KEYWORDS, so no body can name them the way `basics/xor` names `xor`;
`&` and `|` build the terms at the term door but are refused inside a body;
and Python's own `and` in a body lowers to `py-truthy` short-circuits rather
than to MeTTa's connectives. So the engine reduces the connectives and
Python's conditional expression picks the branch, which is what a conditional
expression is for.

One operator does reach here. `|` builds `(or ... True)` because its left
operand is a built term; `TRUE & FALSE` would not, because two GROUND
operands make a Python operator that value's own arithmetic, and it answers
Python's `False` before the engine sees anything.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 989 to 738, -251 (-25.4%), by the twin contract
#: change: the `test` wrapper and the `m.eval` around it left the engine
#: for Python's own `assert` and conditional expression, so all that is
#: left in the engine is reducing `(or (and True False) True)`. Against the
#: example's 2113 the ratio is 0.3493 [measured 2026-08-22 min-of-3,
#: `twin_coverage.py --measure`]. The old figure priced a different
#: program.
BUDGET = 738


def twin(m):
    """Reduce the connectives in the engine, then choose in Python."""
    # (or (and true false) true)
    holds = m.one(S["and"](TRUE, FALSE) | TRUE)
    assert (1 if holds else 2) == 1
