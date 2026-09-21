"""Purpose: derive door orders from source calls without numbering open graphs.

Guarantees: strongly connected components are enumerated before longest paths;
mixed crossings, recursion and open dependencies remain separate findings
[tested: tests/repository/test_door_order.py; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Caller-implemented contracts remain open, including through helper arguments;
combining a contract call with a native crossing is mixed [tested:
test_supplied_callable_with_native_crossing_is_mixed,
test_composition_of_contract_open_door_is_unordered_by_dependency; commit=07976cf8b415390449863d803277b73102673b51].
A shipped door's verdict is read from the generated table
metta/doors/_orders.py, which doororder.py derives from the same analysis and
whose drift the door-order lane refuses; only rows outside the table are
analysed in the running process [tested:
test_shipped_rows_publish_from_the_table_without_analysis,
test_rows_outside_the_table_are_analysed_at_runtime; commit=38aa006aa9ecb1ce5366439fee69474623e37091].
Owns resources: source files are read and closed during snapshot acquisition;
the last source snapshot and its immutable report are cached in this process.
Guarded by: functools.lru_cache protects publication and functools.cache the
solved core; duplicate concurrent analysis is harmless because its input and
result are immutable, and `CallGraph.extended` copies the cached core rather
than writing to it.
"""

from __future__ import annotations

import ast
import hashlib
import os
import pickle
import sys
import tempfile
from collections.abc import Container, Iterable, Mapping
from dataclasses import dataclass
from functools import cache, lru_cache
from graphlib import TopologicalSorter
from pathlib import Path
from types import MappingProxyType

from metta.doors import AnswersAs, Door
from metta.doors._analysis import CallGraph, Calls, ContractCall
from metta.doors._scan import core, core_paths


def components(graph: Mapping[str, Iterable[str]]) -> tuple[tuple[str, ...], ...]:
    """Enumerate SCCs with two iterative depth-first traversals in O(V+E)."""
    # Kosaraju's reverse-postorder construction, as in NetworkX 3.6.1:
    # https://github.com/networkx/networkx/blob/7530809bfa1ea7ed6fdf918a4d1431488953cb1f/networkx/algorithms/components/strongly_connected.py
    edges = {name: tuple(targets) for name, targets in graph.items()}
    for targets in tuple(edges.values()):
        for target in targets:
            edges.setdefault(target, ())
    reverse: dict[str, list[str]] = {name: [] for name in edges}
    for name, targets in edges.items():
        for target in targets:
            reverse[target].append(name)
    seen: set[str] = set()
    postorder: list[str] = []
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


@dataclass(frozen=True, slots=True)
class Verdict:
    """The catalog's projection of one order: a number, or why there is none."""

    number: int | None
    mixed: bool = False
    open: bool = False
    recursive: bool = False
    dependency: bool = False


@dataclass(frozen=True, slots=True)
class Order:
    """A numeric order only when every reachable boundary permits one."""

    number: int | None
    calls: frozenset[str]
    native: frozenset[str]
    open: frozenset[str]
    cycles: tuple[tuple[str, ...], ...]
    blocked_by: frozenset[str] = frozenset()
    contracts: frozenset[ContractCall] = frozenset()

    @property
    def defect_open(self) -> frozenset[str]:
        """Open calls with no declared caller-implemented parameter contract."""
        return self.open - {call.site for call in self.contracts}

    @property
    def mixed(self) -> bool:
        """Whether a native crossing composes a door or invokes a supplied contract."""
        return bool(self.native and (self.calls or self.contracts))

    @property
    def verdict(self) -> Verdict:
        """The five facts the catalog publishes about this order."""
        return Verdict(self.number, self.mixed, bool(self.open), bool(self.cycles), bool(self.blocked_by))


