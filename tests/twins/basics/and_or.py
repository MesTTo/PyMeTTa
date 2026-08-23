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

`m.answers(term).one()` is the cardinality door: exactly one answer, decoded
to the Python bool the conditional expression then reads.

One operator does reach here. `|` builds `(or ... True)` because its left
operand is a built term; `TRUE & FALSE` would not, because two GROUND
operands make a Python operator that value's own arithmetic, and it answers
Python's `False` before the engine sees anything.
Guarantees:
  - TRUE, FALSE, UNIT, and HERE used here are package values rather
    than local reconstructions [tested: test_the_canonical_atoms_are_public_values;
    commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import FALSE, TRUE, S

#: Inferences this twin spends, its own tripwire.
#: PLACEHOLDER for the twins wave: every budget in the corpus is 1 here and
#: the integrator's single re-pin pass prices them all on the merged tree, so
#: a figure measured in this worktree would price a tree that never ships
#: [assumed: unmeasured here, deliberately; commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
BUDGET = 1


def twin(m):
    """Reduce the connectives in the engine, then choose in Python."""
    # (or (and true false) true)
    #
    # COST, recorded because the lane's band reports it and it is the
    # library's to fix, not this twin's: the first answer view a process
    # creates costs about 4,700 inferences to set up its held evaluation, and
    # every one after it about 90. This file asks exactly one question, so it
    # pays the whole setup for it and lands at 5,446 against the example's
    # 2,103. `m.eval` answers the same thing for 738, which is what the file
    # used to do; the cardinality door is the better spelling and the setup is
    # what should get cheaper [measured 2026-08-23 on this worktree;
    # commit=4df40a9de00bbc7fb9c55715a5d802512d6f7dc4].
    holds = m.answers(S["and"](TRUE, FALSE) | TRUE).one()
    assert (1 if holds else 2) == 1
