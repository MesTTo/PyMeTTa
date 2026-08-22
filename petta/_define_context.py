"""Purpose: describe the state shared by compiler lowering bands.
Guarantees:
  - next_aux_serial is unique across concurrent compiler calls [tested
    test_define_from_two_threads_is_serialized]
  - compiler mixins operate on one explicit SSA scope and one shared
    auxiliary-equation collection [tested test_nested_loops_carry_the_outer_state]
  - statement lowering can resolve a local annotation into an in-place MeTTa
    type claim [tested: test_an_annotated_binding_emits_its_claim;
    commit=WORKTREE]
Guarded by:
  - _AUX_LOCK protects the process-wide helper serial [tested
    test_define_from_two_threads_is_serialized]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import itertools
import threading
from collections.abc import Callable
from typing import Any

from .atoms import Atom, Expression

_AUX_NAMES = itertools.count(1)
_AUX_LOCK = threading.Lock()


def next_aux_serial() -> int:
    """Return a process-unique compiler helper serial."""
    with _AUX_LOCK:
        return next(_AUX_NAMES)


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
    aux: list[Expression]
    lifted: dict[str, tuple[str, list[str], bool]]
    closer: Callable[[Any], Atom] | None
    closer_names: list[str]

    def annotation_atom(self, node: ast.expr) -> Atom:
        raise NotImplementedError

    def nondet(self, called: str) -> bool:
        raise NotImplementedError

    def _fork(self) -> CompilerContext:
        raise NotImplementedError

    def _equation_compiler(
        self, params: list[str], closer: Callable[[Any], Atom] | None = None
    ) -> CompilerContext:
        raise NotImplementedError

    def _iteration(self, iter_node: ast.expr, var: str, body: Atom) -> Expression:
        raise NotImplementedError

    def _yield_from(self, node: ast.YieldFrom) -> Atom:
        raise NotImplementedError

    def _bind(self, name: str) -> str:
        raise NotImplementedError

    def block(self, statements: list[ast.stmt]) -> Atom:
        raise NotImplementedError

    def yield_answers(self, statements: list[ast.stmt]) -> list[Atom]:
        raise NotImplementedError

    def _while_statement(self, node: ast.While, rest: list[ast.stmt]) -> Atom:
        raise NotImplementedError

    def _for_statement(self, node: ast.For, rest: list[ast.stmt]) -> Atom:
        raise NotImplementedError

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

    def _x_Name(self, node: ast.Name) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        raise NotImplementedError

    def _x_Constant(self, node: ast.Constant) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        raise NotImplementedError

    def _x_BinOp(self, node: ast.BinOp) -> Atom:  # noqa: N802  -- the suffix mirrors ast node class names used by the translator's dynamic dispatch
        raise NotImplementedError

    def _comprehension(self, generators: list[ast.comprehension], elt: ast.expr, line: int) -> Atom:
        raise NotImplementedError
