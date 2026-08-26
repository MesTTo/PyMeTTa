"""Purpose: data structures with MeTTa's semantics at Python speed, built on
the boundary-free atom kernel (unify, alpha_eq, variables, order_key) and
never touching the engine: importable and usable without janus. PatternMap
answers "which entries apply to this atom", MatchIndex answers "which of
many registered patterns match it" sublinearly, and AlphaSet holds atoms
modulo variable renaming.
Assumes:
  - metta.atoms._match is the private directional primitive every lookup
    here wants: stored patterns are the pattern side and probes are the atom
    side [source: bindings/python/metta/atoms.py:_match; commit=6917bef7ca902671999eafcae3a7a86db8f69723]
Guarantees:
  - PatternMap's ground keys behave exactly like dict keys, the no-tax
    rule [tested test_patternmap_ground_keys_are_dict_keys]
  - MatchIndex.matches agrees with brute-force unification over every
    registered pattern, keeping integer and float atoms apart and NaN atoms
    together the way the engine's matcher does
    [tested test_matchindex_agrees_with_brute_force,
    test_matchindex_matches_grounded_numbers_by_unification]
  - MatchIndex.matches answers in REGISTRATION order whatever order the
    tree walk reached the entries in, and a remove does not disturb it
    [measured 2026-08-19: register a, b; remove a; register c; the answer
    was c before b] [tested
    test_dispatch_through_the_index_delivers_the_same_subscribers_in_the_same_order]
  - MatchIndex indexes Handle atoms by identity without reading the payload
    slot that Handle deliberately leaves unset
    [tested test_matchindex_indexes_handles_without_unwrapping_them;
    commit=WORKTREE]
  - AlphaSet membership is alpha_eq membership [tested
    test_alphaset_is_alpha_membership]
  - LiveView holds exactly what the space holds for its pattern, through
    adds and through removals whose event cannot say which occurrence left
    [tested test_liveview_mirrors_the_space]
Decides:
  - source text is NOT parsed here, because parsing needs the engine and
    this module's contract is engine-freedom; parse() first, or build
    atoms with S/V/Expression
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Iterator, MutableMapping, MutableSet
from operator import itemgetter
from typing import Any, Self

from .atoms import (
    Atom,
    Expression,
    Grounded,
    Symbol,
    Variable,
    _encode,
    _is_ground,
    _match,
    _variables,
    substitute,
)
from .errors import PettaError

__all__ = [
    "AlphaSet",
    "ClosureView",
    "LiveView",
    "MatchIndex",
    "PatternMap",
    "TabledMap",
]


def _as_atom(value: Any) -> Atom:
    """Encode without parsing: engine-freedom is this module's contract,
    so source text must be parsed by the caller.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    if isinstance(value, Atom):
        return value
    if isinstance(value, str):
        msg = (
            f"metta.structures never parses source text ({value!r}), because "
            f"parsing needs the engine and this module runs without one; "
            f"metta.parse() it first, or build the atom with S/V/Expression"
        )
        raise TypeError(
            msg
        )
    return _encode(value)


