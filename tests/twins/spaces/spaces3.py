"""The Python twin of examples/spaces/spaces3.metta: what a pattern shape selects.

Four matches over the same two atoms differ only in the PATTERN: `($x)` selects
the one-element expression, a bare `$x` selects everything, and the template
decides what comes back.

A write is a statement, so the container protocol is its spelling: `space += atom`
IS `(add-atom &wuspace atom)`, and that form answers the unit, which is what the
WROTE group below says. Nothing is taken on trust by saying so: the five
assertions after the writes all read `&wuspace`, so a write that did not happen
fails five forms.
"""

from petta import S, V, expr

#: The answer group a write form contributes. `add-atom` answers the unit, and
#: the unit is what Python's own None means at this seam (§9d's concept map).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 4568 to 4090, -478 (-10.5%), by the P14 twin-style
#: rewrite, and the whole delta is the two writes: the `!(add-atom &wuspace
#: ...)` forms now go through the container door, `wuspace += atom`, so each
#: costs 239 inferences instead of translating and reducing a two-argument
#: (add-atom ...) call. The five assertions did not move; the same terms
#: spelled with named symbols and tuples measure identically, which sibling
#: files with no writes confirm by holding their figure exactly.
#: Prior: ADDED 2026-08-22 at 4568 by the wave-3 spaces baseline.
BUDGET = 4090


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    wuspace = m.space("&wuspace")
    here = S[wuspace.space_name]

    # !(add-atom &wuspace (wu))
    wuspace += S.wu()
    yield WROTE

    # !(add-atom &wuspace (wu 42))
    wuspace += (S.wu, 42)
    yield WROTE

    # A one-element pattern selects the one-element atom. The trailing comma is
    # Python's own way of saying "a tuple of one", and MeTTa's ($x) needs it.
    # !(test (collapse (match &wuspace ($1) ($1))) ((wu)))
    yield m.eval(
        S.test(S.collapse(S.match(here, (V.x,), (V.x,))), (S.wu(),))
    )

    # !(test (collapse (match &wuspace ($1) (hu $1))) ((hu wu)))
    yield m.eval(
        S.test(S.collapse(S.match(here, (V.x,), S.hu(V.x))), (S.hu(S.wu),))
    )

    # !(test (collapse (match &wuspace ($1) $1)) (wu))
    yield m.eval(S.test(S.collapse(S.match(here, (V.x,), V.x)), (S.wu,)))

    # A bare variable pattern is every atom, which is get-atoms by another name.
    # !(test (msort (collapse (match &wuspace $1 $1)))
    #        (msort (collapse (get-atoms &wuspace))))
    yield m.eval(
        S.test(
            S.msort(S.collapse(S.match(here, V.x, V.x))),
            S.msort(S.collapse(S["get-atoms"](here))),
        )
    )

    # !(test (msort (collapse (match &wuspace $1 (wu $1)))) ((wu (wu)) (wu (wu 42))))
    yield m.eval(
        S.test(
            S.msort(S.collapse(S.match(here, V.x, S.wu(V.x)))),
            (S.wu(S.wu()), S.wu(S.wu(42))),
        )
    )
