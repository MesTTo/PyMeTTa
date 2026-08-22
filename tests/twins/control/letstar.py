"""examples/control/letstar.metta in Python: sequential bindings.

Inside a compiled body `x = 1` IS a `let*` binding: the decorator folds a
statement list into nested bindings around what follows it, so the Python for
this file is three lines of ordinary function body.

It is written at the term door instead, and only because of the price:
`@m.define` costs 2,442 inferences for exactly that body against the example's
whole 1,824 and a ceiling of 2,006 (measured 2026-08-22, three fresh
processes). The decorator's fixed cost alone, 1,922 for a body of one line, is
already 105% of this example's total, so no compiled twin of a one-form
example can fit the band. Filed against P14.14.
"""

from petta import S, V

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "@m.define costs 2442 inferences here against the band's ceiling of 2006"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 742 to 595, -147 (-19.8%), by the twin contract
#: change: the `test` wrapper LEFT the engine for `assert`; the form stays a
#: term because `@m.define` costs 2,442 here against a ceiling of 2,006.
#: Measured min-of-3 over fresh processes with the MORK backend linked in,
#: which the artefact-free worktree omits and which moves a compiled twin by
#: about 10 inferences per definition; against the example's 1824 the ratio
#: is 0.3262. Prior: 742, the transliterated twin this replaces.
BUDGET = 595


def twin(m):
    """Bind two names in order, then add them."""
    # !(test (let* (($x 1) ($y 2)) (+ $x $y)) 3)
    assert m.eval(S["let*"](((V.x, 1), (V.y, 2)), V.x + V.y)) == [3]