def derive(rows: Iterable[Door], calls: Mapping[str, Calls]) -> Mapping[str, Order]:
    """Collapse helper paths, then assign orders on the door condensation DAG."""
    records = tuple(rows)
    bodies: dict[str, set[str]] = {}
    for row in records:
        if row.body:
            bodies.setdefault(row.body.module + "." + row.body.symbol, set()).add(row.key)
    helpers = {name: facts for name, facts in calls.items() if name not in bodies}
    helper_graph = {name: facts.targets.intersection(helpers) for name, facts in helpers.items()}
    groups = components(helper_graph)
    group_of = {name: str(index) for index, members in enumerate(groups) for name in members}
    predecessors = {str(index): {group_of[target] for name in members
                                 for target in helper_graph[name] if group_of[target] != str(index)}
                    for index, members in enumerate(groups)}
    summaries: dict[str, Order] = {}
    for group in TopologicalSorter(predecessors).static_order():
        members = groups[int(group)]
        facts = [helpers[name] for name in members]
        dependencies = [summaries[target] for target in predecessors[group]]
        door_calls = frozenset(key for fact in facts for target in fact.targets
                               for key in bodies.get(target, ()))
        native = frozenset(site for fact in facts if not fact.guard for site in fact.native)
        opened = frozenset(site for fact in facts for site in fact.open)
        contracts = frozenset(call for fact in facts for call in fact.contracts)
        cycle = (members,) if len(members) > 1 or members[0] in helper_graph[members[0]] else ()
        summaries[group] = Order(
            None,
            door_calls.union(*(item.calls for item in dependencies)),
            native.union(*(item.native for item in dependencies)),
            opened.union(*(item.open for item in dependencies)),
            tuple(sorted(set(cycle).union(*(item.cycles for item in dependencies)))),
            contracts=contracts.union(*(item.contracts for item in dependencies)),
        )
    initial = {}
    for row in records:
        body = row.body.module + "." + row.body.symbol if row.body else None
        fact = calls.get(body, Calls(open=frozenset({f"source unavailable: {body}"}))) if body else Calls()
        dependencies = [summaries[group_of[target]] for target in fact.targets if target in helpers]
        direct = frozenset(key for target in fact.targets for key in bodies.get(target, ()))
        if row.body is None and row.sugar_of:
            direct |= frozenset({row.sugar_of.base})
        crossings = frozenset() if fact.guard else fact.native
        native = crossings | (frozenset({"declared binding: " + row.binding.door}) if row.binding else frozenset())
        unknown = fact.targets - calls.keys() - bodies.keys()
        opened = fact.open | frozenset("source unavailable: " + name for name in unknown)
        initial[row.key] = Order(
            None, direct.union(*(item.calls for item in dependencies)),
            native.union(*(item.native for item in dependencies)),
            opened.union(*(item.open for item in dependencies)),
            tuple(sorted(set().union(*(item.cycles for item in dependencies)))),
            contracts=fact.contracts.union(*(item.contracts for item in dependencies)),
        )
    graph = {name: value.calls for name, value in initial.items()}
    groups = components(graph)
    group_of = {name: str(index) for index, members in enumerate(groups) for name in members}
    predecessors = {str(index): {group_of[target] for name in members for target in graph.get(name, ())
                                 if group_of[target] != str(index)} for index, members in enumerate(groups)}
    result: dict[str, Order] = {}
    for group in TopologicalSorter(predecessors).static_order():
        members = groups[int(group)]
        cycle = (members,) if len(members) > 1 or members[0] in graph.get(members[0], ()) else ()
        for name in members:
            current = initial.get(name, Order(None, frozenset(), frozenset(), frozenset({"missing door " + name}), ()))
            blocked = frozenset(target for target in current.calls if target not in members and result[target].number is None)
            cycles = tuple(sorted(set(current.cycles).union(cycle)))
            number = None
            if not (current.open or current.mixed or cycles or blocked):
                callee_orders = [result[target].number for target in current.calls]
                number = 1 if current.native else max((value + 1 for value in callee_orders if value is not None), default=0)
            result[name] = Order(number, current.calls, current.native, current.open, cycles, blocked, current.contracts)
    return MappingProxyType({row.key: result[row.key] for row in records})


#: Two, because that is what a whole-tree analysis alternates between when a source set is
#: analysed with and without a row. A miss is correct and only slower, so this bounds memory
#: rather than guessing at a workload. It is no longer what a REGISTRATION costs: a door from
#: outside the shipped table reaches `_core` and `extended` instead, because its entry set is
#: one no other registration shares and so could never hit a cache of any size.
@lru_cache(maxsize=2)
def _facts(sources: tuple[tuple[str, str], ...], entries: frozenset[str],
           lifetimes: frozenset[str]) -> Mapping[str, Calls]:
    """Solve the call graph, cached on exactly what the SOLVE reads.

    The solve is the whole cost of the analysis and it reads three things: the sources, the
    entry points, and which of those defer to a lifetime protocol. It does not read anything
    else a `Door` row carries. Keying the cache on the whole row set instead meant that
    registering a door the generated table does not name re-solved the entire program, because
    two row sets differing in a field the solve never reads are different keys.

    Narrowing the key was necessary and not sufficient: a registered door adds its own body to
    the entry set, so its key still differs from every other registration's and no cache size
    could hold them. `live` therefore routes that case through `_core` and
    `CallGraph.extended`, and this stays the whole-tree path
    [measured 2026-09-19: a full solve is 97.73s against 2.57s for an extension of it].
    """
    return CallGraph(dict(sources), entries, lifetimes).solve()


