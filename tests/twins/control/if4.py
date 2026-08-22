"""examples/control/if4.metta in Python: an `if` inside a condition.

A condition is an ordinary expression, so an `if` sits there as happily as a
comparison does, and this file's whole subject is that nesting.

Written at the term door for the reason if2 and if3 give: `@m.define` costs
3,197 inferences for a body of this shape against the example's whole 2,667
and a ceiling of 2,933 (measured 2026-08-22, three fresh processes). Filed
against P14.14.
"""

from petta import S, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE, FALSE = val(value=True), val(value=False)

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "@m.define costs 3197 inferences here against the band's ceiling of 2933"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1153 to 1004, -149 (-12.9%), by the twin contract
#: change: the `test` wrapper LEFT the engine for `assert`; the form stays a
#: term for if2's reason, 3,197 against a ceiling of 2,933. Measured min-of-3
#: over fresh processes with the MORK backend linked in, which the artefact-
#: free worktree omits and which moves a compiled twin by about 10 inferences
#: per definition; against the example's 2667 the ratio is 0.3765. Prior:
#: 1153, the transliterated twin this replaces.
BUDGET = 1004


def twin(m):
    """Decide a condition with an `if`, then take an arm with another."""
    # !(test (if (if (== 42 42) True False) (if True 42 lol) (+ 2 2)) 42)
    assert m.eval(
        S["if"](
            S["if"](S["=="](42, 42), TRUE, FALSE),
            S["if"](TRUE, 42, S.lol),
            S["+"](2, 2),
        )
    ) == [42]
