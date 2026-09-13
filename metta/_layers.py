"""Purpose: declare package foundations and derive their dependency orders.

Guarantees: unknown foundations and cycles are refused before projections are
computed [tested: tests/checks/check_layering_selftest.py; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
The compiler shares the catalog's native call-contract representation [tested:
test_computed_lambda_calls_bind_keywords_after_creating_the_value;
tests/checks/check_layering_selftest.py; commit=WORKTREE].
Decides: BUILDS_ON is the package dependency policy; import contracts, binding
modes and published layer orders derive from it [source:
extensions/python/metta/_layers.py:BUILDS_ON; commit=WORKTREE].
"""

from __future__ import annotations

from collections.abc import Mapping
from graphlib import TopologicalSorter
from itertools import chain
from types import MappingProxyType
from typing import Literal

# Values are predecessors, as in graphlib.TopologicalSorter. A package may
# import its transitive foundations and its own modules. The root is included
# here even though import-linter's container contract checks only its children.
# closed-set: decides; policy=which packages each package may import, its foundations, from which layergen derives the import-linter contract, the lazy-import direction and the published layer orders; reads=none, it is the source
BUILDS_ON: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "_layers": (),
    "_lazy": (),
    "_version": (),
    "seam": ("_lazy",),
    "_errors": ("seam",),
    "_atoms": ("_errors", "seam"),
    "vocabularies": ("_atoms",),
    "_catalog": ("vocabularies", "_atoms", "_errors", "seam"),
    "doors": ("_catalog", "vocabularies", "_atoms", "_layers"),
    "_binding": ("_catalog", "_atoms", "_errors", "seam"),
    "_compile": ("_catalog", "_atoms", "_errors", "vocabularies"),
    "_spaces": ("_binding", "doors", "_catalog", "_atoms", "_errors", "seam", "_version"),
    "_declare": ("_spaces", "_compile", "doors", "_catalog", "_atoms", "_errors", "seam"),
    "_observe": ("_declare", "_spaces", "_binding", "_catalog", "_atoms", "_errors", "seam"),
    "_faces": ("_declare", "_observe", "_spaces", "doors", "_atoms"),
    "algebra": ("_faces",),
    "convert": ("_faces",),
    "derivation": ("_faces",),
    "foreign": ("_faces",),
    "library": ("_faces", "_version"),
    "parallel": ("_faces",),
    "paths": ("_faces",),
    "structures": ("_faces",),
    "typing": ("_faces",),
    "cli": ("_faces",),
    "ipython": ("_faces",),
    "pytest_plugin": ("_faces",),
    "__main__": ("_faces", "importing", "library", "lint", "manifest", "remote"),
    "_pygments": ("_faces",),
    "events": ("_faces", "structures", "algebra"),
    "integrate": ("_faces", "convert", "foreign", "library"),
    "lint": ("_faces", "foreign"),
    "live": ("_faces", "structures", "foreign"),
    "remote": ("_faces", "foreign"),
    "spaces": ("_faces", "foreign", "structures"),
    "tables": ("_faces", "convert", "foreign"),
    "importing": ("_faces", "integrate"),
    "manifest": ("_faces", "remote", "tables"),
    "subscribe": ("_faces", "events", "foreign"),
    "testing": ("_faces", "algebra", "convert", "foreign", "remote"),
    "aio": ("_faces", "subscribe", "lint"),
    "_history": ("aio", "importing", "manifest", "subscribe", "testing", "parallel", "spaces"),
    "metta": (
        "_history", "cli", "derivation", "ipython", "paths", "pytest_plugin",
        "typing", "__main__", "_pygments", "_version", "_layers", "lint", "live", "spaces",
    ),
})


def analyse(
    graph: Mapping[str, tuple[str, ...]] = BUILDS_ON,
) -> tuple[dict[str, int], dict[str, frozenset[str]]]:
    """Return longest-path orders and transitive foundations of a complete DAG."""
    unknown = set(chain.from_iterable(graph.values())) - graph.keys()
    if unknown:
        msg = f"undeclared package foundations: {', '.join(sorted(unknown))}"
        raise ValueError(msg)
    order: dict[str, int] = {}
    foundations: dict[str, frozenset[str]] = {}
    for name in TopologicalSorter(graph).static_order():
        bases = graph[name]
        order[name] = max((order[base] + 1 for base in bases), default=0)
        foundations[name] = frozenset(bases).union(*(foundations[base] for base in bases))
    return order, foundations


_orders, _foundations = analyse()
ORDERS: Mapping[str, int] = MappingProxyType(_orders)
FOUNDATIONS: Mapping[str, frozenset[str]] = MappingProxyType(_foundations)
del _orders, _foundations


def package_of(module: str) -> str:
    """Return a declared package unit for a qualified metta module name."""
    if module == "metta":
        return module
    if not module.startswith("metta."):
        msg = f"not a metta module: {module!r}"
        raise ValueError(msg)
    name = module.split(".", 2)[1]
    if name not in BUILDS_ON:
        msg = f"undeclared package: {name!r}"
        raise ValueError(msg)
    return name


# policy-inventory-exempt: mechanism-internal; reason=the two Python import strategies selected by the package dependency relation; evidence=extensions/python/metta/_layers.py:binding_mode
def binding_mode(module: str, importer: str = "_faces") -> Literal["direct", "lazy"]:
    """Choose a direct foundation call or a strictly higher deferred call."""
    target = package_of(module)
    if target == importer or target in FOUNDATIONS[importer]:
        return "direct"
    if ORDERS[target] > ORDERS[importer]:
        return "lazy"
    msg = f"{importer} cannot depend on {target}: it is neither a foundation nor higher"
    raise ValueError(msg)


def layer_groups() -> tuple[tuple[str, ...], ...]:
    """Return exhaustive child layers, highest first and siblings sorted."""
    levels: dict[int, list[str]] = {}
    for name, order in ORDERS.items():
        if name != "metta":
            levels.setdefault(order, []).append(name)
    return tuple(tuple(sorted(levels[level])) for level in sorted(levels, reverse=True))
