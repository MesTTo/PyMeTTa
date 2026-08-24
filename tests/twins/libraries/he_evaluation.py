"""examples/libraries/he_evaluation.metta in Python: what evaluation looks like from here.

Four claims, and three of them dissolve into ordinary Python. Calling a defined
function IS `(eval (double 5))`; `kb.eval(term)` is `evalc`'s image to the
letter, since evalc's signature is exactly term plus space; and `chain`, which
executes one instruction, binds its result and runs the continuation, which is
assignment followed by use of the name.

The terms those two doors evaluate are built with Python's own operators over a
GROUNDED operand: `G(5) + 5` stages `(+ 5 5)` where `5 + 5` would compute 10
in Python and reach no engine at all. That lift is what leaves something for
`eval` to do.

The fourth is `println!` mapped over six items. `println!` answers the UNIT
value, which is what the specification types it with, so the answer is six
units rather than six trues, and Python says the same thing with `print`, whose
return is None, the unit's Python spelling.
"""

from metta import G, S

#: A PLACEHOLDER, not a measurement. The twins wave re-authored this file and
#: the integrator prices every budget in one pass on the merged tree, so a
#: figure measured here would pin a tree that does not ship
#: [assumed: this twin's inference cost is unmeasured on this branch;
#: commit=1e264c186c531e69acde5ad03ff6a79210626df4].
BUDGET = 1


def twin(m):
    """Evaluate a call, a term, a chain, and a print over six items."""
    m.fn["import!"](m, S.library(S["lib_he"]))

    @m.define
    def double(x):
        # (= (double $x) (+ $x $x))
        return x + x

    assert double(5) == [10]
    assert m.eval(G(5) + 5) == [10]

    # chain binds one instruction's result and runs the continuation, which is
    # what an assignment and the next statement already are.
    summed = m.answers(G(2) + 3).one()
    assert m.answers(G(summed) * 2).one() == 10

    # Printing answers the unit value, once per item.
    printed = [print(item) for item in (1, 3, 5, 62, 2, 5)]
    assert printed == [None] * 6