def _canonical(atom: Atom) -> Atom:
    """The atom with variables renamed to their first-appearance index,
    so two alpha-equivalent atoms canonicalize identically and ordinary
    hashing becomes alpha-invariant hashing.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    names = _variables(atom)
    if not names:
        return atom
    return substitute(
        atom, {name: Variable(f"_alpha{index}") for index, name in enumerate(names)}
    )


class PatternMap(MutableMapping):
    """A MutableMapping whose keys are atoms and whose point is the
    question "which entries apply to this atom?".

    Ground keys hash exactly like dict keys, the no-tax rule: getting,
    setting, and deleting a ground key is one dict operation. Pattern
    keys (keys carrying variables) land in head/arity buckets, and
    matching(atom) probes only the buckets the atom could touch,
    answering every (key, value) whose key unifies with it. The mapping
    protocol itself stays exact: pm[k] answers the entry stored under
    that very key (alpha-equal for pattern keys), never a unification.

        routes = PatternMap()
        routes[S.route(S.home)] = home_handler          # ground: dict speed
        routes[S.route(V.anything)] = fallback_handler  # pattern: bucketed
        [v for _, v in routes.matching(S.route(S.home))]
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_buckets", "_ground", "_patterns")

    def __init__(self, items: Any = (), /) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self._ground: dict[Atom, Any] = {}
        # Pattern entries keyed by their alpha-canonical form; buckets
        # index canonical keys by (head name or None, arity) plus the
        # any-bucket for bare-variable keys.
        self._patterns: dict[Atom, tuple[Atom, Any]] = {}
        self._buckets: dict[tuple[str | None, int] | None, set[Atom]] = {}
        update = dict(items) if not isinstance(items, dict) else items
        for key, value in update.items():
            self[key] = value

    @staticmethod
    def _bucket_of(key: Atom) -> tuple[str | None, int] | None:
        if isinstance(key, Expression) and key.children:
            head = key.children[0]
            name = head.name if isinstance(head, Symbol) else None
            return (name, len(key.children))
        return None  # a bare variable key matches anything

    def __setitem__(self, key: Any, value: Any) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        atom = _as_atom(key)
        if _is_ground(atom):
            self._ground[atom] = value
            return
        canonical = _canonical(atom)
        self._patterns[canonical] = (atom, value)
        self._buckets.setdefault(self._bucket_of(atom), set()).add(canonical)

    def __getitem__(self, key: Any) -> Any:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        atom = _as_atom(key)
        if _is_ground(atom):
            return self._ground[atom]
        entry = self._patterns.get(_canonical(atom))
        if entry is None:
            raise KeyError(atom)
        return entry[1]

    def __delitem__(self, key: Any) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        atom = _as_atom(key)
        if _is_ground(atom):
            del self._ground[atom]
            return
        canonical = _canonical(atom)
        entry = self._patterns.pop(canonical, None)
        if entry is None:
            raise KeyError(atom)
        bucket = self._buckets.get(self._bucket_of(entry[0]))
        if bucket is not None:
            bucket.discard(canonical)

    def __iter__(self) -> Iterator[Atom]:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        yield from self._ground
        for stored, _ in self._patterns.values():
            yield stored

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return len(self._ground) + len(self._patterns)

    def matching(self, atom: Any) -> Iterator[tuple[Atom, Any]]:
        """Every (key, value) whose KEY unifies with the atom: the
        dispatch question. A ground probe costs one dict hit plus the
        buckets its head and arity could touch; a probe carrying
        variables consults every pattern entry, since a variable probe
        can reach any bucket, and ground entries it unifies with.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        probe = _as_atom(atom)
        if _is_ground(probe):
            value = self._ground.get(probe, _MISSING)
            if value is not _MISSING:
                yield (probe, value)
            candidates: set[Atom] = set()
            for bucket_key in self._probe_buckets(probe):
                candidates |= self._buckets.get(bucket_key, set())
            for canonical in candidates:
                stored, value = self._patterns[canonical]
                if _match(stored, probe) is not None:
                    yield (stored, value)
            return
        for key, value in self._ground.items():
            if _match(probe, key) is not None:
                yield (key, value)
        for stored, value in self._patterns.values():
            if _mutually_unifiable(stored, probe):
                yield (stored, value)

    @staticmethod
    def _probe_buckets(probe: Atom) -> Iterator[tuple[str | None, int] | None]:
        if isinstance(probe, Expression) and probe.children:
            head = probe.children[0]
            if isinstance(head, Symbol):
                yield (head.name, len(probe.children))
            yield (None, len(probe.children))
        yield None

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return (
            f"PatternMap({len(self._ground)} ground, "
            f"{len(self._patterns)} pattern entries)"
        )


_MISSING = object()


def _mutually_unifiable(left: Atom, right: Atom) -> bool:
    """Whether two patterns can meet: one-way in both directions is a
    sound over-approximation of two-way unifiability for the entries a
    matching() probe with variables should answer, and the caller's own
    unify against the answered key settles the rest.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    return _match(left, right) is not None or _match(right, left) is not None