def analyse(rows: Iterable[Door], sources: Mapping[str, str]) -> Mapping[str, Order]:
    """Read one explicit source set without importing any of its bodies."""
    records = tuple(rows)
    entries = frozenset(row.body.module + "." + row.body.symbol for row in records if row.body)
    lifetimes = frozenset(row.body.module + "." + row.body.symbol for row in records
                          # policy-inventory-exempt: mechanism-internal; reason=context and stream results defer execution to their lifetime protocols; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._evaluate
                          if row.body and row.answers in {AnswersAs.context, AnswersAs.stream})
    return derive(records, _facts(tuple(sorted(sources.items())), entries, lifetimes))


def source_text(paths: Mapping[str, Path]) -> dict[str, str]:
    """Include the root stub's named exports while retaining runtime bodies."""
    sources = {module: path.read_text(encoding="utf-8") for module, path in sorted(paths.items())}
    if "metta" in paths:
        stub = paths["metta"].with_suffix(".pyi")
        if stub.is_file():
            declarations = ast.parse(stub.read_text(encoding="utf-8"))
            imports = [ast.unparse(node) for node in declarations.body
                       if isinstance(node, (ast.Import, ast.ImportFrom)) and getattr(node, "module", None) != "__future__"]
            sources["metta"] += "\n" + "\n".join(imports) + "\n"
    return sources


#: Where a solved core is kept between processes. The directory ignores itself,
#: which is how every tool cache in this tree stays out of `git status`: ruff,
#: pytest, mypy, Hypothesis and import-linter each write a `.gitignore` holding
#: `*` inside the directory they create, so the repository's own .gitignore
#: stays about repository-wide rules [source: .gitignore's header].
_CORE_CACHE = Path(__file__).resolve().parent / ".analysis-cache"


def _core_fingerprint(sources: tuple[tuple[str, str], ...], entries: frozenset[str],
                      lifetimes: frozenset[str]) -> str:
    """Name a stored core by everything its contents depend on.

    The source text, the entry and lifetime sets, the interpreter and the
    ANALYSIS MODULE itself: a stored graph is an instance graph of the classes
    in `_analysis.py`, so a change there can make yesterday's file describe
    objects this process no longer has. Keying on it turns that into a miss
    rather than into a wrong answer, which is the only invalidation rule this
    cache needs, because everything else it reads is already in the key.
    """
    digest = hashlib.blake2b(digest_size=20)
    for module, text in sources:
        digest.update(module.encode()); digest.update(b"\0")
        digest.update(text.encode()); digest.update(b"\0")
    for group in (sorted(entries), sorted(lifetimes)):
        for name in group:
            digest.update(name.encode()); digest.update(b"\0")
        digest.update(b"\1")
    digest.update(Path(sys.modules[CallGraph.__module__].__file__).read_bytes())
    digest.update(sys.version.encode())
    return digest.hexdigest()


def _read_core(path: Path) -> CallGraph | None:
    """A stored core, or None for anything at all wrong with the file.

    A cache may never turn a rebuild into a failure, so every way of not
    getting a graph back -- absent, truncated by a killed writer, written by an
    incompatible build -- answers the same way and the caller solves instead.
    """
    try:
        with path.open("rb") as handle:
            graph = pickle.load(handle)
    except (OSError, EOFError, AttributeError, ImportError, IndexError,
            KeyError, TypeError, ValueError, pickle.UnpicklingError):
        return None
    return graph if isinstance(graph, CallGraph) else None


