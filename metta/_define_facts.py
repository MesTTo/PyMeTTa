"""Purpose: derive definition metadata from the Python syntax that
``@define`` already parses: an absolute source span, the source docstring,
lexical free variables, and the join of every call's declared effect.
Guarantees:
  - derivation reads syntax and symbol tables without executing user code
    [tested: test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=214a34885feb4fd1caf26c67143d6a3b0506e824]
  - Python 3.14 annotation scopes cannot be mistaken for the function scope
    whose free variables are reported [tested:
    test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=214a34885feb4fd1caf26c67143d6a3b0506e824]
  - purity checks resolve compiled callees under the same catalog spelling
    rule as expression lowering [tested:
    test_mapped_nondeterministic_calls_keep_their_call_role; commit=6b77b811c44e1819ed9cd99f3809c0667f289e2e]
  - the four-argument unify control form is pure while its branch calls are
    still visited and classified [tested:
    test_expression_position_unify_uses_the_engine_conditional_in_both_contexts;
    commit=6917bef7ca902671999eafcae3a7a86db8f69723]
  - compiler-recognized Python calls remain structural while effects in their
    arguments are joined independently [tested:
    test_compiler_recognized_python_calls_remain_structural,
    test_definition_match_is_a_nondeterministic_read; commit=79e9635b6c20e046ace8fc82bd3edf062c7ae9b2]
  - a ``.value`` access is conservatively mutable-state dependent, so a
    compiled State read or write cannot be advertised as immutable [tested:
    test_compiled_state_properties_round_trip_through_engine_heads;
    commit=3ded7552797b66d78e666141eb51f3bc14686bd2]
  - an exact ``py`` marker binding is always oracleIO even if an engine symbol
    with the same spelling carries weaker metadata [tested:
    test_py_host_island_executes_per_engine_application; commit=3f0a1d237a3c969b2d4ad0d48b2195ce196b631a]
  - delete statements and augmented assignments on Space-typed parameters are
    classified as state writes [tested:
    test_compiled_removal_statements_preserve_one_many_missing_and_target_scope;
    commit=79e9635b6c20e046ace8fc82bd3edf062c7ae9b2]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import inspect
import symtable
import tokenize
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import NamedTuple

from ._name_mapping import resolve_known_name
from .vocabularies import EffectClass


class SourceSpan(NamedTuple):
    """One function definition's absolute source coordinates."""

    path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int


class DefinitionFacts(NamedTuple):
    """Facts derived from one compiled clause's source."""

    source_span: SourceSpan
    doc: str | None
    free_variables: tuple[str, ...]
    effect: EffectClass

    @property
    def pure(self) -> bool:
        """The compatibility projection of a structural effect."""
        return self.effect is EffectClass.pureStructural


_CONTROL_EFFECTS = {
    "collapse": EffectClass.pureStructural,
    "empty": EffectClass.nondeterministicReadOnly,
    "superpose": EffectClass.nondeterministicReadOnly,
    # The four-argument control form itself decides a branch and
    # commits nothing; whichever branch it takes is a call visited
    # and joined on its own, so the form is structural, not a read.
    "unify": EffectClass.pureStructural,
}
_PYTHON_CALL_EFFECTS: dict[str, EffectClass] = dict.fromkeys(
    (
        "abs",
        "len",
        "max",
        "min",
        "pow",
        "range",
        "repr",
        "round",
        "sorted",
        "str",
        "sum",
    ),
    # These names are compiler-recognized structural lowerings, not dynamic
    # calls to arbitrary Python objects. Their argument calls are visited and
    # joined separately below.
    EffectClass.pureStructural,
)


def _tables(root: symtable.SymbolTable) -> Iterator[symtable.SymbolTable]:
    for child in root.get_children():
        yield child
        yield from _tables(child)


def _function_table(
    fn: types.FunctionType,
    source: str,
    path: str,
    absolute_line: int,
) -> symtable.SymbolTable:
    """Find the function scope, never the adjacent annotation scope."""
    roots: list[symtable.SymbolTable] = []
    source_path = Path(path)
    if source_path.is_file():
        with tokenize.open(source_path) as source_file:
            roots.append(symtable.symtable(source_file.read(), path, "exec"))
    roots.append(symtable.symtable(source, path, "exec"))

    for root in roots:
        candidates = [
            table
            for table in _tables(root)
            if table.get_type() == "function" and table.get_name() == fn.__name__
        ]
        exact = [table for table in candidates if table.get_lineno() == absolute_line]
        if len(exact) == 1:
            return exact[0]
        if len(candidates) == 1:
            return candidates[0]
    msg = f"the symbol table for {fn.__name__} at {path}:{absolute_line} is missing"
    raise RuntimeError(msg)


