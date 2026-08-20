"""Purpose: derive immutable definition metadata from the Python syntax that
``@define`` already parses: an absolute source span, the source docstring,
lexical free variables, and whether every call is in the declared pure set.
Guarantees:
  - derivation reads syntax and symbol tables without executing user code
    [tested: test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=214a34885feb4fd1caf26c67143d6a3b0506e824]
  - Python 3.14 annotation scopes cannot be mistaken for the function scope
    whose free variables are reported [tested:
    test_each_ast_derived_fact_replaces_the_flag_it_supersedes;
    commit=214a34885feb4fd1caf26c67143d6a3b0506e824]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import ast
import inspect
import symtable
import tokenize
import types
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import NamedTuple


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
    pure: bool


_PURE_CONTROL_CALLS = frozenset({"collapse", "empty", "superpose"})
_PURE_PYTHON_CALLS = frozenset(
    {"abs", "len", "max", "min", "pow", "range", "repr", "round", "sorted", "str", "sum"}
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
            if table.get_type() == "function"
            and table.get_name() == fn.__name__
        ]
        exact = [table for table in candidates if table.get_lineno() == absolute_line]
        if len(exact) == 1:
            return exact[0]
        if len(candidates) == 1:
            return candidates[0]
    raise RuntimeError(
        f"the symbol table for {fn.__name__} at {path}:{absolute_line} is missing"
    )


class _Purity(ast.NodeVisitor):
    def __init__(
        self,
        local_functions: set[str],
        known: Callable[[str], bool],
        pure: Callable[[str], bool],
    ) -> None:
        self.local_functions = local_functions
        self.known = known
        self.is_declared_pure = pure
        self.result = True

    def visit_Call(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Name):
            self.result = False
        else:
            name = node.func.id
            if name == "match":
                self.result = False
            elif (
                name in self.local_functions
                or name in _PURE_CONTROL_CALLS
                or name in _PURE_PYTHON_CALLS
            ):
                pass
            elif self.known(name):
                self.result = self.result and self.is_declared_pure(name)
            elif not name[:1].isupper():
                # An unknown capitalized call is a data constructor. An
                # unknown lowercase call will be refused by compilation, but
                # is conservatively impure if this analysis is used alone.
                self.result = False
        self.generic_visit(node)


def derive_definition_facts(
    fn: types.FunctionType,
    definition: ast.FunctionDef,
    *,
    source: str,
    source_lines: list[str],
    first_line: int,
    known: Callable[[str], bool],
    pure: Callable[[str], bool],
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
        sorted(
            name
            for name in table.get_identifiers()
            if table.lookup(name).is_free()
        )
    )

    local_functions = {
        node.name
        for node in ast.walk(definition)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    purity = _Purity(local_functions, known, pure)
    for statement in definition.body:
        purity.visit(statement)

    return DefinitionFacts(
        span,
        ast.get_docstring(definition, clean=True),
        free_variables,
        purity.result,
    )
