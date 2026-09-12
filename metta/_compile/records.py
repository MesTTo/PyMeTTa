"""Purpose: lower declared constructors and fields using static receiver types.

Guarantees:
  - annotations, constructor calls and declared fields carry receiver types;
    ordinary unknown host attributes keep their existing island meaning
    [tested: test_class_constructors_compile_fields; commit=WORKTREE]
  - value construction uses the compiler's SSA bindings and subsequent value
    writes refuse with a replacement remedy [tested:
    test_class_value_post_init_and_write_refusal; commit=WORKTREE]
"""

from __future__ import annotations

import ast
import copy
import inspect
from typing import Any

from metta._atoms.factories import Atom, S, Symbol, Variable, _expr
from metta._compile.context import CompilerContext
from metta._errors.errors import CompileError
from metta._lazy import lazy


class _LiteralField(ast.Attribute):
    """A field whose name came from a string rather than an identifier."""


def declared(value: Any) -> Any:
    return lazy('metta._declare.classes').declaration(value)


def field_name(compiler: CompilerContext, name: str) -> str:
    if compiler.class_context is None:
        return name
    return lazy('metta._declare.classes')._mangle(compiler.class_context, name)


def static_value(compiler: CompilerContext, node: ast.expr) -> Any:
    if isinstance(node, ast.Name) and node.id not in compiler.scope:
        return compiler.host_value(node.id)
    if isinstance(node, ast.Attribute):
        parent = static_value(compiler, node.value)
        if isinstance(parent, type):
            return inspect.getattr_static(parent, node.attr, None)
    return None


def record_type(compiler: CompilerContext, node: ast.expr) -> Any:
    if isinstance(node, ast.Name):
        return declared(compiler.record_locals.get(node.id))
    if isinstance(node, ast.Call):
        return declared(static_value(compiler, node.func))
    if isinstance(node, ast.Attribute):
        owner = record_type(compiler, node.value)
        field = owner.field(field_name(compiler, node.attr)) if owner is not None else None
        return declared(field.annotation) if field is not None else None
    return None


def field_number(compiler: CompilerContext, node: ast.expr) -> bool:
    if not isinstance(node, ast.Attribute):
        return False
    owner = record_type(compiler, node.value)
    field = owner.field(field_name(compiler, node.attr)) if owner is not None else None
    return field is not None and field.annotation in (int, float)


def field_key(name: str) -> str:
    return f"class-field-{name}"


def value_receiver(compiler: CompilerContext) -> Atom:
    construction = compiler.construction
    assert construction is not None
    plan, _receiver = construction
    missing = [field.name for field in plan.stored_fields if field_key(field.name) not in compiler.scope]
    if missing:
        msg = f"{plan.name} is used before fields {', '.join(missing)} are initialized; assign its fields before passing self"
        raise CompileError(
            msg,
            construct="constructor fields", line=1,
        )
    return plan.term(*(Variable(compiler.scope[field_key(field.name)]) for field in plan.stored_fields))


def field_call(owner: Any, name: str, *arguments: Atom, write: bool = False) -> Atom:
    head = owner.accessor(name, write=write)
    body = _expr(head, *arguments)
    if not owner.public_accessors:
        return _expr(S.evalc, body, Symbol(owner.space.name))
    return body


def attribute(compiler: CompilerContext, node: ast.Attribute) -> Atom | None:
    owner = record_type(compiler, node.value)
    if owner is None:
        owner = declared(static_value(compiler, node.value))
        name = field_name(compiler, node.attr)
        if owner is not None and name in owner.classvars:
            return field_call(owner, name)
        return None
    field = owner.field(field_name(compiler, node.attr))
    if field is None:
        return None
    if compiler.construction is not None:
        plan, receiver = compiler.construction
        if plan.grain == "value" and isinstance(node.value, ast.Name) and node.value.id == receiver:
            key = field_key(field.name)
            if key not in compiler.scope:
                msg = f"{plan.name}.{field.name} is read before initialization; assign it before this read"
                raise CompileError(
                    msg,
                    construct="constructor field", line=node.lineno,
                )
            return Variable(compiler.scope[key])
    return field_call(owner, field.name, compiler.expression(node.value))


