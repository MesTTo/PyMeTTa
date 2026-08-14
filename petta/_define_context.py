"""Purpose: describe the state shared by compiler lowering bands.
Guarantees:
  - compiler mixins operate on one explicit SSA scope and one shared
    auxiliary-equation collection [tested test_nested_loops_carry_the_outer_state]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import ast
from collections.abc import Callable
from typing import Any

from .atoms import Atom, Expr


class CompilerContext:
    """State and cross-band operations supplied by the concrete compiler."""

    name: str
    pyname: str
    _builtins: dict[str, Any]
    host: Callable[[str], bool]
    runtime_ops: set[str]
    hazards: set[str]
    scope: dict[str, str]
    known: Callable[[str], bool]
    used: set[str]
    aux: list[Expr]
    lifted: dict[str, tuple[str, list[str], bool]]
    closer: Callable[[Any], Atom] | None
    closer_names: list[str]

    def _inner(self, extra: list[str]) -> CompilerContext:
        raise NotImplementedError

    def _python_resolvable(self, identifier: str) -> bool:
        raise NotImplementedError

    def _temp(self, base: str) -> str:
        raise NotImplementedError

    def expression(self, node: ast.expr) -> Atom:
        raise NotImplementedError

    def _truthy(self, node: ast.expr) -> Atom:
        raise NotImplementedError

    def _x_Name(self, node: ast.Name) -> Atom:
        raise NotImplementedError

    def _x_Constant(self, node: ast.Constant) -> Atom:
        raise NotImplementedError

    def _comprehension(self, generators: list[ast.comprehension], elt: ast.expr, line: int) -> Atom:
        raise NotImplementedError
