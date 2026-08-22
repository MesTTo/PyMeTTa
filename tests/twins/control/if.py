"""examples/control/if.metta in Python: the three-argument `if`.

Both arms are expressions, `(3 4)` and `(5 6)`, and a Python tuple is one.
The condition is false, so the answer is the second arm.

Inside a compiled body Python's own conditional expression IS this form:
`(3, 4) if 1 > 2 else (5, 6)` lowers to `(if (> 1 2) (3 4) (5 6))` arm for
arm. That is not what this file writes, and the reason is a price rather than
a missing lowering. Measured 2026-08-22 over three fresh processes,
`@m.define` costs 2,769 inferences for a two-arm conditional before the call
is made, against this whole example's 2,092 and the lane's ceiling of 2,301,
so the Python spelling of a one-form example cannot fit the band that prices
it. The term door costs 654. The measurement is filed as residue against
P14.14, which owns the budget law.
"""

from petta import S, expr

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "@m.define costs 2769 inferences here against the band's ceiling of 2301"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 887 to 654, -233 (-26.3%), by the twin contract
#: change: the `test` wrapper LEFT the engine for `assert`; the form stays a
#: term because `@m.define` costs 2,769 here against a ceiling of 2,301.
#: Measured min-of-3 over fresh processes with the MORK backend linked in,
#: which the artefact-free worktree omits and which moves a compiled twin by
#: about 10 inferences per definition; against the example's 2092 the ratio
#: is 0.3126. Prior: 887, the transliterated twin this replaces.
BUDGET = 654


def twin(m):
    """Ask a false question and read the arm it takes."""
    # !(test (if (> 1 2) (3 4) (5 6)) (5 6))
    assert m.eval(S["if"](S[">"](1, 2), (3, 4), (5, 6))) == [expr(5, 6)]
