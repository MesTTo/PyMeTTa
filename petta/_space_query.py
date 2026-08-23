"""Purpose: plan and decode eager conjunctive queries for one named space.
Guarantees:
  - relational solve answers retain variable columns and expose one-answer
    attribute projection [tested:
    test_solve_retires_the_five_relational_let_workarounds,
    test_solve_projects_variables_from_the_winning_pattern; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
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
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from typing import Any

from ._engine import Runtime
from ._name_mapping import resolve_known_name
from ._space_objects import _column_names, _limits, guard_atom
from .atoms import Atom, Expression, _atom_from_wire, _to_atom
from .results import Rows, _QueryContext


class SolveRows(Rows):
    """Bindings produced by relational solve, with one-answer projection."""

    def __getattr__(self, name: str) -> Any:
        # One resolver rule everywhere: attribute access carries the factories'
        # total underscore-to-hyphen map, so row.async_x reads column async-x
        # exactly as V.async_x wrote it. Bracket access stays exact.
        resolved = resolve_known_name(name, self.columns.__contains__, allow_bang=False)
        if resolved is None:
            msg = f"no solution variable {name!r}; variables are {list(self.columns)}"
            raise AttributeError(msg)
        values = self._column(resolved)
        return values[0] if len(values) == 1 else values


def solve_rows(columns: tuple[str, ...], answers: list[Atom]) -> SolveRows:
    """Shape evaluated answer templates back into caller-named bindings."""
    rows: list[tuple[Atom, ...]]
    if len(columns) == 1:
        rows = [(answer,) for answer in answers]
    else:
        rows = []
        for answer in answers:
            if not isinstance(answer, Expression) or len(answer) != len(columns):
                msg = f"solve answer {answer!r} does not carry {len(columns)} bindings"
                raise TypeError(msg)
            rows.append(tuple(answer))
    return SolveRows(columns, rows)


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
    return [tuple(_atom_from_wire(value) for value in row) for row in answered]
