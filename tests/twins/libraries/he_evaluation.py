"""examples/libraries/he_evaluation.metta in Python: what evaluation looks like from here.

Four claims, and three of them dissolve into ordinary Python. Calling a defined
function IS `(eval (double 5))`; `kb.eval(term)` is `evalc`'s image to the
letter, since evalc's signature is exactly term plus space; and `chain`, which
executes one instruction, binds its result and runs the continuation, which is
assignment followed by use of the name.

The fourth is `println!` mapped over six items. `println!` answers the UNIT
value, which is what the specification types it with, so the answer is six
units rather than six trues, and Python says the same thing with `print`, whose
return is None, the unit's Python spelling.
"""

from petta import S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=bf25e468a4b2ec6fb0c4666e4f841fbd8e2a5ccf].
BUDGET = 1


def twin(m):
    """Evaluate a call, a term, a chain, and a print over six items."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    @m.define
    def double(x):
        return x + x

    assert double(5) == [10]
    assert m.eval(S["+"](5, 5)) == [10]

    # chain binds one instruction's result and runs the continuation, which is
    # what an assignment and the next statement already are.
    doubled = m.answers(S["+"](2, 3)).one()
    assert m.answers(S["*"](doubled, 2)).one() == 10

    # Printing answers the unit value, once per item.
    printed = [print(item) for item in (1, 3, 5, 62, 2, 5)]
    assert printed == [None] * 6
