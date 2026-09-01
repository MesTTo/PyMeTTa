"""Purpose: mark and execute explicit ``py(expr)`` host islands in compiled bodies.
Assumes:
  - only the expression compiler constructs ``_HostIsland`` values; the public
    ``py`` function is an identity outside a compiled definition [tested:
    test_py_is_identity_outside_a_compiled_body; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
Guarantees:
  - a marked expression executes at engine application time with the current
    compiled local values and live Python globals and closure cells [tested:
    test_py_host_island_executes_per_engine_application; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - each island retains its source spelling and repeated-loop status for lint
    diagnostics [tested: test_py_host_island_inside_loops_emits_exact_findings;
    commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - nested scopes created by an island resolve the same runtime locals as the
    outer expression [tested: test_host_island_nested_scopes_see_compiled_locals;
    commit=WORKTREE]
Fails when:
  - an internal compiled call supplies a different number of runtime locals
    than the island captured; this is a compiler/runtime contract violation.
"""  # noqa: D205  -- the module contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import copy
import types
from typing import Any

__all__ = ["py"]


def py[T](value: T) -> T:
    """Mark a host expression inside ``@define``; otherwise return it unchanged.

    The compiler recognizes this exact callable by identity. It stores the
    enclosed expression as an applicable grounded value, so the host code runs
    when the equation is applied rather than when the decorator compiles it.
    """
    return value


class _HostIsland:
    """One compiled host expression applied to its current engine locals."""

    __slots__ = (
        "_closure_cells",
        "_code",
        "_globals",
        "in_loop",
        "line",
        "path",
        "runtime_names",
        "source",
    )

    def __init__(
        self,
        fn: types.FunctionType,
        expression: ast.expr,
        runtime_names: tuple[str, ...],
        *,
        source: str,
        path: str,
        first_line: int,
        in_loop: bool,
        marked: bool = True,
    ) -> None:
        body = copy.deepcopy(expression)
        tree = ast.fix_missing_locations(ast.Expression(body=body))
        if first_line > 1:
            ast.increment_lineno(tree, first_line - 1)
        self._code = compile(tree, path, "eval")
        self._globals = fn.__globals__
        self._closure_cells = tuple(
            zip(fn.__code__.co_freevars, fn.__closure__ or (), strict=True)
        )
        self.runtime_names = runtime_names
        spelled = ast.get_source_segment(source, expression) or ast.unparse(expression)
        # An implicit island keeps the author's own spelling: wrapping it in
        # py(...) would show source the author never wrote in lint findings.
        self.source = f"py({spelled})" if marked else spelled
        self.path = path
        self.line = first_line + expression.lineno - 1
        self.in_loop = in_loop

    def __call__(self, *values: Any) -> Any:
        if len(values) != len(self.runtime_names):
            msg = (
                f"{self.source} expected {len(self.runtime_names)} compiled local(s), "
                f"got {len(values)}"
            )
            raise RuntimeError(msg)
        namespace = self._globals.copy()
        for name, cell in self._closure_cells:
            try:
                namespace[name] = cell.cell_contents
            except ValueError:
                continue
        namespace.update(zip(self.runtime_names, values, strict=True))
        # Evaluating arbitrary host syntax is the explicit purpose of an
        # island, marked or implicit; either way nothing here ran at
        # compile time. The
        # code object was compiled from the marker's own source span inside
        # the user's own function, so it is their expression running in their
        # process, not input crossing a boundary. ast.literal_eval cannot
        # stand in: an island is an expression, not a literal.
        # pylint: disable-next=eval-used
        return eval(self._code, namespace, namespace)  # noqa: S307  # nosec B307
