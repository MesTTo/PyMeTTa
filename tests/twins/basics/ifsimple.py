"""examples/basics/ifsimple.metta in Python: `if` with no else branch.

MeTTa's two-argument `if` answers nothing when its condition is false, and
Python's conditional expression cannot mean that, because it always has an
else. What does mean it is a GENERATOR: a compiled body that yields nothing
prunes its branch, so `def keep(c, v): if c: yield v` says exactly this form
and `keep(False, 42)` answers `[]`.

That spelling is not what this file uses, and the reason is a measurement
rather than a taste. The original defines nothing and costs 1308 inferences
for its one form, while the twin that says the two-argument `if` in Python
costs 3289, because a decorated definition pays a per-name admission before
the first call: two and a half times the original, and far outside the band
ceiling of 1439 [measured 2026-08-22 min-of-3, this twin written both ways].
An example that
defines nothing cannot afford a definition, so the form is built at the term
door instead, and the residue table records that against P14.14, the row that
owns the band.
"""

from petta import S, val

#: MeTTa's boolean ATOM, which is what `True` means inside a term. Named
#: rather than written inline because a bare boolean in an argument list
#: reads as a Python flag, and this is an answer.
TRUE = val(value=True)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 373 to 224, -149 (-39.9%), by the twin contract
#: change: the `test` wrapper left the engine for `assert`, so the twin
#: asks the engine one question, `(if True 42)`. The Python spelling of
#: that form is a compiled generator and costs 3,275, which is why this
#: file stays at the term door. Against the example's 1308 the ratio is
#: 0.1713 [measured 2026-08-22 min-of-3, `twin_coverage.py --measure`]. The
#: old figure priced a different program.
BUDGET = 224


def twin(m):
    """Answer under a condition that holds."""
    assert m.eval(S["if"](TRUE, 42)) == [42]  # rung: MeTTa's two-argument if
