"""Purpose: derive door orders from source calls without numbering open graphs.

Guarantees: strongly connected components are enumerated before longest paths;
mixed crossings, recursion and open dependencies remain separate findings
[tested: tests/repository/test_door_order.py; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
Caller-implemented contracts remain open, including through helper arguments;
combining a contract call with a native crossing is mixed [tested:
test_supplied_callable_with_native_crossing_is_mixed,
test_composition_of_contract_open_door_is_unordered_by_dependency; commit=WORKTREE].
Owns resources: source files are read and closed during snapshot acquisition;
the last source snapshot and its immutable report are cached in this process.
Guarded by: functools.lru_cache protects publication; duplicate concurrent
analysis is harmless because its input and result are immutable.
"""

from __future__ import annotations

import ast
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from graphlib import TopologicalSorter
from pathlib import Path
from types import MappingProxyType

from metta.doors import AnswersAs, Door
from metta.doors._analysis import CallGraph, Calls, ContractCall
from metta.doors._scan import core_paths


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
        native = frozenset(site for fact in facts for site in fact.native)
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
        native = fact.native | (frozenset({"declared binding: " + row.binding.door}) if row.binding else frozenset())
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


def analyse(rows: Iterable[Door], sources: Mapping[str, str]) -> Mapping[str, Order]:
    """Read one explicit source set without importing any of its bodies."""
    records = tuple(rows)
    entries = {row.body.module + "." + row.body.symbol for row in records if row.body}
    lifetimes = {row.body.module + "." + row.body.symbol for row in records
                 # policy-inventory-exempt: mechanism-internal; reason=context and stream results defer execution to their lifetime protocols; evidence=extensions/python/metta/doors/_analysis.py:CallGraph._evaluate
                 if row.body and row.answers in {AnswersAs.context, AnswersAs.stream}}
    return derive(records, CallGraph(sources, entries, lifetimes).solve())


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


@lru_cache(maxsize=1)
def _snapshot(rows: tuple[Door, ...], sources: tuple[tuple[str, str], ...]) -> Mapping[str, Order]:
    return analyse(rows, dict(sources))


def orders(rows: Iterable[Door]) -> Mapping[str, Order]:
    """Derive a catalog snapshot from the shipped core and loaded providers."""
    records = tuple(rows)
    paths = {module: path for path, module in core_paths()}
    for row in records:
        if row.body and row.body.module not in paths:
            loaded = sys.modules.get(row.body.module)
            filename = vars(loaded).get("__file__") if loaded is not None else None
            if filename:
                paths[row.body.module] = Path(filename)
    sources = tuple(source_text(paths).items())
    return _snapshot(records, sources)
