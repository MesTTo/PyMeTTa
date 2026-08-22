"""examples/control/collapse.metta in Python: collapsing one answer.

`(1 2 3)` has no head to call, so it answers itself, and `collapse` gathers
that one answer into a one-element expression. The doubled parentheses of
`((1 2 3))` are the whole point of the file, and in Python they are a list
holding one atom: evaluating a term already answers the multiset, so
`collapse` needs no spelling of its own.
"""

from petta import expr

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 617 to 226, -391 (-63.4%), by the twin contract
#: change: the `test` wrapper and the `collapse` LEFT the engine entirely;
#: what is left is building the term and evaluating it, because calling
#: already answers the multiset a collapse gathers. Measured min-of-3 over
#: fresh processes with the MORK backend linked in, which the artefact-free
#: worktree omits and which moves a compiled twin by about 10 inferences per
#: definition; against the example's 1790 the ratio is 0.1263. Prior: 617,
#: the transliterated twin this replaces.
BUDGET = 226


def twin(m):
    """Evaluate a term nothing reduces, and count the answers it gives."""
    # !(test (collapse (1 2 3)) ((1 2 3)))
    assert m.eval(expr(1, 2, 3)) == [expr(1, 2, 3)]
