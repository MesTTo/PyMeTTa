"""examples/spaces/spaces.metta in Python: writes a later match can see.

`matchtrickery` adds two atoms and matches them in one expression, and the
example's point is the ordering: `let*` binds both writes before the match
reads the space, so the match sees them.

The equation is written at the container door, one rung below `@m.define`, and
both halves of its body are why. No compiled body can spell the hyphen in
`add-atom`, because a free name there is resolved against the engine's registry
exactly as written. And the compiled `match(...)` reads its TEMPLATE with the
ordinary expression compiler, where the lowercase `bar` is a call to a function
that does not exist rather than the relation it is here (residue, P14.4).
Calling the definition, and collecting its answers, are ordinary Python.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 2220 to 1373, -847 (-38.2%), by the twin contract
#: change: `(test (collapse (matchtrickery)) ...)` became one `assert` over
#: `m.fn("matchtrickery").all()`, so the `test` and `collapse` wrappers left
#: the engine while the equation and the call it makes stayed exactly where
#: the example puts them. Against the example's 5261 the ratio is 0.2610.
#: Prior: 2220, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 1373


def twin(m):
    """Store one self-writing definition, then read what calling it answers."""
    here = S[m.space_name]

    # (= (matchtrickery)
    #    (let* (($t1 (add-atom &self (foo a)))
    #           ($t2 (add-atom &self (foo b))))
    #          (match &self (foo $1) (bar $1))))
    writes = (
        (V.first, S["add-atom"](here, S.foo(S.a))),  # rung: no compiled body spells a hyphen
        (V.second, S["add-atom"](here, S.foo(S.b))),  # rung: as above
    )
    m += equation(S.matchtrickery()).to(
        S["let*"](writes, S.match(here, S.foo(V.x), S.bar(V.x)))  # rung: the stored body of an equation the decorator cannot compile
    )

    assert m.fn("matchtrickery").all() == [S.bar(S.a), S.bar(S.b)]
