"""Purpose: construct native applications in Python's argument evaluation order.

Guarantees:
  - result consumers use the call-values domain, preserving its native
    strings [tested: test_call_consumer_source.CallConsumerSourceTests;
    commit=b8f5c6b9a3ef41b173d6af81e1b9bb526977a908]
  - value consumers execute through _python-call-value with the keyword
    frame crossing as pairs, so the callee receives the atoms and held values
    themselves [tested: test_compiled_host_calls_keep_data_out_of_keyword_control,
    test_host_call_frames_do_not_inspect_callable_signatures; commit=WORKTREE]
  - carried values and host-island locals remain data inside independent call
    frames [tested: test_compiled_host_calls_keep_data_out_of_keyword_control,
    test_carried_native_calls_hold_completed_operand_values; commit=86756da11eade288973b0dfaab7486a29e598cfd]
  - native and borrowed positional sequences retain their atom elements
    [tested: test_expanded_arguments_preserve_native_atom_values; commit=86756da11eade288973b0dfaab7486a29e598cfd]
  - each Python call form retains its materializer's length effects
    [tested: test_expanded_arguments_follow_python_length_hint_effects;
    commit=86756da11eade288973b0dfaab7486a29e598cfd]
  - expansion and keyword-group merge order follow Python's call construction
    [tested: test_expanded_calls_match_python_operand_and_mapping_failure_order;
    commit=86756da11eade288973b0dfaab7486a29e598cfd]
"""

from __future__ import annotations

import ast

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._catalog import call_signatures
from metta._catalog.call_values import CallConsumer
from metta._compile.context import CompilerContext


def expanded(node: ast.Call) -> bool:
    return any(isinstance(value, ast.Starred) for value in node.args) or any(keyword.arg is None for keyword in node.keywords)


def dynamic(compiler: CompilerContext, node: ast.Call) -> bool:
    callee = node.func
    if (isinstance(callee, ast.Subscript) and isinstance(callee.value, ast.Name)
            and callee.value.id in compiler.builders and callee.value.id not in compiler.scope):
        return False
    return not isinstance(node.func, (ast.Name, ast.Attribute)) or (isinstance(node.func, ast.Name) and node.func.id in compiler.scope)


def value_source(value: Atom) -> Atom:
    """Read a completed atom; only a compiled expression describes computation."""
    return value if isinstance(value, Expression) else _expr(S.noeval, value)


def bound_application(compiler: CompilerContext, function: Atom, positional: Atom,
                      keywords: Atom, *, consumer: CallConsumer = "value") -> Atom:
    """Execute the live application described by independent argument frames.

    A value consumer calls through the seam, `_python-call-value`, which binds
    the callable value and evaluates it in its home for one answer. The
    keyword frame is the real dictionary the merges above assembled, and the
    seam takes keyword data as pairs, so it crosses as `(py-dict-pairs frame)`
    at this boundary rather than the seam accepting a grounded mapping.
    """
    if consumer == "value":
        compiler.runtime_ops.update(("_python-call-value", "py-dict", "py-dict-pairs"))
        pairs = Variable(compiler._temp("call-keyword-pairs"))
        return _expr(S.let, pairs, _expr(S["py-dict-pairs"], keywords),
                     _expr(S["_python-call-value"], Symbol("&self"), function, positional, pairs))
    compiler.runtime_ops.update(("_python-bind-call", "py-dict"))
    assembled = Variable(compiler._temp("call-application"))
    binding = _expr(S["_python-bind-call"], Symbol("&self"), function, positional, keywords, Grounded(consumer))
    return _expr(S.let, assembled, binding, _expr(S.eval, assembled))


def application(compiler: CompilerContext, node: ast.Call, *, consumer: CallConsumer = "value", callee: Atom | None = None) -> Atom:
    """Evaluate operands, bind their syntax, then execute the assembled term."""
    compiler.runtime_ops.update(("_python-bind-call", "_python-merge-keywords", "py-dict"))
    if consumer == "iterable":
        compiler.runtime_ops.add("py-iter-once")
    function = Variable(compiler._temp("call-function"))
    bindings = [(value_source(compiler.expression(node.func) if callee is None else callee), function)]
    deferred = len(node.args) == 1 and isinstance(node.args[0], ast.Starred)
    pieces = []
    for source in node.args:
        spread = isinstance(source, ast.Starred)
        value = compiler.expression(source.value if isinstance(source, ast.Starred) else source)
        variable = Variable(compiler._temp("call-argument"))
        bindings.append((value_source(value), variable))
        if spread and not deferred:
            compiler.runtime_ops.add("_python-expand-positional")
            materialized = Variable(compiler._temp("call-positionals"))
            bindings.append((_expr(S["_python-expand-positional"], variable, call_signatures.annotation(list)), materialized))
            variable = materialized
        pieces.append(variable if spread else _expr(S.noeval, Expression([variable])))
    positional: Atom = _expr(S.noeval, Expression([]))
    if deferred:
        positional = pieces[0]
    else:
        for piece in reversed(pieces):
            # union-atom returns Atom: the assembled run is data, including
            # executable-looking children. append's Undefined result re-enters
            # reduction here. lib_builtin_types declares both contracts.
            positional = _expr(S["union-atom"], piece, positional)
    arguments = Variable(compiler._temp("call-positionals"))
    bindings.append((positional, arguments))
    keywords = Variable(compiler._temp("call-keywords"))
    bindings.append((_expr(S["py-dict"], Expression([])), keywords))
    named = []
    mapping: Atom
    for index, keyword in enumerate(node.keywords):
        value = Variable(compiler._temp("call-keyword"))
        bindings.append((value_source(compiler.expression(keyword.value)), value))
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
        compiler.runtime_ops.add("_python-expand-positional")
        materialized = Variable(compiler._temp("call-positionals"))
        bindings.append((_expr(S["_python-expand-positional"], arguments, call_signatures.annotation(tuple)), materialized))
        arguments = materialized
    body = bound_application(compiler, function, arguments, keywords, consumer=consumer)
    for value, variable in reversed(bindings):
        # The pattern is the fresh variable. A callable value may contain a
        # segment binder; putting that syntax in chain's pattern position
        # asks the native sequence matcher to interpret the callable as a gap.
        body = _expr(S.let, variable, value, body)
    return body
