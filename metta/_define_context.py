"""Purpose: describe the state shared by compiler lowering bands.
Guarantees:
  - expression lowering can inspect an exact host binding without executing
    an attribute lookup [tested:
    test_callable_mentions_share_operator_and_fourteen_math_names;
    commit=cff2e7f319bd2212f0c2d74f8d5fe5be3ac693b5]
  - next_aux_serial is unique across concurrent compiler calls [tested
    test_define_from_two_threads_is_serialized]
  - compiler mixins operate on one explicit SSA scope and one shared
    auxiliary-equation collection [tested test_nested_loops_carry_the_outer_state]
  - statement lowering can resolve a local annotation into an in-place MeTTa
    type claim [tested: test_an_annotated_binding_emits_its_claim;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - namespace-builder roles are explicit compiler state and survive every
    nested compiler fork [tested:
    test_compiled_bodies_reach_all_four_mention_families; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - compiler bands can resolve a bound Defined through its MeTTa name [tested:
    test_compiled_body_calls_renamed_defined_sibling; commit=18b1135167d60396c41e63e42ded2f66d0eb1900]
  - statement and expression bands share the typed State-cell resolver contract
    used by property reads and writes [tested:
    test_compiled_state_properties_round_trip_through_engine_heads;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - nested compiler forks retain source coordinates and loop depth for host
    island diagnostics [tested:
    test_py_host_island_inside_loops_emits_exact_findings;
    commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - expression lowering can request exact parameter names for a known call
    shape [tested: test_known_call_site_keywords_bind_to_positional_metta_arguments;
    commit=c2ad5892fbfdd690dd7e9b507e76e87d7d1376d1]
  - compiler forks retain literal container species used by Python operator
    dispatch [tested:
    test_compiled_operators_follow_python_protocols_and_result_species;
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
    builders: frozenset[str]
    # True while a pattern scope compiles through this compiler: patterns
    # are structural, so the host-island fallback stays out of them and the
    # loud refusals keep their ground there. Set and restored by the two
    # pattern scopes, never by forks.
    _in_pattern: bool = False
    # The scope key holding the innermost except arm's error atom, or None
    # outside every arm; a bare `raise` re-throws through it. Lexical, so
    # forks and nested equation compilers inherit it.
    handler_error: str | None = None
    # True while compiling lexically inside a try BODY: a binding there
    # traps error data and produces it, so `total = 10 // x` aborts to the
    # arms exactly as Python's raise would, instead of binding an (Error
    # ...) atom that rides out through the success tag. Elsewhere bindings
    # stay bare and the railway carries errors to the answer.
    in_try_body: bool = False
    # `type X = ...` aliases in this definition, each mapping to its type
    # alternatives: a single-type alias inlines at annotation sites (the
    # in-place claim checker reads atoms, not rewrites) while its equation
    # still gives the NAME meaning in the space; a union alias stays
    # symbolic. Shared across every compiler of the definition, like aux.
    type_aliases: dict[str, list[Atom]]
    # Names a `global` pragma declared: their reads island against the
    # live module and their assignments island a globals() write. Shared
    # across every compiler of the definition.
    pragma_globals: set[str]
    # Library aliases the compiled equations lean on (a dict literal needs
    # lib_dict's vocabulary); shared like aux, imported at installation.
    libraries: set[str]
    # Local names currently bound to a dict-space, copied per fork like
    # space_locals: subscripts read get-value, membership asks dict-has,
    # subscript assignment is dict-put and del is dict-remove.
    dict_locals: set[str]
    # Local Python container species whose common Atom image would otherwise
    # erase list-versus-tuple or set/dict-space protocol dispatch.
    container_locals: dict[str, str]
    # Names whose declared or locally derived Python type is an exact native
    # int/float. These may retain the engine's pure numeric heads; every
    # untyped operand must use Python's live operator protocol instead.
    number_locals: set[str]
    number_return: bool

    def annotation_alternatives(self, node: ast.expr) -> list[Atom]:
        raise NotImplementedError

    def annotation_is_native_number(self, node: ast.expr) -> bool:
        raise NotImplementedError

    def _binop_atom(
        self,
        op: ast.operator,
        left: Atom,
        right: Atom,
        line: int | None,
        *,
        left_kind: str | None = None,
        right_kind: str | None = None,
        native: bool = False,
    ) -> Atom:
        raise NotImplementedError

    def _inplace_atom(
        self,
        op: ast.operator,
        left: Atom,
        right: Atom,
        line: int | None,
        *,
        left_kind: str | None = None,
        right_kind: str | None = None,
    ) -> Atom:
        raise NotImplementedError

    def _container_kind(self, node: ast.expr) -> str | None:
        raise NotImplementedError

    def _native_number(self, node: ast.expr) -> bool:
        raise NotImplementedError

    def _diagnostic_term(self, node: ast.expr) -> Atom:
        raise NotImplementedError

    def _operator_operand(self, operand: Atom, kind: str | None) -> Atom:
        raise NotImplementedError

    def _dict_atom(self, atom: Atom) -> bool:
        raise NotImplementedError

    def _implicit_island(self, node: ast.expr) -> Atom:
        raise NotImplementedError

    def _effect_block(
        self,
        statements: list[ast.stmt],
        continuation: Callable[[CompilerContext], Atom],
    ) -> Atom:
        raise NotImplementedError

    host: Callable[[str], bool]
    host_value: Callable[[str], Any]
    runtime_ops: set[str]
    hazards: set[str]
    scope: dict[str, str]
    space_locals: set[str]
    known: Callable[[str], bool]
    returns_bool: Callable[[str], bool]
    used: set[str]
    aux: list[Expression]
    lifted: dict[str, tuple[str, list[str], bool]]
    closer: Callable[[Any], Atom] | None
    closer_names: list[str]
    function: Any
    source: str
    source_path: str
    first_line: int
    loop_depth: int

    def annotation_atom(self, node: ast.expr) -> Atom:
        raise NotImplementedError

    def nondet(self, called: str) -> bool:
        raise NotImplementedError

    def _resolved_call_name(self, called: str) -> str:
        raise NotImplementedError

    def _resolved_name(self, identifier: str) -> str | None:
        raise NotImplementedError

    def _bound_defined_name(self, identifier: str) -> str | None:
        raise NotImplementedError

    def call_parameters(self, called: str, arity: int) -> tuple[str, ...] | None:
        raise NotImplementedError

    def _bound_call_parameters(self, identifier: str, arity: int) -> tuple[str, ...] | None:
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

    def _mention(self, node: ast.expr) -> Atom | None:
        raise NotImplementedError

    def _state_cell(self, node: ast.expr) -> Atom | None:
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
