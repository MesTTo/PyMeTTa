"""examples/control/letext.metta in Python: `let` matches a pattern.

`let` binds by MATCHING a pattern against a value, not by naming a variable:
`($x (42 (if (== $x 2) 43 44)))` meets `(3 (42 $z))`, so `$x` takes 3 from the
left of the value and `$z` takes the still-unrun `(if (== 3 2) 43 44)` from the
right of the pattern. Variables on BOTH sides bind at once, and the body then
evaluates what `$z` holds, so `(+ 3 44)` is 47.

Python's assignment binds one way, into names, so nothing here is an
assignment. A compiled body refuses a tuple target outright, "a compiled body
binds plain names; destructuring and attribute assignment have no let* form",
and even a destructuring assignment would only carry the left-to-right half.
Filed as residue against P14.4.
"""

from petta import S, V

#: Why this twin sits below the top rung; see the module docstring.
RUNG = "a `let` whose pattern and value both carry variables has no assignment spelling"

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 1264 to 1114, -150 (-11.9%), by the twin contract
#: change: the `test` wrapper LEFT the engine for `assert`; the `let` stays a
#: term because its pattern and its value both carry variables. Measured min-
#: of-3 over fresh processes with the MORK backend linked in, which the
#: artefact-free worktree omits and which moves a compiled twin by about 10
#: inferences per definition; against the example's 2620 the ratio is 0.4252.
#: Prior: 1264, the transliterated twin this replaces.
BUDGET = 1114


def twin(m):
    """Bind in both directions at once, then use what was bound."""
    # !(test (let ($x (42 (if (== $x 2) 43 44))) (3 (42 $z)) (+ $x $z)) 47)
    assert m.eval(
        S.let(
            (V.x, (42, S["if"](V.x.eq(2), 43, 44))),
            (3, (42, V.z)),
            V.x + V.z,
        )
    ) == [47]
