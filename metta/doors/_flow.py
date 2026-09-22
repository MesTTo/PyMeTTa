"""Purpose: quotient identity-copy constraints by proven mutual inclusion.

Guarantees: SCC members denote the same value set at a fixed point; directed
edges outside an SCC retain their direction [tested:
test_copy_components_preserve_the_least_fixed_point; commit=WORKTREE].
Owns resources: each CopyGraph owns its mutable edge and representative maps.
Guarded by: the owning CallGraph evaluates one worklist in one thread.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

type Slot = tuple[str, str]


def components[Node: (str, tuple[str, str])](graph: Mapping[Node, Iterable[Node]]) -> tuple[tuple[Node, ...], ...]:
    """Enumerate SCCs in O(V log V + E) time and O(V+E) space, sorting members."""
    # Kosaraju's reverse-postorder construction, as in NetworkX 3.6.1:
    # https://github.com/networkx/networkx/blob/7530809bfa1ea7ed6fdf918a4d1431488953cb1f/networkx/algorithms/components/strongly_connected.py
    edges = {name: tuple(targets) for name, targets in graph.items()}
    for targets in tuple(edges.values()):
        for target in targets:
            edges.setdefault(target, ())
    reverse: dict[Node, list[Node]] = {name: [] for name in edges}
    for name, targets in edges.items():
        for target in targets:
            reverse[target].append(name)
    seen: set[Node] = set()
    postorder: list[Node] = []
    for name in sorted(edges):
        if name in seen:
            continue
        seen.add(name)
        stack = [(name, iter(reverse[name]))]
        while stack:
            current, children = stack[-1]
            child = next(children, None)
            if child is None:
                postorder.append(current)
                stack.pop()
            elif child not in seen:
                seen.add(child)
                stack.append((child, iter(reverse[child])))
    seen.clear()
    result = []
    for name in reversed(postorder):
        if name in seen:
            continue
        members = []
        pending = [name]
        seen.add(name)
        while pending:
            current = pending.pop()
            members.append(current)
            for child in edges[current]:
                if child not in seen:
                    seen.add(child)
                    pending.append(child)
        result.append(tuple(sorted(members)))
    return tuple(result)


class CopyGraph:
    """Inclusion edges and the equivalence they prove, independent of call edges."""

    def __init__(self) -> None:
        self.parents: dict[Slot, Slot] = {}
        self.edges: dict[Slot, set[Slot]] = {}
        self.changed = False

    def representative(self, slot: Slot) -> Slot:
        """Find a cell with path compression; no recursion limit applies."""
        path = []
        while slot in self.parents:
            path.append(slot)
            slot = self.parents[slot]
        for member in path:
            self.parents[member] = slot
        return slot

    def add(self, source: Slot, target: Slot) -> None:
        """Record an identity inclusion, including before either cell has values."""
        source, target = self.representative(source), self.representative(target)
        if source != target:
            targets = self.edges.setdefault(source, set())
            if target not in targets:
                targets.add(target)
                self.changed = True

    def collapse(self) -> tuple[tuple[Slot, ...], ...]:
        """Return newly merged cells and retain the quotient's directed edges.

        Time: O(V log V + E). Space: O(V+E), V copy cells and E copy edges
        since the last quotient. Mutual subset inclusion proves equality; coincidentally
        equal current sets cannot supply an edge. SVF makes the same distinction:
        https://github.com/SVF-tools/SVF/blob/f3f095033ac117c9b4ab576410d2326807e6ee31/svf/lib/WPA/AndersenSFR.cpp#L35-L48
        """
        if not self.changed:
            return ()
        groups = tuple(group for group in components(self.edges) if len(group) > 1)
        for representative, *members in groups:
            for member in members:
                self.parents[member] = representative
        edges: dict[Slot, set[Slot]] = {}
        for source, targets in self.edges.items():
            representative = self.representative(source)
            destinations = {self.representative(target) for target in targets} - {representative}
            if destinations:
                edges.setdefault(representative, set()).update(destinations)
        self.edges = edges
        self.changed = False
        return groups
