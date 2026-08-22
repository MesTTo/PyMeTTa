"""examples/control/if2.metta in Python: a symbol is not a variable.

`(is-var a)` asks about the ATOM `a`, so the answer is False and the else arm
runs. The then arm `(() (+ 1 1))` is an expression whose first element is the
empty expression, and Python's own empty tuple is that atom.

A compiled body would spell the whole form in Python, `((), 1 + 1) if is_var(x)
else 2 + 2`, except for two holes. `is-var` is hyphenated and a compiled body
reaches a function only by the name it can write; and the decorator costs more
than the lane allows here, 3,324 inferences for this body against the
example's whole 2,365 and a ceiling of 2,601 (measured 2026-08-22, three fresh
processes). Both are filed as residue, the second against P14.14.
"""

from petta import S

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "@m.define costs 3324 inferences here against the band's ceiling of 2601"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1187 to 1040, -147 (-12.4%), by the twin contract
#: change: the `test` wrapper LEFT the engine for `assert`; the form itself
#: stays a term because `@m.define` costs 3,324 here against a ceiling of
#: 2,601. Measured min-of-3 over fresh processes with the MORK backend linked
#: in, which the artefact-free worktree omits and which moves a compiled twin
#: by about 10 inferences per definition; against the example's 2365 the
#: ratio is 0.4397. Prior: 1187, the transliterated twin this replaces.
BUDGET = 1040


def twin(m):
    """Ask whether a symbol is a variable, and take the arm that answers."""
    # !(test (if (is-var a) (() (+ 1 1)) (+ 2 2)) 4)
    assert m.eval(S["if"](S["is-var"](S.a), ((), S["+"](1, 1)), S["+"](2, 2))) == [4]
