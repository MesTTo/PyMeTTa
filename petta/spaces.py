"""Purpose: space combinators on the public seam: union, readonly, mapped,
and overlay compose existing spaces into new ones with zero engine changes,
each an ordinary SpaceProvider, which is the point: the seam proves its
composability by having the combinators be users of it.
Guarantees:
  - union and readonly implement no write operation, so the engine's own
    capability refusal answers add-atom on them [tested
    test_union_refuses_writes_through_the_engine]
  - mapped presents only atoms unifying its inner shape, both directions
    derived from the one declaration [tested
    test_mapped_presents_and_writes_through_the_declaration]
  - overlay reads both layers and writes, removes, and clears the front
    only, ChainMap's own rule [tested test_overlay_routes_writes_to_front]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
from typing import Any

from .atoms import Atom, Expr, _to_atom, is_ground, substitute, unify
from .errors import PettaError
from .foreign import Matcher, SpaceProvider
from .structures import _canonical

__all__ = ["diff", "mapped", "overlay", "readonly", "union"]


class _Member:
    """One underlying space read (and optionally written) uniformly: a
    MeTTa handle uses its indexed query for candidates, a provider its
    own match or enumeration. Combinators compose members, so nothing
    below cares which kind it holds.
    """

    def __init__(self, target: Any) -> None:
        if isinstance(target, str):
            raise PettaError(
                f"a combinator takes a MeTTa handle or a SpaceProvider, not "
                f"the name {target!r}; a name alone carries no engine"
            )
        self.target = target
        self._is_space = hasattr(target, "space_name") and hasattr(target, "query")

    def atoms(self) -> Iterator[Atom]:
        return iter(self.target.atoms())

    def match(self, pattern: Atom) -> Iterator[Atom]:
        if self._is_space:
            rows = self.target.query(pattern)
            names = rows.columns
            for row in rows:
                yield substitute(pattern, dict(zip(names, row, strict=True)))
            return
        if isinstance(self.target, Matcher):
            yield from self.target.match(pattern)
            return
        yield from self.atoms()

    def add(self, *atoms: Atom) -> None:
        if self._is_space:
            self.target.add(*atoms)
            return
        for atom in atoms:
            self.target.add(atom)

    def remove(self, pattern: Atom) -> bool:
        return bool(self.target.remove(pattern))

    def clear(self) -> None:
        self.target.clear()

    def describe(self) -> str:
        if self._is_space:
            return str(self.target.space_name)
        return type(self.target).__name__


class _Union(SpaceProvider):
    """The read-only aggregate: rdflib's ReadOnlyGraphAggregate reading.
    match answers every member's candidates (over-approximation stays
    sound by the seam's own law), atoms chains, and no write operation
    exists, so the engine's capability refusal answers writes. The MeTTa
    reading: overlapping shapes answer as a nondeterministic union the
    way overlapping equations do; a union space is that, one level up.
    """

    def __init__(self, members: list[_Member]) -> None:
        self._members = members

    def atoms(self) -> Iterator[Atom]:
        for member in self._members:
            yield from member.atoms()

    def match(self, pattern: Atom) -> Iterator[Atom]:
        for member in self._members:
            yield from member.match(pattern)

    def __repr__(self) -> str:
        inside = ", ".join(member.describe() for member in self._members)
        return f"<union of {inside}>"


def union(*spaces: Any) -> _Union:
    """A set of spaces read as one, writes refused by capability.

        m.register_space(petta.spaces.union(kb, rules), "&all")
        m.run("!(match &all (edge $a $b) $b)")

    Every member's candidates answer; duplicates across members are
    answers twice, the multiset reading a union of multisets has.
    """
    if not spaces:
        raise PettaError("union needs at least one space")
    return _Union([_Member(space) for space in spaces])


class _ReadOnly(SpaceProvider):
    """The inner space with every write capability stripped: reads
    forward, and the absence of write methods makes the engine refuse
    add-atom with its standing capability error. declare_writes carries
    the policy vocabulary; this is the one-line spelling for handing a
    space to code that must not mutate it.
    """

    def __init__(self, member: _Member) -> None:
        self._member = member

    def atoms(self) -> Iterator[Atom]:
        return self._member.atoms()

    def match(self, pattern: Atom) -> Iterator[Atom]:
        return self._member.match(pattern)

    def __repr__(self) -> str:
        return f"<readonly {self._member.describe()}>"


def readonly(inner: Any) -> _ReadOnly:
    """The inner space, reads only; writes meet the capability refusal."""
    return _ReadOnly(_Member(inner))


class _Mapped(SpaceProvider):
    """A view of the inner space through one (bridge outer inner) pair:
    petta.tables' derivation with unification where tables emits WHERE.
    The outer shape is what this space presents; the inner shape is how
    the same fact is spelled underneath; the shared variables carry the
    values both ways.
    """

    def __init__(self, member: _Member, outer: Expr, inner: Expr) -> None:
        self._member = member
        self._outer = outer
        self._inner = inner

    def _inward(self, outer_atom: Atom) -> Atom | None:
        bindings = unify(self._outer, outer_atom)
        if bindings is None:
            return None
        return substitute(self._inner, bindings)

    def _outward(self, inner_atom: Atom) -> Atom | None:
        bindings = unify(self._inner, inner_atom)
        if bindings is None:
            return None
        return substitute(self._outer, bindings)

    def atoms(self) -> Iterator[Atom]:
        for atom in self._member.atoms():
            outward = self._outward(atom)
            if outward is not None:
                yield outward

    def match(self, pattern: Atom) -> Iterator[Atom]:
        inner_pattern = self._inward(pattern)
        if inner_pattern is None:
            # unify is one-way (shape side binds), so its failure proves
            # absence only for a GROUND pattern, where one-way and two-way
            # agree. A pattern with variables can still touch instances a
            # one-way walk refuses, (edge $x $x) against a shape carrying
            # literals for instance, so the sound side is enumeration and
            # the engine's own re-unification keeps the answers right.
            if not is_ground(pattern):
                yield from self.atoms()
            return
        for candidate in self._member.match(inner_pattern):
            outward = self._outward(candidate)
            if outward is not None:
                yield outward

    def add(self, atom: Atom) -> None:
        inward = self._inward(atom)
        if inward is None:
            raise PettaError(
                f"{atom} does not fit this view's shape {self._outer}; the "
                f"view admits only atoms the declaration maps"
            )
        self._member.add(inward)

    def remove(self, pattern: Atom) -> bool:
        inward = self._inward(pattern)
        if inward is None:
            return False
        return self._member.remove(inward)

    def __repr__(self) -> str:
        return f"<{self._outer} mapped onto {self._inner} in {self._member.describe()}>"


def mapped(inner: Any, declaration: Any) -> _Mapped:
    """A shape view over ANY space, from one declaration:

        view = petta.spaces.mapped(kb, "(bridge (edge $a $b) (triple $a linked-to $b))")

    presents the inner space's (triple ...) atoms as (edge ...) atoms,
    both directions derived from the pattern pair by unification, the
    tables bridge with WHERE replaced by unify. Renames, projections,
    and legacy-shape adapters stop being custom providers and become
    this one line. Adds map right-to-left; removal maps the pattern
    through; atoms the declaration does not map are invisible here and
    untouched there.
    """
    parsed = _to_atom(declaration)
    if (
        not isinstance(parsed, Expr)
        or len(parsed.children) != 3
        or str(parsed.children[0]) != "bridge"
        or not isinstance(parsed.children[1], Expr)
        or not isinstance(parsed.children[2], Expr)
    ):
        raise PettaError(
            f"a mapped declaration is (bridge <outer-shape> <inner-shape>), "
            f"got {parsed}"
        )
    outer, inner_shape = parsed.children[1], parsed.children[2]
    return _Mapped(_Member(inner), outer, inner_shape)


class _Overlay(SpaceProvider):
    """Reads both layers; writes, removals, and clears touch the front
    only, collections.ChainMap's own rule, stated loudly because for
    multisets silent routing would invent placement decisions. The back
    layer is never written, so removing an atom the back holds leaves
    it answering, exactly as deleting a ChainMap key from the first map
    leaves the second map's value visible.
    """

    def __init__(self, front: _Member, back: _Member) -> None:
        self._front = front
        self._back = back

    def atoms(self) -> Iterator[Atom]:
        yield from self._front.atoms()
        yield from self._back.atoms()

    def match(self, pattern: Atom) -> Iterator[Atom]:
        yield from self._front.match(pattern)
        yield from self._back.match(pattern)

    def add(self, atom: Atom) -> None:
        self._front.add(atom)

    def remove(self, pattern: Atom) -> bool:
        return self._front.remove(pattern)

    def clear(self) -> None:
        self._front.clear()

    def __repr__(self) -> str:
        return f"<overlay {self._front.describe()} over {self._back.describe()}>"


def overlay(front: Any, back: Any) -> _Overlay:
    """Both layers read as one; every write lands on front. The
    explicitly chosen form union() refuses to be: ChainMap semantics
    for spaces, deletes not forwarded to back.
    """
    return _Overlay(_Member(front), _Member(back))


def _diff_key(atom: Atom) -> str:
    """The multiset key: the alpha-canonical PRINTED form, digest()'s own
    equivalence, so (f $x) and (f $y) count as one atom and a stored
    unhashable ground value still keys.
    """
    return str(_canonical(atom))


def _surplus(these: list[Atom], those: list[Atom]) -> list[Atom]:
    remaining = Counter(_diff_key(atom) for atom in those)
    extras = []
    for atom in these:
        key = _diff_key(atom)
        if remaining[key]:
            remaining[key] -= 1
        else:
            extras.append(atom)
    return extras


def diff(a: Any, b: Any) -> tuple[list[Atom], list[Atom]]:
    """What digest() cannot say: HOW two spaces differ.

    Answers (only_in_a, only_in_b), the multiset difference over
    enumeration, so a space holding an atom twice against one holding it
    once differs by the one copy. Alpha-equivalent atoms count as the
    same atom, digest()'s own equivalence, and each side's extras come
    back in that side's enumeration order. Both arguments are anything
    the combinators accept: a MeTTa handle or a provider. Each side is
    enumerated exactly once, so a live space is compared at one moment.
    """
    a_atoms = list(_Member(a).atoms())
    b_atoms = list(_Member(b).atoms())
    return _surplus(a_atoms, b_atoms), _surplus(b_atoms, a_atoms)