class MatchIndex:
    """Many registered patterns, one incoming atom, "which patterns match
    it?" answered sublinearly: pub/sub topic matching, rule dispatch,
    feature targeting, webhook routing.

    An imperfect discrimination tree, the term-indexing structure theorem
    provers use at millions-of-terms scale, over the atom kernel: each
    pattern flattens to a preorder token path with variables as skip
    edges, retrieval walks the ground atom's own tokens following exact
    and skip edges at once, and the candidates verify with unify, which
    is also what makes nonlinear patterns ((f $x $x)) exact.

        inbox = MatchIndex()
        inbox.add(S.order(V.id, S.express), rush_handler)
        [value for _, value in inbox.matches(S.order(ground(7), S.express))]
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_entries", "_next", "_root", "_size")

    def __init__(self) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self._root: dict = {}
        # Keyed by a counter that only ever goes UP, which is what makes the
        # key both unique and an ordering. Keying on (id(atom), live count)
        # was neither: the count goes back DOWN on remove, so a later
        # registration takes a number a survivor already holds, and the two
        # then sort by whichever the tree walk reached first. Measured
        # 2026-08-19: register a, b; remove a; register c; matches() answers
        # c before b. id() alone is no help either, since CPython reuses an
        # address as soon as the object at it is freed.
        self._entries: dict[int, tuple[Atom, Any]] = {}
        self._next = 0
        self._size = 0

    @staticmethod
    def _tokens(atom: Atom) -> list:
        """Preorder tokens; a variable is one skip token whatever it
        would bind.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        out: list = []
        stack = [atom]
        while stack:
            node = stack.pop()
            if isinstance(node, Variable):
                out.append("*")
            elif isinstance(node, Expression):
                out.append(("open", len(node.children)))
                stack.extend(reversed(node.children))
            elif isinstance(node, Symbol):
                out.append(("sym", node.name))
            else:
                # Handle is a Grounded species with no payload slot. Its
                # concrete species supplies identity equality and hashing,
                # so keep the handle itself as the discrimination token.
                value = getattr(node, "value", node) if isinstance(node, Grounded) else node
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    # Numeric atoms share one token kind because the kernel's
                    # equality is by numeric value: 0 and 0.0 must reach the
                    # same edge. Python gives equal int/float values equal
                    # hashes, while NaN remains unequal and is rejected by
                    # the final unify check just like the brute-force path.
                    out.append(("val", "number", value))
                    continue
                try:
                    hash(value)
                except TypeError:
                    out.append(("obj", id(value)))
                else:
                    out.append(("val", type(value).__name__, value))
        return out

    def add(self, pattern: Any, value: Any = None) -> None:
        """Register a pattern with a value (a handler, a topic, an id)."""
        atom = _as_atom(pattern)
        node = self._root
        for token in self._tokens(atom):
            node = node.setdefault(token, {})
        entry_id = self._next
        node.setdefault("$leaves", []).append(entry_id)
        self._entries[entry_id] = (atom, value)
        self._next += 1
        self._size += 1

    def remove(self, pattern: Any, value: Any = None) -> bool:
        """Remove one registration matching (pattern, value) exactly;
        answers whether one existed.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        atom = _as_atom(pattern)
        node = self._root
        for token in self._tokens(atom):
            step = node.get(token)
            if step is None:
                return False
            node = step
        for entry_id in list(node.get("$leaves", [])):
            stored, stored_value = self._entries[entry_id]
            if stored == atom and stored_value == value:
                node["$leaves"].remove(entry_id)
                del self._entries[entry_id]
                self._size -= 1
                return True
        return False

    def matches(self, atom: Any) -> Iterator[tuple[Atom, Any]]:
        """Every registered (pattern, value) whose pattern matches the
        ground atom, in REGISTRATION order, whatever order the tree walk
        reached them in. The tree answers candidates; unify confirms, so
        nonlinearity is exact.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        probe = _as_atom(atom)
        if not _is_ground(probe):
            # The tree's walk reads probe tokens literally, so a probe
            # variable would need every edge followed; brute force is the
            # honest spelling of that, and stays exact through unify.
            entries = sorted(self._entries.items(), key=itemgetter(0))
            for _, (stored, value) in entries:
                if _mutually_unifiable(stored, probe):
                    yield (stored, value)
            return
        tokens = self._tokens(probe)
        skips = self._skip_table(tokens)
        found: list[tuple[int, tuple[Atom, Any]]] = []
        stack = [(self._root, 0)]
        while stack:
            node, position = stack.pop()
            if position == len(tokens):
                for entry_id in node.get("$leaves", []):
                    entry = self._entries[entry_id]
                    if _match(entry[0], probe) is not None:
                        found.append((entry_id, entry))
                continue
            token = tokens[position]
            exact = node.get(token)
            if exact is not None:
                stack.append((exact, position + 1))
            starred = node.get("*")
            if starred is not None:
                stack.append((starred, skips[position]))
        for _, entry in sorted(found, key=itemgetter(0)):
            yield entry

    @staticmethod
    def _skip_table(tokens: list) -> list[int]:
        """For each position, the position just past that whole subterm,
        which is where a variable edge lands.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        skips = [0] * len(tokens)
        for position in range(len(tokens) - 1, -1, -1):
            token = tokens[position]
            if isinstance(token, tuple) and token[0] == "open":
                landing = position + 1
                for _ in range(token[1]):
                    landing = skips[landing]
                skips[position] = landing
            else:
                skips[position] = position + 1
        return skips

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self._size

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return f"MatchIndex({self._size} patterns)"


class AlphaSet(MutableSet):
    """A set of atoms modulo variable renaming: a rule or pattern store
    that must not hold the same rule twice under renamed variables.
    Membership, addition, and discard all read through the canonical
    form, so (f $x $x) and (f $y $y) are one element and (f $x $y) is
    another.

        rules = AlphaSet([parse("(= (inc $x) (+ $x 1))")])
        parse("(= (inc $n) (+ $n 1))") in rules     # True
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    __slots__ = ("_members",)

    def __init__(self, items: Any = (), /) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self._members: dict[Atom, Atom] = {}
        for item in items:
            self.add(item)

    def __contains__(self, item: Any) -> bool:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return _canonical(_as_atom(item)) in self._members

    def __iter__(self) -> Iterator[Atom]:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return iter(self._members.values())

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return len(self._members)

    def add(self, value: Any) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        atom = _as_atom(value)
        self._members.setdefault(_canonical(atom), atom)

    def discard(self, value: Any) -> None:  # noqa: D102  -- the enclosing type and implemented protocol supply this method contract
        self._members.pop(_canonical(_as_atom(value)), None)

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return f"AlphaSet({len(self._members)} atoms)"


