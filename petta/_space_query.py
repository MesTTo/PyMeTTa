"""Purpose: plan and decode eager conjunctive queries for one named space.
Guarantees:
  - conjunctive patterns preserve first-appearance column order [tested
    test_query_surfaces_share_column_order]
  - guards and limits are sent to the engine rather than applied after
    decoding [tested test_query_where_guard_and_limit]
  - non-positive limits fail before an engine call [tested
    test_limit_validation_refuses_nonsense]
  - eager Rows retain normalized query context for why() [tested
    test_query_rows_explain_empty_results]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

from typing import Any

from ._engine import Runtime
from ._space_objects import _column_names, _limits, guard_atom
from .atoms import Atom, _to_atom, atom_from_wire
from .results import Rows, _QueryContext


def _query_target(
    space: str,
    wires: list[Any],
    columns: list[str],
    where: Atom | None,
    limit: int | None,
) -> tuple[str, list[Any]]:
    if where is not None:
        return "petta_py_query_guarded_all", [
            space,
            wires,
            where.to_wire(),
            columns,
            limit or 0,
        ]
    if limit is not None:
        return "petta_py_query_limit_all", [space, wires, columns, limit]
    return "petta_py_query_all", [space, wires, columns]


def query_rows(
    rt: Runtime,
    space: str,
    patterns: tuple[Any, ...],
    *,
    where: Any | None,
    limit: int | None,
    timeout: float | None,
    inferences: int | None,
) -> Rows:
    """Execute one eager query and decode its rows."""
    _validate_limit(limit)
    atoms: list[Atom] = [_to_atom(pattern) for pattern in patterns]
    guard = guard_atom(where)
    columns = _column_names(atoms)
    predicate, inputs = _query_target(
        space,
        [atom.to_wire() for atom in atoms],
        columns,
        guard,
        limit,
    )
    answered = _execute_query(rt, predicate, inputs, _limits(timeout, inferences))
    return Rows(
        tuple(columns),
        _decode_rows(answered),
        _query=_QueryContext(space, tuple(atoms), guard),
    )


def _validate_limit(limit: int | None) -> None:
    if limit is None:
        return
    # The comparison below is what would otherwise report a wrong type, as
    # "'<=' not supported between instances of 'str' and 'int'", which names
    # neither the argument nor the call.
    if isinstance(limit, bool) or not isinstance(limit, int):
        msg = f"limit must be a positive int or None, got {limit!r}"
        raise TypeError(msg)
    if limit <= 0:
        msg = f"limit must be positive, got {limit}"
        raise ValueError(msg)


def _execute_query(
    rt: Runtime,
    predicate: str,
    inputs: list[Any],
    limits: tuple[float, int] | None,
) -> Any:
    if limits is None:
        return rt.apply_must(predicate, *inputs)
    return rt.apply_must("petta_py_limited", *limits, predicate, inputs)


def _decode_rows(answered: Any) -> list[tuple[Atom, ...]]:
    return [tuple(atom_from_wire(value) for value in row) for row in answered]
