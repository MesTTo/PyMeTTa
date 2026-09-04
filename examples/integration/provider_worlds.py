"""Purpose: let a foreign provider receive bounds and commit immutable worlds.

``BoundedMatcher`` is a performance promise: a provider may honor ``limit``
only when its candidates are exact answers. ``Snapshotter`` and
``WorldCommitter`` are the read and atomic-write halves of reified worlds.
"""

from _common import check, done

from metta import Atom, MeTTa, S, V
from metta.foreign import SpaceProvider


class VersionedFacts(SpaceProvider):
    """An exact in-memory backend that records bounds and world commits."""

    def __init__(self, rows) -> None:
        """Start from a stable atom sequence."""
        self.rows = list(rows)
        self.limits = []
        self.commits = []

    def atoms(self):
        """Enumerate the current snapshot."""
        return iter(list(self.rows))

    def match(self, pattern: Atom, *, limit: int | None = None):
        """Yield exact matches, stopping at the caller's admitted bound."""
        self.limits.append(limit)
        matches = [row for row in self.rows if row.unify(pattern) is not None]
        yield from matches[:limit]

    def pushdown(self, _pattern: Atom) -> str:
        """Declare that every yielded candidate is an answer."""
        return "exact"

    def add(self, atom: Atom) -> None:
        """Append one ordinary write."""
        self.rows.append(atom)

    def remove(self, atom: Atom) -> bool:
        """Remove one occurrence when present."""
        if atom not in self.rows:
            return False
        self.rows.remove(atom)
        return True

    def snapshot(self) -> tuple[Atom, ...]:
        """Capture the immutable base used by a reified world."""
        return tuple(self.rows)

    def commit_world(
        self,
        base: tuple[Atom, ...],
        removed: list[Atom],
        added: list[Atom],
    ) -> None:
        """Land one base-relative multiset diff atomically."""
        if tuple(self.rows) != base:
            msg = "the provider changed after this world was reified"
            raise RuntimeError(msg)
        updated = list(self.rows)
        for atom in removed:
            updated.remove(atom)
        updated.extend(added)
        self.rows = updated
        self.commits.append((removed, added))


with MeTTa() as context:
    provider = VersionedFacts(S.item(number) for number in range(3))
    space = context.space(backing=provider)

    rows = space.match(S.item(V.number), limit=1)
    check("an exact provider receives the answer bound", len(rows), 1)
    check("the bounded matcher stopped at the requested count", provider.limits, [1])

    space.covers("writesState")
    world = space.reify()
    try:
        answers, successor = world.eval(S.add_atom(S["&self"], S.item(3)))
        try:
            check("world evaluation leaves the provider untouched", len(provider.rows), 3)
            check("the successor records the write", answers, [True])
            space.commit(successor)
        finally:
            successor.close()
    finally:
        world.close()

    check("WorldCommitter received one atomic diff", provider.commits, [([], [S.item(3)])])
    check("the committed world is now visible", provider.rows[-1], S.item(3))

done("provider_worlds")
