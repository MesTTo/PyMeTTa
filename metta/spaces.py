"""Purpose: space views and combinators on the public seam. Object views,
union, readonly, mapped, and overlay are ordinary SpaceProvider instances;
the same engine route therefore matches a live object or composes existing
spaces without hardcoded integration paths.
Guarantees:
  - view presents mappings and zero-based sequences through one kv relation
    and sets as members, reading the Python object afresh for every query
    [tested: test_view_is_a_live_queryable_space; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - union and readonly implement no write operation, so the engine's own
    capability refusal answers add-atom on them [tested
    test_union_refuses_writes_through_the_engine]
  - mapped presents only atoms unifying its inner shape, both directions
    derived from the one declaration [tested
    test_mapped_presents_and_writes_through_the_declaration]
  - overlay reads both layers and writes, removes, and clears the front
    only, ChainMap's own rule [tested test_overlay_routes_writes_to_front]
  - object_view reads live fields, joins with stored atoms through union, and
    turns an added py-field atom into setattr [tested:
    test_a_query_joins_stored_atoms_with_live_object_fields;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - provider queries and bridge declarations retain directional pattern
    matching after public ``unify`` becomes symmetric [tested:
    test_mapped_repeated_variable_pattern_stays_sound;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - union, readonly, mapped, and overlay snapshot each member once; a live
    member without the explicit snapshot protocol refuses by member name
    [tested: test_reify_refuses_and_names_a_live_composite_member;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from collections.abc import Set as AbstractSet
from typing import Any

from ._object_fields import field_names
from .atoms import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _decode,
    _encode,
    _is_ground,
    _match,
    _to_atom,
    ground,
    substitute,
)
from .errors import MettaError
from .foreign import Matcher, Snapshotter, SpaceProvider
from .structures import _canonical

__all__ = [
    "ObjectView",
    "diff",
    "mapped",
    "object_view",
    "overlay",
    "readonly",
    "union",
    "view",
]


class _LiveDataView(SpaceProvider):
    """A dict, set, or sequence read through its current Python contents."""

    _relation = Symbol("kv")

    def __init__(self, obj: Mapping[Any, Any] | AbstractSet[Any] | Sequence[Any]) -> None:
        self.object = obj
        self._members = isinstance(obj, AbstractSet)

    @staticmethod
    def _key_atom(key: Any) -> Atom:
        return Symbol(key) if isinstance(key, str) else _encode(key)

    def _entries(self) -> Iterator[tuple[Any, Any]]:
        if isinstance(self.object, Mapping):
            yield from self.object.items()
        elif isinstance(self.object, Sequence):
            yield from enumerate(self.object)

    def _kv_atom(self, key: Any, value: Any) -> Expression:
        return Expression([self._relation, self._key_atom(key), _encode(value)])

    def atoms(self) -> Iterator[Atom]:
        """Enumerate the object's current transparent image."""
        if self._members:
            yield from (_encode(member) for member in self.object)
            return
        yield from (self._kv_atom(key, value) for key, value in self._entries())

    def match(self, pattern: Atom) -> Iterator[Atom]:
        """Narrow bound keys by lookup and reverse-bound values by a scan."""
        if self._members:
            yield from self._match_member(pattern)
            return
        if (
            not isinstance(pattern, Expression)
            or len(pattern.children) != 3
            or pattern.children[0] != self._relation
        ):
            return
        key_pattern, _value_pattern = pattern.children[1:]
        for key, value in self._matching_entries(key_pattern):
            candidate = self._kv_atom(key, value)
            if _match(pattern, candidate) is not None:
                yield candidate

    def _matching_entries(self, key_pattern: Atom) -> Iterator[tuple[Any, Any]]:
        if isinstance(key_pattern, Variable):
            yield from self._entries()
            return
        if isinstance(self.object, Mapping):
            keys: tuple[Any, ...]
            if isinstance(key_pattern, Symbol):
                keys = (key_pattern, key_pattern.name)
            elif isinstance(key_pattern, Grounded) and hasattr(
                key_pattern, "value"
            ):
                keys = (_decode(key_pattern),)
            else:
                keys = (key_pattern,)
            seen: set[int] = set()
            for key in keys:
                try:
                    value = self.object[key]
                except (KeyError, TypeError):
                    continue
                identity = id(key)
                if identity not in seen:
                    seen.add(identity)
                    yield key, value
            return
        if (
            isinstance(key_pattern, Grounded)
            and hasattr(key_pattern, "value")
            and isinstance(self.object, Sequence)
        ):
            index = _decode(key_pattern)
            if type(index) is int and 0 <= index < len(self.object):
                yield index, self.object[index]

    def _match_member(self, pattern: Atom) -> Iterator[Atom]:
        if _is_ground(pattern):
            member = _decode(pattern)
            try:
                present = member in self.object
            except TypeError:
                present = False
            if present:
                candidate = _encode(member)
                if _match(pattern, candidate) is not None:
                    yield candidate
            return
        for candidate in self.atoms():
            if _match(pattern, candidate) is not None:
                yield candidate


