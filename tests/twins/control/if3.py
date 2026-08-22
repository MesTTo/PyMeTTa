"""examples/control/if3.metta in Python: an unbound variable IS one.

The companion of if2: there the argument was a symbol and `is-var` answered
False, here it is `$A` and the then arm runs, which is itself an `if`.

Written at the term door for if2's second reason: `@m.define` costs 3,197
inferences for this body against the example's whole 2,317 and a ceiling of
2,548 (measured 2026-08-22, three fresh processes), so the Python spelling of
a one-form example cannot fit the band that prices it. Filed against P14.14.
"""

from petta import S, V, val

#: MeTTa's boolean ATOMS, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and these are answers.
TRUE = val(value=True)

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "@m.define costs 3197 inferences here against the band's ceiling of 2548"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 955 to 806, -149 (-15.6%), by the twin contract
#: change: the `test` wrapper LEFT the engine for `assert`; the form stays a
#: term for if2's reason, 3,197 against a ceiling of 2,548. Measured min-of-3
#: over fresh processes with the MORK backend linked in, which the artefact-
#: free worktree omits and which moves a compiled twin by about 10 inferences
#: per definition; against the example's 2317 the ratio is 0.3479. Prior:
#: 955, the transliterated twin this replaces.
BUDGET = 806


def twin(m):
    """Ask whether a variable is a variable, and take the arm that answers."""
    # !(test (if (is-var $A) (if True 42 lol) (+ 2 2)) 42)
    assert m.eval(
        S["if"](S["is-var"](V.A), S["if"](TRUE, 42, S.lol), S["+"](2, 2))
    ) == [42]
