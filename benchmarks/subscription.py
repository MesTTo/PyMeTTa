"""Purpose: price the subscription write path at the size where the dispatch
strategy is the cost. Every subscription is on ONE space and every write
consults them, which is the many-subscriptions case MatchIndex's own
docstring describes.
Guarantees:
  - the measured window holds writes only; the space, the subscriptions and
    the atoms are built before it [tested
    test_subscription_dispatch_case_measures_writes_only]
Owns:
  - subscription_dispatch_case owns one space and SUBSCRIPTIONS standing
    queries until close_subscription_case releases them [tested
    test_subscription_dispatch_case_measures_writes_only]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from petta import MeTTa, S, V, ground

SUBSCRIPTIONS = 1_000
WRITES = 200


def subscription_dispatch_case(subscriptions: int = SUBSCRIPTIONS, writes: int = WRITES):
    """A space watched by many standing queries, and the writes to make.

    One subscription matches each write and the rest are filtered out, which
    is the shape a dispatch strategy is judged on: the scan pays for every
    non-match, the tree does not.
    """
    space = MeTTa().space()
    delivered = [0]

    def count(_event) -> None:
        delivered[0] += 1

    standing = [
        space.subscribe(S.topic(S[f"k{index}"], V.payload), count)
        for index in range(subscriptions)
    ]
    atoms = [
        S.topic(S[f"k{index % subscriptions}"], ground(index)) for index in range(writes)
    ]

    def run() -> int:
        for atom in atoms:
            space.add(atom)
        return len(atoms)

    return space, standing, delivered, run


def close_subscription_case(state) -> None:
    space, standing, _delivered, _run = state
    for subscription in standing:
        subscription.cancel()
    space.drop()