# ------------------------------------------------------------ engine-backed
# The classes below take a live MeTTa handle and cross deliberately: the win
# IS the engine (tabling with write-invalidation, subscriptions), so their
# constructors do the setup crossings and their hot paths batch or stay
# local. The module itself still imports without an engine.


def _tabling_ready(space: Any) -> None:
    """lib_tabling, imported idempotently: the structure's dependency is
    the structure's setup.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
    space.run("!(import! &self (library lib_tabling))")


def _call_expr(name: str, args: tuple) -> Expression:
    return Expression([Symbol(name), *(_encode(argument) for argument in args)])


class TabledMap:
    """A computed cache that stays correct: a read-only view of a TABLED
    function, so tm[args] evaluates once, repeats answer from the
    engine's table, and a write to a space the function reads (by its
    literal name) invalidates exactly the affected tables, SWI's
    incremental tabling underneath. functools.cache has no dependency
    tracking at all; this is the memoization that is safe next to a
    mutating knowledge base.

        m.run("(= (cheapest) (min-atom (collapse (match &kb (price $i $p) $p))))")
        prices = TabledMap(m, "cheapest", arity=0)
        prices[()]                  # evaluated once, tabled
        kb.add(S.price(S.plum, 1))  # invalidates
        prices[()]                  # re-evaluated, fresh

    Not a Mapping ABC on purpose: the key domain is the function's, not
    enumerable, so iteration would lie. `key in tm` COMPUTES (and
    tables) the entry, which is what membership means for a computed
    map. A nondeterministic function does not fit a map; a key whose
    call answers several values raises, and one answering none is a
    KeyError.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, space: Any, name: str, *, arity: int | None = None) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self._space = space
        self._name = name
        _tabling_ready(space)
        if arity is None:
            compiled = space.arities(name)
            if len(compiled) != 1:
                msg = (
                    f"{name!r} has {len(compiled)} compiled arities; pass "
                    f"arity= to say which one this map views"
                )
                raise PettaError(
                    msg
                )
            arity = compiled[0] - 1
        self._arity = arity
        holes = " ".join(f"$x{position}" for position in range(arity))
        spelled = f"({name} {holes})" if holes else f"({name})"
        self._call_pattern = spelled
        declared = space.run(f"!(tabled {spelled})")
        if declared != [[True]]:
            msg = f"tabling {spelled} was not accepted: {declared!r}"
            raise PettaError(msg)

    def _key(self, key: Any) -> tuple:
        parts = key if isinstance(key, tuple) else (key,)
        if len(parts) != self._arity:
            msg = f"{self._name} takes {self._arity} argument(s), got {len(parts)}"
            raise PettaError(
                msg
            )
        return parts

    def __getitem__(self, key: Any) -> Any:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        parts = self._key(key)
        call = _call_expr(self._name, parts)
        if not self._space.eval(call):
            raise KeyError(key)
        # The second crossing answers from the table the first one built.
        return self._space._one(call)

    def __contains__(self, key: Any) -> bool:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        try:
            parts = self._key(key)
        except PettaError:
            return False
        return bool(self._space.eval(_call_expr(self._name, parts)))

    def stats(self) -> dict[str, int]:
        """The engine's own counters for this function's tables: tables,
        answers, complete-call, invalidated, reevaluated. invalidated
        above reevaluated is SWI deciding a table was not worth
        rebuilding yet; both moving is the freshness machinery working.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        (answer,) = self._space.eval(f"(table-stats {self._call_pattern})")
        if not isinstance(answer, Expression):
            msg = f"table-stats answered {answer!r}, not an expression"
            raise PettaError(msg)
        report: dict[str, int] = {}
        for pair in answer.children:
            if isinstance(pair, Expression) and len(pair.children) == 2:
                count = pair.children[1]
                report[str(pair.children[0])] = int(getattr(count, "value", count))
        return report

    def clear(self) -> None:
        """Drop this function's tables; the next read re-evaluates."""
        self._space.run(f"!(table-clear {self._call_pattern})")

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return f"TabledMap({self._name}/{self._arity} on {self._space.name})"


