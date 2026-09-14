"""Purpose: lower declared constructors, fields and methods from receiver types.

Guarantees:
  - ordinary, qualified and super calls retain their original receiver and
    lexical provider [tested:
    test_unbound_private_and_super_values_keep_the_lexical_provider; commit=WORKTREE]
  - mutable field bindings expose a write status for statement continuation
    selection [tested: test_refused_field_writes_stop_their_compiled_continuation;
    commit=9eebb619cb02f267e1d541a7d6e989b990f68982]
  - field assignments preserve computed syntax values and evaluate the target
    once in Python order [tested:
    test_field_assignment_keeps_computed_syntax_values,
    test_field_assignment_evaluates_its_target_once_in_python_order; commit=2070690afe0f1e6c580ebdb86e418e5a85bcc02d]
  - class calls evaluate supplied expressions before default computations and
    preserve their resulting atom values [tested:
    test_constructor_arguments_preserve_values_and_run_factories,
    test_constructor_sources_finish_before_factories_and_post_init; commit=310a9d8b547a77412a518a37ab79fba073eb22ac]
  - annotations, constructor calls and declared fields carry receiver types;
    ordinary unknown host attributes keep their existing island meaning
    [tested: test_class_constructors_compile_fields; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - value construction uses the compiler's SSA bindings and subsequent value
    writes refuse with a replacement remedy [tested:
    test_class_value_post_init_and_write_refusal; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
"""

from __future__ import annotations

import ast
import builtins
import copy
import inspect
from dataclasses import dataclass
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._catalog.call_values import apply_sources
from metta._compile import call_syntax
from metta._compile.context import CompilerContext
from metta._errors.errors import CompileError
from metta._lazy import lazy


class _LiteralField(ast.Attribute):
    """A field whose name came from a string rather than an identifier."""


@dataclass(frozen=True)
class MethodReference:
    """A lexical lookup; cooperative super can precede its eventual provider."""

    method: Any
    home: Any
    name: str
    receiver: ast.expr | None
    after: type | None

    @property
    def result_type(self) -> Any:
        return self.method.result_type if self.method is not None else Any

    @property
    def generator(self) -> bool:
        return self.method is not None and self.method.generator

    @property
    def private(self) -> bool:
        return self.name.startswith("_")


def declared(value: Any) -> Any:
    return lazy('metta._declare.classes').declaration(value)


def host_operand(compiler: CompilerContext, name: str) -> Atom:
    """Project a declared local before an island consumes Python values."""
    value = Variable(compiler.scope[name])
    owner = declared(compiler.record_locals.get(name))
    if owner is None:
        return value
    compiler.class_dependencies.add(owner.cls)
    return owner.host_value(value)


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
        constructor = declared(static_value(compiler, node.func))
        if constructor is not None:
            return constructor
        member = method_reference(compiler, node.func)
        return declared(member.result_type) if member is not None else None
    if isinstance(node, ast.Attribute):
        owner = record_type(compiler, node.value)
        field = owner.field(field_name(compiler, node.attr)) if owner is not None else None
        return declared(field.annotation) if field is not None else None
    return None


def field_number(compiler: CompilerContext, node: ast.expr) -> bool:
    if isinstance(node, ast.Call):
        member = method_reference(compiler, node.func)
        return member is not None and member.result_type in (int, float)
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
        static_owner = declared(static_value(compiler, node.value))
        name = field_name(compiler, node.attr)
        if static_owner is not None and name in static_owner.classvars:
            return field_call(static_owner, name)
    field = owner.field(field_name(compiler, node.attr)) if owner is not None else None
    if field is None:
        member = method_reference(compiler, node)
        if member is None:
            return None
        method, home, receiver, after = member.method, member.home, member.receiver, member.after
        if receiver is None:
            return _expr(S.noeval, method.__metta__())
        head = lazy('metta._declare.methods').selector(home, member.name, after=after, value=True)
        result = _expr(head, compiler.expression(receiver))
        return _expr(S.evalc, result, Symbol(home.space.name)) if member.private else result
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


