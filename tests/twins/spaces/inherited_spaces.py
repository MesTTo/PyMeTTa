"""The Python twin of examples/spaces/inherited_spaces.metta: child-first reads, front-only writes.

A child space reads through to its parent, so one conjunction joins a parent fact
to a child fact and same-shaped facts answer child first. Writes never reach an
ancestor, and the count sees only the writable front store.

Every write is the container protocol, `space += fact`, and both handles are
ordinary Python variables. The CREATION stays a term, because `new-space` answers
the NAME it created, `&family-child`, while `m.new_space(inherits=parent)`
answers a handle over a name the engine picked: a symbol is not a variable, so
those two answers are not alpha-equal. The residue files the missing door, a
NAMED inheriting space, against P14.10.
"""

from petta import S, V, expr

#: The answer group a write form contributes: `add-atom` answers the unit,
#: which is what Python's own None means at this seam (§9d).
WROTE = (expr(),)

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 6327 to 4780, -1547 (-24.5%), by the P14 twin-style
#: rewrite, and the whole delta is the six writes: each moved from evaluating an
#: (add-atom ...) term to `space += fact`, 258 a write, inside the 239-to-311
#: band this folder measures across six files. The creation is
#: an unchanged term and the six assertions are the same terms spelled with
#: named symbols and tuples.
#: Prior: ADDED 2026-08-22 at 6327 by the wave-3 spaces baseline.
BUDGET = 4780


def twin(m):
    """One answer group per runnable form of the original, in source order.

    A `test` form answers `(True)` and prints `is X, should Y. ✅`;
    every other form says its own answer in the comment above it.
    """
    parent = m.space("&family-parent")
    at_parent = S[parent.space_name]

    # !(add-atom &family-parent (edge a b))
    parent += (S.edge, S.a, S.b)
    yield WROTE
    # !(add-atom &family-parent (parent-only kept))
    parent += (S["parent-only"], S.kept)
    yield WROTE
    # !(add-atom &family-parent (layer parent))
    parent += (S.layer, S.parent)
    yield WROTE

    # !(new-space &family-child (inherits &family-parent))
    yield m.eval(
        S["new-space"](S["&family-child"], S.inherits(at_parent))
    )
    child = m.space("&family-child")
    at_child = S[child.space_name]

    # !(add-atom &family-child (edge b c))
    child += (S.edge, S.b, S.c)
    yield WROTE
    # !(add-atom &family-child (child-only local))
    child += (S["child-only"], S.local)
    yield WROTE
    # !(add-atom &family-child (layer child))
    child += (S.layer, S.child)
    yield WROTE

    # One conjunction joins a parent fact to a child fact, because each link is
    # matched through the whole read chain.
    # !(test (collapse (match &family-child (, (edge $x $y) (edge $y $z)) ($x $z)))
    #        ((a c)))
    yield m.eval(
        S.test(
            S.collapse(
                S.match(
                    at_child,
                    S[","](S.edge(V.x, V.y), S.edge(V.y, V.z)),
                    (V.x, V.z),
                )
            ),
            ((S.a, S.c),),
        )
    )

    # Same-shaped facts pin child-first reads.
    # !(test (collapse (match &family-child (layer $x) $x)) (child parent))
    yield m.eval(
        S.test(
            S.collapse(S.match(at_child, S.layer(V.x), V.x)),
            (S.child, S.parent),
        )
    )

    # The capacity/count boundary sees only the writable front store, which is
    # also what len(child) answers through the protocol door.
    # !(test (space-atom-count &family-child) 3)
    yield m.eval(S.test(S["space-atom-count"](at_child), 3))

    # Writes never mutate an ancestor.
    # !(test (collapse (match &family-parent (parent-only $x) $x)) (kept))
    yield m.eval(
        S.test(
            S.collapse(S.match(at_parent, S["parent-only"](V.x), V.x)),
            (S.kept,),
        )
    )
    # !(test (collapse (match &family-child (parent-only $x) $x)) (kept))
    yield m.eval(
        S.test(
            S.collapse(S.match(at_child, S["parent-only"](V.x), V.x)),
            (S.kept,),
        )
    )
    # !(test (collapse (match &family-parent (child-only $x) $x)) ())
    yield m.eval(
        S.test(
            S.collapse(S.match(at_parent, S["child-only"](V.x), V.x)), ()
        )
    )