class LiveView:
    """A materialised view of one pattern, kept current by the space's
    own subscription events: dashboards, counters, "the current set of
    X" a program keeps consulting. Reads are local, the maintenance
    already happened.

        alerts = LiveView(m, S.alert(V.level))
        S.alert(S.red) in alerts       # no engine call
        len(alerts)                    # multiset size, like len(space)

    The seed query and the subscription install run inside ONE engine
    transaction, so no write can fall between them: the view starts
    exactly consistent and every later matching write arrives as an
    event. A space is a multiset and so is the view: len counts copies,
    iteration yields them, count(atom) answers multiplicity. close()
    cancels the subscription; a closed view keeps its last state.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, space: Any, pattern: Any) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self._space = space
        self._pattern = pattern
        self._lock = threading.Lock()
        self._held: Counter[Atom] = Counter()
        self._subscription: Any = None

        def setup() -> None:
            self._subscription = space.subscribe(
                pattern, self._deliver, on="both"
            )
            self._seed()

        space.transaction(setup)

    def _seed(self) -> None:
        """Read the whole multiset from the space. The first read and the
        answer to a removal the event cannot resolve are the same
        computation, so they are one.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        rows = self._space.match(self._pattern)
        names = rows.columns
        held: Counter[Atom] = Counter()
        for row in rows:
            held[substitute(_as_atom(self._pattern), dict(zip(names, row, strict=True)))] += 1
        self._held = held

    def _deliver(self, event: Any) -> None:
        with self._lock:
            if event.action == "add":
                self._held[event.atom] += 1
                return
            # A removal event fires once per removal and carries the
            # PATTERN asked for, not the occurrence that left (measured
            # 2026-08-19: `(alert $q)` over {(alert red), (alert amber)}
            # delivered `(alert $_610)` and the space kept amber). One
            # removal is one occurrence, multiset subtraction, so the
            # pattern alone no longer says what changed.
            #
            # It does say it when the pattern is ground and the only held
            # atom unifying with it is the pattern itself: nothing else
            # stored can unify with a ground atom, so exactly one copy of
            # it left. That is every `remove(S.alert(S.red))`, and it stays
            # a local decrement. Anything else re-reads the space, which
            # is what the subscription's own contract asks of a handler
            # that needs more than the event carries.
            pattern = event.atom
            stale = [held for held in self._held if _match(pattern, held) is not None]
            if stale == [pattern] and _is_ground(pattern):
                self._held[pattern] -= 1
                if self._held[pattern] <= 0:
                    del self._held[pattern]
                return
            self._seed()

    def __contains__(self, atom: Any) -> bool:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        with self._lock:
            return self._held[_as_atom(atom)] > 0

    def count(self, atom: Any) -> int:
        """How many copies of this atom the view holds."""
        with self._lock:
            return self._held[_as_atom(atom)]

    def __len__(self) -> int:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        with self._lock:
            return sum(self._held.values())

    def __iter__(self) -> Iterator[Atom]:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        with self._lock:
            snapshot = list(self._held.elements())
        return iter(snapshot)

    def close(self) -> None:
        """Cancel the subscription; the view stops updating."""
        if self._subscription is not None:
            self._subscription.cancel()
            self._subscription = None

    def __enter__(self) -> Self:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        self.close()

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return f"LiveView({self._pattern} on {self._space.name}, {len(self)} atoms)"


