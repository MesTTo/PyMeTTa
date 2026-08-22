"""examples/libraries/he_evaluation.metta in Python: what evaluation looks like from here.

Four claims, and three of them dissolve into ordinary Python. Calling a defined
function IS `(eval (double 5))`; `kb.eval(term)` is `evalc`'s image to the
letter, since evalc's signature is exactly term plus space; and `chain`, which
executes one instruction, binds its result and runs the continuation, is
assignment followed by use of the name.

The fourth is `println!` mapped over six items. `println!` answers the UNIT
value, which is what the specification types it with, so the answer is six
units rather than six trues, and Python says the same thing with `print`, whose
return is None, the unit's Python spelling.
"""

from petta import S

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 13555 to 9487, -4068 (-30.01%), by the idiomatic
#: rewrite: the `chain` claim became an assignment and the `for-each-in-atom`
#: of `println!` became a comprehension over `print`, so two of the four
#: claims no longer reach the engine at all, and four `test` wrappers went
#: with them. Measured min-of-three with the MORK backend linked into this
#: worktree, which the earlier figure may not have been. Prior: 13555 was the
#: last figure for the generator twin that yielded `m.eval(S.test(...))` once
#: per runnable form.
BUDGET = 9487


def twin(m):
    """Evaluate a call, a term, a chain, and a print over six items."""
    m.eval(S["import!"](S["&self"], S.library(S.lib_he)))  # rung: import!'s target space is an ARGUMENT, and a space handle does not encode as one (the engine answers "expects a space"), so the name is written as the symbol its own door takes

    @m.define
    def double(x):
        return x + x

    assert double(5) == [10]
    assert m.eval(S["+"](5, 5)) == [10]

    # chain binds one instruction's result and runs the continuation, which is
    # what an assignment and the next statement already are.
    doubled = m.one(S["+"](2, 3))
    assert m.one(S["*"](doubled, 2)) == 10

    # Printing answers the unit value, once per item.
    printed = [print(item) for item in (1, 3, 5, 62, 2, 5)]
    assert printed == [None] * 6