def binding(compiler: CompilerContext, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> tuple[Atom, Atom] | None:
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            return None
        target = node.targets[0]
    else:
        target = node.target
    if not isinstance(target, ast.Attribute):
        return None
    owner = record_type(compiler, target.value)
    if owner is None:
        return None
    name = target.attr if isinstance(target, _LiteralField) else field_name(compiler, target.attr)
    field = owner.field(name)
    if field is None:
        msg = f"{owner.name}.{target.attr} is not a declared field; annotate the field on {owner.name} before assigning it"
        raise CompileError(
            msg,
            construct="closed field", line=node.lineno,
        )
    constructing = compiler.construction is not None and isinstance(target.value, ast.Name) and target.value.id == compiler.construction[1]
    if owner.grain == "value":
        if not constructing:
            msg = f"{owner.name} is a value; use dataclasses.replace(value, {field.name}=...) to construct a replacement"
            raise CompileError(
                msg,
                construct="value field write", line=node.lineno,
            )
        rewritten = copy.copy(node)
        field_target = ast.copy_location(ast.Name(id=field_key(field.name), ctx=ast.Store()), target)
        if isinstance(rewritten, ast.Assign):
            rewritten.targets = [field_target]
        else:
            rewritten.target = field_target
        return compiler._binding(rewritten)
    if node.value is None:
        msg = "a field annotation needs a value to write"
        raise CompileError(msg, construct="field annotation", line=node.lineno)
    value = compiler.expression(node.value)
    if isinstance(node, ast.AugAssign):
        left = ast.copy_location(ast.Attribute(value=target.value, attr=target.attr, ctx=ast.Load()), target)
        value = compiler._binop_atom(
            node.op, compiler.expression(left), value, node.lineno,
            native=field_number(compiler, left) and compiler._native_number(node.value),
        )
    return Variable(compiler._temp("field-write")), field_call(owner, field.name, compiler.expression(target.value), value, write=True)


def call(compiler: CompilerContext, node: ast.Call) -> Atom | None:
    owner = declared(static_value(compiler, node.func))
    if owner is not None:
        if any(isinstance(arg, ast.Starred) for arg in node.args) or any(keyword.arg is None for keyword in node.keywords):
            return None
        try:
            bound = owner.signature.bind(*node.args, **{keyword.arg: keyword.value for keyword in node.keywords if keyword.arg is not None})
        except TypeError as error:
            msg = f"{owner.name} constructor: {error}"
            raise CompileError(msg, construct="constructor arguments", line=node.lineno) from error
        compiler.class_dependencies.add(owner.cls)
        expressions = [*node.args, *(keyword.value for keyword in node.keywords)]
        supplied = {id(expression): Variable(compiler._temp("constructor-argument")) for expression in expressions}
        evaluated = [(compiler.expression(expression), supplied[id(expression)]) for expression in expressions]
        arguments = owner.arguments(bound.arguments, lambda expression: supplied[id(expression)])
        body = _expr(Symbol(f"make-{owner.name}"), *arguments)
        if any(name not in bound.arguments for name in owner.defaults):
            body = _expr(S.transaction, body)
        # Python evaluates supplied arguments in source order before entering
        # the constructor. Default factories belong to the constructor itself.
        for value, variable in reversed(evaluated):
            body = _expr(S.chain, value, variable, body)
        return body
    return None


def initialization_assignment(compiler: CompilerContext, node: ast.expr) -> ast.Assign | None:
    if (
        compiler.construction is not None
        and isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and static_value(compiler, node.func.value) is object
        and node.func.attr == "__setattr__"
        and len(node.args) == 3 and not node.keywords
        and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)
    ):
        # Python mangles identifiers at compilation, never string values.
        target = ast.copy_location(_LiteralField(value=node.args[0], attr=node.args[1].value, ctx=ast.Store()), node)
        return ast.copy_location(ast.Assign(targets=[target], value=node.args[2]), node)
    return None


def remember_binding(compiler: CompilerContext, name: str, node: ast.expr, annotation: ast.expr | None) -> None:
    owner = record_type(compiler, node)
    if annotation is not None and compiler._annotation_value is not None:
        try:
            annotated = declared(compiler._annotation_value(annotation))
        except CompileError:
            # The binding's annotation claim owns diagnostics. A local MeTTa
            # type alias need not also have a Python namespace binding.
            pass
        else:
            owner = annotated or owner
    if owner is None:
        compiler.record_locals.pop(name, None)
    else:
        compiler.record_locals[name] = owner.cls