class ClosureView:
    """Reachability over a stored relation: dependencies, hierarchies,
    (a, b) in view. The closure is a pair of MeTTa equations over the
    relation's own atoms, TABLED from birth, because tabling is what
    makes a cyclic or symmetric closure terminate at all (SLG
    resolution's whole point) and what keeps the answers fresh when the
    relation's atoms change (the space is read by its literal name, so
    SWI's incremental tabling invalidates on writes).

        deps = ClosureView(m, "imports")
        (S.app, S.libc) in deps
        deps.reachable(S.app)

    Nodes are ATOMS, not names: the relation holds whatever atoms were
    stored in it, and a Python str is a MeTTa String rather than the
    symbol of the same spelling, so reachable("app") answers nothing
    where reachable(S.app) answers the closure. The relation NAME is a
    str because it names a function rather than an atom.

    symmetric=True adds the reversed base case, the undirected reading;
    without tabling that spelling never terminates, which is why the
    class always tables. Defines `<relation>-closure` (and its `-step`)
    in the space, named so a MeTTa program can call the same closure.
    """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

    def __init__(self, space: Any, relation: str, *, symmetric: bool = False) -> None:  # noqa: D107  -- the enclosing class documents construction and the object invariants
        self._space = space
        self._relation = relation
        self._fn = f"{relation}-closure"
        step = f"{relation}-step"
        _tabling_ready(space)
        name = space.name
        space.run(f"(= ({step} $x $y) (match {name} ({relation} $x $y) $y))")
        if symmetric:
            space.run(f"(= ({step} $x $y) (match {name} ({relation} $y $x) $y))")
        space.run(f"(= ({self._fn} $x $y) ({step} $x $y))")
        space.run(f"(= ({self._fn} $x $z) (let $y ({step} $x $y) ({self._fn} $y $z)))")
        for declared in (step, self._fn):
            accepted = space.run(f"!(tabled ({declared} $a $b))")
            if accepted != [[True]]:
                msg = f"tabling ({declared} ...) was not accepted: {accepted!r}"
                raise PettaError(
                    msg
                )

    def __contains__(self, pair: tuple) -> bool:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        start, end = pair
        return bool(self._space.eval(_call_expr(self._fn, (start, end))))

    def reachable(self, start: Any) -> set[Atom]:
        """Every node reachable from start, as a set: the closure is a
        relation, so duplicates are answer multiplicity, not data.
        """  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose
        answers = self._space.eval(_call_expr(self._fn, (start, Variable("_reach"))))
        return {answer for answer in answers if isinstance(answer, Atom)}

    def __repr__(self) -> str:  # noqa: D105  -- the Python data-model hook is defined by its name and enclosing type contract
        return f"ClosureView({self._relation} on {self._space.name})"