def _write_core(path: Path, graph: CallGraph) -> None:
    """Store a solved core so the next process loads it instead of solving.

    Written to a temporary file in the same directory and renamed, because the
    four xdist workers of the test lane solve at once and a reader must never
    meet a half-written file; rename is atomic within a filesystem. Failing to
    store is not an error: the cache is an optimisation and a read-only or full
    filesystem must cost time rather than the run.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        (path.parent / ".gitignore").write_text("*\n", encoding="utf-8")
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                pickle.dump(graph, handle, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
    except OSError:
        return


@cache
def _core(sources: tuple[tuple[str, str], ...], entries: frozenset[str],
          lifetimes: frozenset[str]) -> CallGraph:
    """The solved core, kept so a door from outside it costs only its own module.

    Held as the GRAPH rather than its answers, because what a door outside the
    shipped table needs is the store the answers were derived from. `extended`
    copies it, so the cached graph is never the one that gets written to.

    Kept ACROSS processes as well as within one. Solving costs 108s over the
    172 core modules and `@cache` is per-process, so every xdist worker that
    met a door outside the shipped table paid it again; loading the same graph
    costs 1.1s [measured 2026-09-21: build 108.15s, dump 0.69s into 98.0 MB,
    load 1.14s, and the restored graph extends to an identical result].
    """
    path = _CORE_CACHE / (_core_fingerprint(sources, entries, lifetimes) + ".pickle")
    stored = _read_core(path)
    if stored is not None:
        return stored
    graph = CallGraph(dict(sources), entries, lifetimes)
    graph.solve()
    _write_core(path, graph)
    return graph


def _entry_names(records: tuple[Door, ...], modules: Container[str] | None = None,
                 *, deferring: bool = False) -> frozenset[str]:
    """Door bodies as entry points, optionally only those a module set contains."""
    return frozenset(
        row.body.module + "." + row.body.symbol for row in records
        if row.body and (modules is None or row.body.module in modules)
        # policy-inventory-exempt: mechanism-internal; reason=context and stream results defer execution to their lifetime protocols; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._evaluate
        and (not deferring or row.answers in {AnswersAs.context, AnswersAs.stream}))


@cache
def _core_entries() -> tuple[frozenset[str], frozenset[str]]:
    """The SHIPPED table's own entries and lifetimes, read from marked source.

    `_core` is keyed on the entry set it solves for, so taking that set from the
    caller's records gives a different key per caller and pays the fixed point
    again under each one. The catalog snapshot passes the whole live table, which
    made the key look constant until something passed a subset
    [measured 2026-09-20: `orders()` over the 210 shipped rows plus one provider
    row took 105.03s cold and 3.79s on the same key, while callers passing 3 and
    5 of those rows each missed and solved again].

    Reading the shipped rows makes the key a constant of the tree, so one solve
    serves every caller in the process. It is also the entry set doororder.py
    derives the verdict table from, so a row analysed at runtime is now measured
    against the same core as the table it sits beside, instead of against
    whichever subset its caller happened to name -- an entry set reaches fewer
    symbols, and a helper only a shipped entry reaches is one the smaller
    analysis cannot see is part of a cycle.
    """
    rows = core()
    return _entry_names(rows), _entry_names(rows, deferring=True)


def live(rows: Iterable[Door]) -> Mapping[str, Order]:
    """Analyse the shipped core and the loaded providers' own source files.

    A door the generated table does not name is analysed against the core rather
    than alongside it. Its module is the only new source and its body the only new
    entry, and the core's store is already the least fixed point for the core's
    own entries, so what is new is propagated into a copy of that store instead of
    the whole program being solved again. Before this, a test registering sixty
    synthetic doors paid sixty whole-program analyses, each keyed on an entry set
    no other test shared, which is why a larger cache could not help
    [measured 2026-09-19: one solve is 97.73s, of which the fixed point is 95.28s].

    The entries the core is solved for come from `_core_entries`, not from these
    records, which is what leaves one cache entry rather than one per caller.
    The extension still names every record, since a caller's rows can add
    entries the shipped table has not got.
    """
    records = tuple(rows)
    core_modules = {module: path for path, module in core_paths()}
    outside: dict[str, Path] = {}
    for row in records:
        if row.body and row.body.module not in core_modules:
            loaded = sys.modules.get(row.body.module)
            filename = vars(loaded).get("__file__") if loaded is not None else None
            if filename:
                outside[row.body.module] = Path(filename)
    # Read once: every core source is opened to build this, and the two paths
    # below both want it.
    sources = source_text(core_modules)
    if not outside:
        return analyse(records, sources)
    entries, lifetimes = _core_entries()
    graph = _core(tuple(sorted(sources.items())), entries, lifetimes)
    return derive(records, graph.extended(
        source_text(outside),
        entries | _entry_names(records),
        lifetimes | _entry_names(records, deferring=True)))


def orders(rows: Iterable[Door]) -> Mapping[str, Verdict]:
    """Read shipped verdicts from the generated table; analyse only rows outside it."""
    # The generated table imports this module's Verdict, so it is read here.
    from metta.doors._orders import VERDICTS  # noqa: PLC0415

    records = tuple(rows)
    result = {row.key: VERDICTS[row.key] for row in records if row.key in VERDICTS}
    if len(result) < len(records):
        derived = live(records)
        result.update((row.key, derived[row.key].verdict) for row in records if row.key not in VERDICTS)
    return MappingProxyType(result)
