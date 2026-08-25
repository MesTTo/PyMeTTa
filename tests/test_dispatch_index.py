"""Purpose: subscription dispatch routed through the discrimination tree this
package ships, held to the linear scan it replaces on BOTH delivery and
order.
Guarantees:
  - the scan oracle uses directional pattern matching, so a variable in a
    stored event does not make a literal watching pattern match [tested:
    test_dispatch_through_the_index_delivers_the_same_subscribers_in_the_same_order;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from metta import S, V, ground
from metta.atoms import _match


def _scan(registered, space, atom, action="add"):
    """The strategy this replaces, written out: every registration on this
    space, in the order it was made, one unify each, deliver the matches.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    return [
        name
        for name, subscription, pattern, on, watched in registered
        if subscription._active
        and watched is space
        and on in ("both", action)
        and _match(pattern, atom) is not None
    ]


def test_dispatch_through_the_index_delivers_the_same_subscribers_in_the_same_order(
    metta,
):
    """A reordering is a behaviour change even when every subscriber fires.

    Delivery is synchronous and inside the write, so a subscriber can write
    back, and two subscribers on one atom compose in the order they were
    registered. That order is part of the contract, which is why this
    asserts the delivered SEQUENCE against the scan's rather than the
    delivered set.

    The registrations are chosen to break a tree that is merely plausible:

      - patterns that differ only in whether a position is a variable, so
        the retrieval walk reaches them through different edges. The walk
        pushes the skip edge after the exact one and pops, so it visits the
        variable pattern FIRST, which is the wrong way round;
      - a cancel followed by a fresh subscribe, which is what makes an
        entry id derived from the live entry COUNT collide with a
        surviving one. Measured 2026-08-19 on the shipped MatchIndex:
        registration order ['b', 'c'] came back ['c', 'b'];
      - two identical patterns, since a discrimination tree stores them at
        one node and their relative order is then the leaf list's;
      - a subscription that matches nothing, one on another space, and one
        watching removals only, so the filters compose;
      - a NON-ground atom, which a tree walk cannot read literally.
    """
    space = metta._new_space()
    other = metta._new_space()
    delivered: list[str] = []
    registered: list[tuple] = []

    def watch(name, target, pattern, on="add"):
        subscription = target.subscribe(
            pattern, lambda _event, name=name: delivered.append(name), on=on
        )
        registered.append((name, subscription, pattern, on, target))
        return subscription

    try:
        watch("exact-first", space, S.topic(S.k, S.v))
        doomed = watch("cancelled", space, S.topic(V.a, V.b))
        watch("loose-after", space, S.topic(V.a, V.b))
        watch("same-as-loose", space, S.topic(V.c, V.d))
        watch("never-matches", space, S.other(V.a))
        watch("removals-only", space, S.topic(V.a, V.b), on="remove")
        watch("wrong-space", other, S.topic(V.a, V.b))
        watch("nested", space, S.topic(S.k, V.b))

        # The cancel-then-subscribe interleaving.
        doomed.cancel()
        watch("after-cancel", space, S.topic(V.a, V.b))
        watch("after-cancel-exact", space, S.topic(S.k, S.v))

        probes = [
            S.topic(S.k, S.v),
            S.topic(S.k, S.other),
            S.topic(ground(1), ground(2.5)),
            S.topic(S.k, V.free),
            S.other(S.k),
            S.unrelated(S.k, S.v, S.w),
        ]
        for probe in probes:
            delivered.clear()
            space.add(probe)
            assert delivered == _scan(registered, space, probe), (
                f"add {probe}: delivered {delivered}, the scan says "
                f"{_scan(registered, space, probe)}"
            )

        for probe in probes:
            # Put it back first: the engine's removal is retractall, so a
            # removal that matches nothing fires no hook at all and there
            # would be no dispatch to compare.
            space.add(probe)
            delivered.clear()
            space.remove(probe)
            assert delivered == _scan(registered, space, probe, "remove"), (
                f"remove {probe}: delivered {delivered}, the scan says "
                f"{_scan(registered, space, probe, 'remove')}"
            )

        # Every registration that should ever fire did fire at least once,
        # so the comparison above is not two empty lists agreeing.
        delivered.clear()
        space.add(S.topic(S.k, S.v))
        assert delivered == [
            "exact-first",
            "loose-after",
            "same-as-loose",
            "nested",
            "after-cancel",
            "after-cancel-exact",
        ]
    finally:
        for _name, subscription, _pattern, _on, _target in registered:
            if subscription._active:
                subscription.cancel()
        other.drop()
        space.drop()