class _EffectAnalysis(ast.NodeVisitor):
    def __init__(
        self,
        local_functions: set[str],
        known: Callable[[str], bool],
        effect: Callable[[str], EffectClass],
        host_island_names: frozenset[str],
        space_locals: set[str],
    ) -> None:
        self.local_functions = local_functions
        self.known = known
        self.declared_effect = effect
        self.host_island_names = host_island_names
        self.space_locals = space_locals
        self.result = EffectClass.pureStructural

    def _join(self, effect: EffectClass) -> None:
        self.result = self.result.join(effect)

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            self._join(EffectClass.oracleIO)
        else:
            name = node.func.id
            if name in self.host_island_names:
                self._join(EffectClass.oracleIO)
            elif name == "match":
                # ``match(pattern, body)`` consults the definition's space
                # and may produce several bindings, but it does not mutate
                # that space. Calls nested in the first argument are pattern
                # constructors rather than executable operations, while the
                # body may contain real calls and must still be visited.
                self._join(EffectClass.nondeterministicReadOnly)
                for argument in node.args[1:]:
                    self.visit(argument)
                for keyword in node.keywords:
                    self.visit(keyword.value)
                return
            if name in self.local_functions:
                pass
            elif name in _PYTHON_CALL_EFFECTS:
                self._join(_PYTHON_CALL_EFFECTS[name])
            elif name in _CONTROL_EFFECTS:
                self._join(_CONTROL_EFFECTS[name])
            elif (resolved := resolve_known_name(name, self.known)) is not None:
                self._join(self.declared_effect(resolved))
            elif not name[:1].isupper():
                # An unknown capitalized call is a data constructor. An
                # unknown lowercase call will be refused by compilation, but
                # is conservatively host-observable if this analysis is used alone.
                self._join(EffectClass.oracleIO)
        self.generic_visit(node)

    def visit_Yield(self, node: ast.Yield) -> None:
        self._join(EffectClass.nondeterministicReadOnly)
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self._join(EffectClass.nondeterministicReadOnly)
        self.generic_visit(node)

    def visit_Delete(self, node: ast.Delete) -> None:
        self._join(EffectClass.writesState)
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id in self.space_locals:
            self._join(EffectClass.writesState)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # A `.value` attribute is the State cell surface, which the compiler
        # lowers to the engine's own state heads. Its context says which one:
        # the same node appears with Store on the left of `cell.value += 1`
        # and with Load in `return cell.value`, so a read stays a read rather
        # than being charged the write's rank. This joined rather than
        # assigned, because a body's effect is the join over its statements
        # and a plain assignment here would erase a stronger sibling.
        if node.attr == "value":
            self._join(
                EffectClass.readOnlyLookup
                if isinstance(node.ctx, ast.Load)
                else EffectClass.writesState
            )
        self.generic_visit(node)


def derive_definition_facts(
    fn: types.FunctionType,
    definition: ast.FunctionDef,
    *,
    source: str,
    source_lines: list[str],
    first_line: int,
    known: Callable[[str], bool],
    effect: Callable[[str], EffectClass],
    host_island_names: frozenset[str],
    space_locals: set[str] | None = None,
) -> DefinitionFacts:
    """Derive facts from the same syntax tree compilation consumes."""
    path = inspect.getsourcefile(fn) or inspect.getfile(fn)
    if not (path.startswith("<") and path.endswith(">")):
        path = str(Path(path).resolve())
    start_line = first_line + definition.lineno - 1
    end_line = first_line + (definition.end_lineno or definition.lineno) - 1
    definition_line = source_lines[definition.lineno - 1]
    indentation = definition_line[: len(definition_line) - len(definition_line.lstrip())]
    indentation_bytes = len(indentation.encode("utf-8"))
    span = SourceSpan(
        path,
        start_line,
        indentation_bytes + definition.col_offset,
        end_line,
        indentation_bytes + (definition.end_col_offset or definition.col_offset),
    )

    table = _function_table(fn, source, path, start_line)
    free_variables = tuple(
        sorted(name for name in table.get_identifiers() if table.lookup(name).is_free())
    )

    local_functions = {
        node.name
        for node in ast.walk(definition)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    effects = _EffectAnalysis(
        local_functions, known, effect, host_island_names, space_locals or set()
    )
    for statement in definition.body:
        effects.visit(statement)

    return DefinitionFacts(
        span,
        ast.get_docstring(definition, clean=True),
        free_variables,
        effects.result,
    )
