"""examples/spaces/matchsingle.metta in Python: two ways to take one match.

`(a b)` and `(a c)` both match, and both definitions answer only the first: one
cuts after the match, one wraps it in `once`.

Both equations are written at the container door, and the reason is the same
for each. A compiled body resolves a free name against the engine's FUNCTION
REGISTRY, and neither `cut` nor `once` is in it: both are forms the translator
handles, so `is_function` answers False and a body naming either is refused.
The compiled `match(...)` is blocked independently, because it takes its space
as a literal `"&name"` and these definitions take it as a PARAMETER (residue,
P14.4). The facts above them are ordinary tuples, and calling the definitions
is `m.fn(name).all(...)`, the door for a function that may answer more than
once.
"""

from petta import S, V, equation

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 3764 to 3120, -644 (-17.1%), by the twin contract
#: change: two `(test (collapse ...) ...)` terms became two `assert`s over
#: `.all()`, so the `test` and `collapse` wrappers left the engine and the two
#: equations and the two calls over them are what is left. Against the
#: example's 8575 the ratio is 0.3638.
#: Prior: 3764, pinned 2026-08-22 by the P14 twin-style rewrite and
#: measured under the previous contract, where twin(m) was a generator the
#: lane consumed form by form.
BUDGET = 3120


def twin(m):
    """Store two matching facts, then take one match two ways."""
    here = S[m.space_name]

    m += (S.a, S.b)
    m += (S.a, S.c)

    # (= (match-single-via-cut $space $pattern $outPattern)
    #    (let* (($x (match $space $pattern $outPattern))
    #           ($temp (cut)))
    #          $x))
    m += equation(S["match-single-via-cut"](V.space, V.pattern, V.out)).to(
        S["let*"](  # rung: a definition whose SPACE is a parameter, and `cut` is not a registry function
            (
                (V.found, S.match(V.space, V.pattern, V.out)),  # rung: as above
                (V.stop, S.cut()),
            ),
            V.found,
        )
    )

    # (= (match-single-via-once $space $pattern $outPattern)
    #    (once (match $space $pattern $outPattern)))
    m += equation(S["match-single-via-once"](V.space, V.pattern, V.out)).to(
        S.once(S.match(V.space, V.pattern, V.out))  # rung: as above, with `once` in place of `cut`
    )

    assert m.fn("match-single-via-cut").all(here, S.a(V.x), S.a(V.x)) == [S.a(S.b)]
    assert m.fn("match-single-via-once").all(here, S.a(V.x), S.a(V.x)) == [S.a(S.b)]