def binding(compiler: CompilerContext, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> tuple[Atom | None, Atom] | None:
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
        binding_target, binding_value = compiler._binding(rewritten)
        return binding_target, lazy('metta._declare.field_values').adopted(owner, field, binding_value)
    if node.value is None:
        msg = "a field annotation needs a value to write"
        raise CompileError(msg, construct="field annotation", line=node.lineno)
    value = compiler.expression(node.value)
    receiver_source = compiler.expression(target.value)
    receiver = Variable(compiler._temp("field-receiver")) if isinstance(node, ast.AugAssign) else receiver_source
    if isinstance(node, ast.AugAssign):
        left = ast.copy_location(ast.Attribute(value=target.value, attr=target.attr, ctx=ast.Load()), target)
        value = compiler._binop_atom(
            node.op, field_call(owner, field.name, receiver), value, node.lineno,
            native=field_number(compiler, left) and compiler._native_number(node.value),
        )
    written = Variable(compiler._temp("field-value"))
    body = _expr(S.let, written, value, field_call(owner, field.name, receiver, written, write=True))
    if isinstance(node, ast.AugAssign):
        body = _expr(S.let, receiver, receiver_source, body)
    return None, body


def call(compiler: CompilerContext, node: ast.Call) -> Atom | None:
    member = method_reference(compiler, node.func)
    if member is not None:
        method, home, receiver, after = member.method, member.home, member.receiver, member.after
        if call_syntax.expanded(node):
            return call_syntax.application(compiler, node)
        arguments = node.args
        qualified = receiver is None
        if qualified:
            if not arguments:
                return call_syntax.application(compiler, node)
            receiver, *arguments = arguments
        sources = [receiver, *arguments, *(keyword.value for keyword in node.keywords)]
        supplied = {id(source): Variable(compiler._temp("method-operand")) for source in sources}
        evaluated = [(compiler.expression(source), supplied[id(source)]) for source in sources]
        params = tuple(method.call_signature.parameters.values()) if method is not None else ()
        direct = method is not None and not node.keywords and len(arguments) == len(params) and all(
            parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for parameter in params
        )
        if qualified:
            head = Symbol(method.name if direct else method.apply_name)
        else:
            head = lazy('metta._declare.methods').selector(home, member.name, after=after, applied=not direct)
        operands: list[Atom] = [supplied[id(receiver)]]
        values = [supplied[id(argument)] for argument in arguments]
        if direct:
            operands.extend(values)
        else:
            operands.extend((Expression(values), Expression([
                Expression([Grounded(keyword.arg), supplied[id(keyword.value)]])
                for keyword in node.keywords
            ])))
        body = _expr(head, *operands)
        if member.private:
            body = _expr(S.evalc, body, Symbol((method.owner if qualified else home).space.name))
        for value, variable in reversed(evaluated):
            body = _expr(S.chain, value, variable, body)
        return body
    if isinstance(node.func, ast.Name) and node.func.id not in compiler.scope:
        function = compiler.host_value(node.func.id)
        if function is builtins.type and len(node.args) == 1 and not node.keywords and record_type(compiler, node.args[0]) is not None:
            return _expr(S["get-type"], compiler.expression(node.args[0]))
        if function is builtins.isinstance and len(node.args) == 2 and not node.keywords:
            target = declared(static_value(compiler, node.args[1]))
            if target is not None:
                compiler.class_dependencies.add(target.cls)
                kind = Variable(compiler._temp("instance-type"))
                matches = _expr(S.collapse, _expr(S.chain, _expr(S["get-type"], compiler.expression(node.args[0])), kind,
                                               _expr(S["if"], _expr(S["=="], kind, Symbol(target.name)), Grounded(value=True), _expr(S.empty))))
                return _expr(S["not"], _expr(S["=="], matches, Expression([])))
    owner = declared(static_value(compiler, node.func))
    if owner is not None:
        if call_syntax.expanded(node):
            compiler.class_dependencies.add(owner.cls)
            image = lazy('metta._declare.constructors').image(owner)
            return call_syntax.application(compiler, node, callee=_expr(S.noeval, image))
        try:
            owner.signature.bind(*node.args, **{keyword.arg: keyword.value for keyword in node.keywords if keyword.arg is not None})
        except TypeError as error:
            msg = f"{owner.name} constructor: {error}"
            raise CompileError(msg, construct="constructor arguments", line=node.lineno) from error
        compiler.class_dependencies.add(owner.cls)
        expressions = [*node.args, *(keyword.value for keyword in node.keywords)]
        supplied = {id(expression): Variable(compiler._temp("constructor-argument")) for expression in expressions}
        evaluated = [(compiler.expression(expression), supplied[id(expression)]) for expression in expressions]
        parameters = tuple(owner.signature.parameters.values())
        direct = not node.keywords and len(node.args) == len(parameters) and all(
            parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for parameter in parameters
        )
        constructor_args = [supplied[id(argument)] for argument in node.args]
        if direct:
            body = _expr(Symbol(f"make-{owner.name}"), *constructor_args)
        else:
            keywords = Expression([Expression([Grounded(keyword.arg), supplied[id(keyword.value)]])
                                   for keyword in node.keywords])
            application = apply_sources(Symbol(f"make-{owner.name}:apply"), (
                _expr(S.noeval, Expression(constructor_args)), _expr(S.noeval, keywords),
            ))
            body = _expr(S.evalc, application, Symbol(owner.space.name))
        # Python evaluates supplied arguments in source order before entering
        # the constructor. Default factories belong to the constructor itself.
        for value, variable in reversed(evaluated):
            body = _expr(S.chain, value, variable, body)
        return body
    return None


def method_reference(compiler: CompilerContext, node: ast.expr) -> Any:
    """Resolve a descriptor from receiver structure and lexical class context."""
    if not isinstance(node, ast.Attribute):
        return None
    after = None
    receiver: ast.expr | None = node.value
    if (
        isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "super" and not node.value.keywords
        and compiler.host_value("super") is builtins.super
    ):
        if not node.value.args and compiler.class_context is not None and compiler.method_receiver is not None:
            after = compiler.class_context
            receiver = ast.copy_location(ast.Name(id=compiler.method_receiver, ctx=ast.Load()), node.value)
        elif len(node.value.args) == 2 and declared(static_value(compiler, node.value.args[0])) is not None:
            after = static_value(compiler, node.value.args[0])
            receiver = node.value.args[1]
        else:
            return None
        home = declared(after)
    else:
        home = record_type(compiler, node.value)
        if home is None:
            home = declared(static_value(compiler, node.value))
            receiver = None
    if home is None:
        return None
    name = field_name(compiler, node.attr)
    method = lazy('metta._declare.methods').selected(home, name, after=after)
    if method is None and after is None:
        return None
    compiler.class_dependencies.add(home.cls)
    return MethodReference(method, home, name, receiver, after)


def answer_stream(compiler: CompilerContext, node: ast.expr) -> bool:
    """Read method cardinality beside the existing ordinary-call declaration."""
    if not isinstance(node, ast.Call):
        return False
    member = method_reference(compiler, node.func)
    if member is not None:
        return member.generator
    if isinstance(node.func, ast.Name):
        return compiler.nondet(compiler._resolved_call_name(node.func.id))
    mentioned = compiler._mention(node.func)
    return isinstance(mentioned, Symbol) and compiler.nondet(mentioned.name)


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
