"""Purpose: construct native applications in Python's argument evaluation order.

Guarantees:
  - expansion and keyword-group merge order follow Python's call construction
    [tested: test_expanded_calls_match_python_operand_and_mapping_failure_order;
    commit=10ef2f6958af451bcc3e651e0e0ccc7cc8ec7ce8]
"""

from __future__ import annotations

import ast

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._compile.context import CompilerContext


def expanded(node: ast.Call) -> bool:
    return any(isinstance(value, ast.Starred) for value in node.args) or any(keyword.arg is None for keyword in node.keywords)


def dynamic(compiler: CompilerContext, node: ast.Call) -> bool:
    callee = node.func
    if (isinstance(callee, ast.Subscript) and isinstance(callee.value, ast.Name)
            and callee.value.id in compiler.builders and callee.value.id not in compiler.scope):
        return False
    return not isinstance(node.func, (ast.Name, ast.Attribute)) or (isinstance(node.func, ast.Name) and node.func.id in compiler.scope)


def application(compiler: CompilerContext, node: ast.Call, *, consumer: str = "value", callee: Atom | None = None) -> Atom:
    """Evaluate operands, bind their syntax, then execute the assembled term."""
    compiler.runtime_ops.update(("_python-bind-call", "_python-merge-keywords", "py-dict"))
    if consumer == "iterable":
        compiler.runtime_ops.add("py-iter-once")
    function = Variable(compiler._temp("call-function"))
    bindings = [(compiler.expression(node.func) if callee is None else callee, function)]
    deferred = len(node.args) == 1 and isinstance(node.args[0], ast.Starred)
    pieces = []
    for source in node.args:
        spread = isinstance(source, ast.Starred)
        value = compiler.expression(source.value if isinstance(source, ast.Starred) else source)
        if spread and not deferred:
            compiler.runtime_ops.add("py-iter-once")
            value = _expr(S.collapse, _expr(S["py-iter-once"], value))
        variable = Variable(compiler._temp("call-argument"))
        bindings.append((value, variable))
        pieces.append(variable if spread else _expr(S.noeval, Expression([variable])))
    positional: Atom = _expr(S.noeval, Expression([]))
    if deferred:
        positional = pieces[0]
    else:
        for piece in reversed(pieces):
            positional = _expr(S.append, piece, positional)
    arguments = Variable(compiler._temp("call-positionals"))
    bindings.append((positional, arguments))
    keywords = Variable(compiler._temp("call-keywords"))
    bindings.append((_expr(S["py-dict"], Expression([])), keywords))
    named = []
    mapping: Atom
    for index, keyword in enumerate(node.keywords):
        value = Variable(compiler._temp("call-keyword"))
        bindings.append((compiler.expression(keyword.value), value))
        if keyword.arg is not None:
            named.append(_expr(S.entry, Grounded(keyword.arg), value))
            if index + 1 < len(node.keywords) and node.keywords[index + 1].arg is not None:
                continue
            mapping = Expression(named)
            named = []
        else:
            mapping = value
        merged = Variable(compiler._temp("call-keywords"))
        bindings.append((_expr(S["_python-merge-keywords"], keywords, mapping), merged))
        keywords = merged
    # CPython carries a lone *operand to CALL_FUNCTION_EX; mixed positional
    # groups use LIST_EXTEND before keywords. Named keyword runs merge as one
    # group after all their values are read. These timings are observable.
    # https://github.com/python/cpython/blob/v3.14.4/Python/codegen.c#L4022-L4072
    if deferred:
        compiler.runtime_ops.add("py-iter-once")
        materialized = Variable(compiler._temp("call-positionals"))
        bindings.append((_expr(S.collapse, _expr(S["py-iter-once"], arguments)), materialized))
        arguments = materialized
    assembled = Variable(compiler._temp("call-application"))
    bindings.append((_expr(S["_python-bind-call"], Symbol("&self"), function, arguments, keywords, Grounded(consumer)), assembled))
    body = _expr(S.eval, assembled)
    for value, variable in reversed(bindings):
        # The pattern is the fresh variable. A callable value may contain a
        # segment binder; putting that syntax in chain's pattern position
        # asks the native sequence matcher to interpret the callable as a gap.
        body = _expr(S.let, variable, value, body)
    return body