def view(obj: Any):
    """Return an attached live space over a dict, set, or sequence.

    Dictionaries image as ``(kv key value)``. Sequences use that same relation
    with zero-based integer keys, matching Python's indices; a value-bound
    query therefore answers every matching index. Sets image as raw members.
    External mutations are visible on the next query.
    """
    supported = isinstance(obj, (Mapping, AbstractSet)) or (
        isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray))
    )
    if not supported:
        msg = "view expects a dict, set, or non-string sequence"
        raise TypeError(msg)
    from ._space import MeTTa, Space  # noqa: PLC0415 -- the satellite stays lazy at root import

    return MeTTa(Space()).space(backing=_LiveDataView(obj))


class ObjectView(SpaceProvider):
    """One live Python object presented as ``(py-field obj name value)``.

    Enumeration names the object's public fields. A bound field may also be
    served through ``getattr``, which lets an object with ``__getattr__``
    answer the mode it actually supports without pretending it can enumerate.
    Adding the same atom shape writes the value with ``setattr``.
    """

    def __init__(self, obj: Any, relation: str | Symbol = "py-field") -> None:
        """Wrap one live object, presenting its fields under *relation*."""
        if isinstance(relation, str):
            if not relation:
                msg = "an object view relation name cannot be empty"
                raise MettaError(msg)
            relation = Symbol(relation)
        elif not isinstance(relation, Symbol):
            msg = "an object view relation is a symbol or its string name"
            raise TypeError(msg)
        self.object = obj
        self.relation = relation
        self._root = ground(obj)

    def atoms(self) -> Iterator[Atom]:
        """Yield one field atom per readable public field of the object."""
        for name in field_names(self.object):
            candidate = self._field_atom(name)
            if candidate is not None:
                yield candidate

    def match(self, pattern: Atom) -> Iterator[Atom]:
        """Yield candidate field atoms for *pattern*, narrowed by root and field name."""
        parts = self._parts(pattern)
        if parts is None:
            return
        root, name_atom, _value = parts
        if not isinstance(root, Variable) and root != self._root:
            return
        if isinstance(name_atom, Variable):
            names = field_names(self.object)
        elif isinstance(name_atom, Symbol):
            names = [name_atom.name]
        elif isinstance(name_atom, Grounded) and isinstance(
            getattr(name_atom, "value", None), str
        ):
            names = [name_atom.value]
        else:
            return
        for name in names:
            candidate = self._field_atom(name)
            if candidate is not None:
                yield candidate

    def add(self, atom: Atom) -> None:
        """Write one ``(relation <object> <field> <value>)`` atom via ``setattr``."""
        parts = self._parts(atom)
        if parts is None:
            msg = (
                f"an object view writes ({self.relation} <object> <field> <value>); "
                f"got {atom}"
            )
            raise MettaError(msg)
        root, name_atom, value_atom = parts
        if root != self._root:
            msg = "an object view writes only the object it presents"
            raise MettaError(msg)
        if isinstance(name_atom, Symbol):
            name = name_atom.name
        elif isinstance(name_atom, Grounded) and isinstance(
            getattr(name_atom, "value", None), str
        ):
            name = name_atom.value
        else:
            msg = "an object view write needs one ground field name"
            raise MettaError(msg)
        setattr(self.object, name, _decode(value_atom))

    def _parts(self, atom: Atom) -> tuple[Atom, Atom, Atom] | None:
        if (
            not isinstance(atom, Expression)
            or len(atom.children) != 4
            or atom.children[0] != self.relation
        ):
            return None
        return atom.children[1], atom.children[2], atom.children[3]

    def _field_atom(self, name: str) -> Expression | None:
        try:
            value = getattr(self.object, name)
        except AttributeError:
            return None
        return Expression([self.relation, self._root, Symbol(name), _encode(value)])

    def __repr__(self) -> str:
        """Return the debug label naming the viewed type and the relation."""
        return f"<object view of {type(self.object).__name__} as {self.relation}>"


def object_view(obj: Any, *, relation: str | Symbol = "py-field") -> ObjectView:
    """Present one object as a live, writable provider.

    Compose it with stored facts through ``spaces.union(stored, view)`` and
    register the result like any other provider. Register the view itself
    when MeTTa should write its fields through ``add-atom``.
    """
    return ObjectView(obj, relation)


class _Member:
    """One underlying space read (and optionally written) uniformly: a
    MeTTa handle uses its indexed query for candidates, a provider its
    own match or enumeration. Combinators compose members, so nothing
    below cares which kind it holds.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, target: Any) -> None:
        if isinstance(target, str):
            msg = (
                f"a combinator takes a MeTTa handle or a SpaceProvider, not "
                f"the name {target!r}; a name alone carries no engine"
            )
            raise MettaError(
                msg
            )
        self.target = target
        self._is_space = hasattr(target, "_rt") and hasattr(target, "_space")

    def atoms(self) -> Iterator[Atom]:
        return iter(self.target.atoms())

    def match(self, pattern: Atom) -> Iterator[Atom]:
        if self._is_space:
            rows = self.target.match(pattern)
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

    def snapshot(self) -> tuple[Atom, ...]:
        """Capture this member once, never via a live enumeration fallback."""
        source = self.target
        if self._is_space:
            backing = getattr(self.target, "_backing", None)
            if backing is None:
                return tuple(self.target.atoms())
            source = backing
        if not isinstance(source, Snapshotter):
            msg = (
                f"cannot reify {self.describe()}: member "
                f"{type(source).__name__} is live and provides no snapshot()"
            )
            raise MettaError(msg)
        captured = tuple(source.snapshot())
        if any(not isinstance(atom, Atom) for atom in captured):
            msg = f"{self.describe()}.snapshot() returned a non-Atom member"
            raise MettaError(msg)
        return captured

    def describe(self) -> str:
        if self._is_space:
            return str(self.target.name)
        return type(self.target).__name__


class _Union(SpaceProvider):
    """The read-only aggregate: rdflib's ReadOnlyGraphAggregate reading.
    match answers every member's candidates (over-approximation stays
    sound by the seam's own law), atoms chains, and no write operation
    exists, so the engine's capability refusal answers writes. The MeTTa
    reading: overlapping shapes answer as a nondeterministic union the
    way overlapping equations do; a union space is that, one level up.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, members: list[_Member]) -> None:
        self._members = members

    def atoms(self) -> Iterator[Atom]:
        for member in self._members:
            yield from member.atoms()

    def match(self, pattern: Atom) -> Iterator[Atom]:
        for member in self._members:
            yield from member.match(pattern)

    def snapshot(self) -> tuple[Atom, ...]:
        """One immutable concatenation of one snapshot per member."""
        return tuple(atom for member in self._members for atom in member.snapshot())

    def __repr__(self) -> str:
        inside = ", ".join(member.describe() for member in self._members)
        return f"<union of {inside}>"


def union(*spaces: Any) -> _Union:
    """A set of spaces read as one, writes refused by capability.

        m._register_space(metta.spaces.union(kb, rules), "&all")
        m.run("!(match &all (edge $a $b) $b)")

    Every member's candidates answer; duplicates across members are
    answers twice, the multiset reading a union of multisets has.
    """
    if not spaces:
        msg = "union needs at least one space"
        raise MettaError(msg)
    return _Union([_Member(space) for space in spaces])


class _ReadOnly(SpaceProvider):
    """The inner space with every write capability stripped: reads
    forward, and the absence of write methods makes the engine refuse
    add-atom with its standing capability error. ``writes`` carries
    the policy vocabulary; this is the one-line spelling for handing a
    space to code that must not mutate it.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, member: _Member) -> None:
        self._member = member

    def atoms(self) -> Iterator[Atom]:
        return self._member.atoms()

    def match(self, pattern: Atom) -> Iterator[Atom]:
        return self._member.match(pattern)

    def snapshot(self) -> tuple[Atom, ...]:
        """Snapshot the same inner contents while retaining no write door."""
        return self._member.snapshot()

    def __repr__(self) -> str:
        return f"<readonly {self._member.describe()}>"


def readonly(inner: Any) -> _ReadOnly:
    """The inner space, reads only; writes meet the capability refusal."""
    return _ReadOnly(_Member(inner))


def _repeats_a_variable(atom: Atom) -> bool:
    """Whether any named variable occurs more than once in the pattern."""
    seen: set[str] = set()
    stack: list[Atom] = [atom]
    while stack:
        term = stack.pop()
        if isinstance(term, Variable):
            if term.name != "_" and term.name in seen:
                return True
            seen.add(term.name)
        elif isinstance(term, Expression):
            stack.extend(term.children)
    return False


class _Mapped(SpaceProvider):
    """A view of the inner space through one (bridge outer inner) pair:
    metta.tables' derivation with unification where tables emits WHERE.
    The outer shape is what this space presents; the inner shape is how
    the same fact is spelled underneath; the shared variables carry the
    values both ways.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, member: _Member, outer: Expression, inner: Expression) -> None:
        self._member = member
        self._outer = outer
        self._inner = inner

    def _inward(self, outer_atom: Atom) -> Atom | None:
        bindings = _match(self._outer, outer_atom)
        if bindings is None:
            return None
        return substitute(self._inner, bindings)

    def _outward(self, inner_atom: Atom) -> Atom | None:
        bindings = _match(self._inner, inner_atom)
        if bindings is None:
            return None
        return substitute(self._outer, bindings)

    def atoms(self) -> Iterator[Atom]:
        for atom in self._member.atoms():
            outward = self._outward(atom)
            if outward is not None:
                yield outward

    def match(self, pattern: Atom) -> Iterator[Atom]:
        # _match is one-way (shape side binds), so a translated pattern is
        # exact only when one-way and two-way agree: for a GROUND pattern,
        # and for a linear one, where no binding can constrain another. A
        # repeated variable makes the one-way walk over-commit, so
        # ($x (f $y) $x) translated narrowly and the view under-answered
        # its own store; that class takes the enumeration side, and the
        # engine's re-unification keeps the answers right
        # [tested: test_mapped_passes_the_conformance_kit].
        inner_pattern = self._inward(pattern)
        if inner_pattern is not None and (
            _is_ground(pattern) or not _repeats_a_variable(pattern)
        ):
            for candidate in self._member.match(inner_pattern):
                outward = self._outward(candidate)
                if outward is not None:
                    yield outward
            return
        if not _is_ground(pattern):
            yield from self.atoms()

    def snapshot(self) -> tuple[Atom, ...]:
        """Map one immutable inner capture into this view's outward shape."""
        outward = (self._outward(atom) for atom in self._member.snapshot())
        return tuple(atom for atom in outward if atom is not None)

    def add(self, atom: Atom) -> None:
        inward = self._inward(atom)
        if inward is None:
            msg = (
                f"{atom} does not fit this view's shape {self._outer}; the "
                f"view admits only atoms the declaration maps"
            )
            raise MettaError(
                msg
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

        view = metta.spaces.mapped(kb, "(bridge (edge $a $b) (triple $a linked-to $b))")

    presents the inner space's (triple ...) atoms as (edge ...) atoms,
    both directions derived from the pattern pair by unification, the
    tables bridge with WHERE replaced by unify. Renames, projections,
    and legacy-shape adapters stop being custom providers and become
    this one line. Adds map right-to-left; removal maps the pattern
    through; atoms the declaration does not map are invisible here and
    untouched there.
    """  # noqa: D415  -- the first line deliberately introduces the indented example that follows
    parsed = _to_atom(declaration)
    if (
        not isinstance(parsed, Expression)
        or len(parsed.children) != 3
        or str(parsed.children[0]) != "bridge"
        or not isinstance(parsed.children[1], Expression)
        or not isinstance(parsed.children[2], Expression)
    ):
        msg = (
            f"a mapped declaration is (bridge <outer-shape> <inner-shape>), "
            f"got {parsed}"
        )
        raise MettaError(
            msg
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
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, front: _Member, back: _Member) -> None:
        self._front = front
        self._back = back

    def atoms(self) -> Iterator[Atom]:
        yield from self._front.atoms()
        yield from self._back.atoms()

    def match(self, pattern: Atom) -> Iterator[Atom]:
        yield from self._front.match(pattern)
        yield from self._back.match(pattern)

    def snapshot(self) -> tuple[Atom, ...]:
        """Capture front then back, preserving overlay enumeration order."""
        return (*self._front.snapshot(), *self._back.snapshot())

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
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _Overlay(_Member(front), _Member(back))


def _diff_key(atom: Atom) -> str:
    """The multiset key: the alpha-canonical PRINTED form, digest()'s own
    equivalence, so (f $x) and (f $y) count as one atom and a stored
    unhashable ground value still keys.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
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
