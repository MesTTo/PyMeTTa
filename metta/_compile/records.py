"""Purpose: lower declared constructors, fields and methods from receiver types.

Guarantees:
  - ordinary, qualified and super calls retain their original receiver and
    lexical provider [tested:
    test_unbound_private_and_super_values_keep_the_lexical_provider; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
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
  - syntax Python routes to a special method lowers to the operand's own
    dispatch entry when its static type is a declared class: operators and
    their reflected and in-place partners, comparisons, the builtin calls the
    reference routes, subscripts and their writes and deletes, containment,
    truth, instance calls, iteration through a generator `__iter__`, `with`
    through enter and exit, and keyword class patterns through
    `__match_args__`; an operand of unknown type keeps the builtin [tested:
    test_operators_on_a_declared_value_lower_to_its_special_methods,
    test_containers_iterate_index_contain_and_truth_test_through_their_methods,
    test_calls_context_managers_and_augmented_assignment_reach_their_methods,
    test_keyword_class_patterns_place_fields_through_match_args; commit=WORKTREE]
  - the operator form costs exactly the method call it stands for [tested:
    test_an_operator_costs_exactly_the_method_call_it_stands_for; commit=WORKTREE]
  - a property read is its getter's call and a property write its setter's
    [tested: test_properties_static_and_class_methods_and_memoised_members; commit=WORKTREE]
"""

from __future__ import annotations

import ast
import builtins
import copy
import inspect
from dataclasses import dataclass
from typing import Any

from metta._atoms import operators
from metta._atoms._python_protocols import BY_OPERATOR
from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._catalog.call_values import apply_sources
from metta._compile import call_syntax
from metta._compile.context import CompilerContext, next_aux_serial
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
        # A special method is a protocol name, not a private member.
        return self.name.startswith("_") and not (self.name.startswith("__") and self.name.endswith("__"))


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
        if member is not None:
            return declared(member.result_type)
        if isinstance(node.func, ast.Name) and node.func.id in compiler.scope:
            return _protocol_result(compiler, node.func, "__call__")
        return None
    if isinstance(node, ast.Attribute):
        owner = record_type(compiler, node.value)
        field = owner.field(field_name(compiler, node.attr)) if owner is not None else None
        if field is not None:
            return declared(field.annotation)
        member = method_reference(compiler, node) if owner is not None else None
        return declared(member.result_type) if member is not None and member.method is not None and member.method.is_property else None
    if isinstance(node, ast.BinOp):
        entry = operators.BY_NODE.get(type(node.op).__name__)
        if entry is None:
            return None
        result = _protocol_result(compiler, node.left, entry.dunder)
        if result is None and entry.reflected is not None:
            result = _protocol_result(compiler, node.right, entry.reflected)
        return result
    if isinstance(node, ast.UnaryOp):
        entry = operators.BY_NODE.get(type(node.op).__name__)
        return _protocol_result(compiler, node.operand, entry.dunder) if entry is not None else None
    if isinstance(node, ast.Subscript) and not isinstance(node.slice, ast.Slice):
        return _protocol_result(compiler, node.value, "__getitem__")
    return None


def _protocol_result(compiler: CompilerContext, node: ast.expr, dunder: str) -> Any:
    """The declared class a special method answers, when the operand's type declares one."""
    member = protocol_member(compiler, node, dunder)
    return declared(member[1].result_type) if member is not None else None


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
    assert construction is not None  # nosec B101 # a value receiver is compiled inside the construction that set it
    plan, _receiver = construction
    missing = [field.name for field in plan.stored_fields if field_key(field.name) not in compiler.scope]
    if missing:
        msg = f"{plan.name} is used before fields {', '.join(missing)} are initialized; assign its fields before passing self"
        raise CompileError(
            msg,
            construct="constructor fields", line=1,
        )
    return plan.term(*(Variable(compiler.scope[field_key(field.name)]) for field in plan.stored_fields))


def field_call(owner: Any, name: str, *arguments: Atom, write: bool = False, delete: bool = False) -> Expression:
    head = owner.accessor(name, write=write, delete=delete)
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
        if method is not None and method.is_property:
            # `obj.area` on a property is the getter's call, the reference's own routing.
            synthesized = ast.Call(func=node, args=[], keywords=[])
            ast.copy_location(synthesized, node)
            return call(compiler, synthesized)
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
    if isinstance(target, ast.Subscript):
        written = subscript_write(compiler, node)
        return None if written is None else (None, written)
    if not isinstance(target, ast.Attribute):
        return None
    owner = record_type(compiler, target.value)
    if owner is None:
        return None
    name = target.attr if isinstance(target, _LiteralField) else field_name(compiler, target.attr)
    field = owner.field(name)
    if field is None:
        getter = lazy('metta._declare.methods').selected(owner, name)
        if getter is not None and getter.setter is not None and node.value is not None:
            # `obj.area = v` on a property is its setter, the reference's own routing;
            # the augmented form reads the property first, as Python does.
            assigned: ast.expr = node.value
            if isinstance(node, ast.AugAssign):
                read = ast.copy_location(ast.Attribute(value=target.value, attr=target.attr, ctx=ast.Load()), target)
                assigned = ast.copy_location(ast.BinOp(left=read, op=node.op, right=node.value), node)
            stored = protocol_call(compiler, target.value, getter.setter.python_name, assigned, at=node)
            return None if stored is None else (None, stored)
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
    if isinstance(node.func, ast.Name) and node.func.id in compiler.scope and not node.keywords:
        # `adder(3)` on a declared local is its `__call__`, the instance term applied.
        applied = protocol_call(compiler, node.func, "__call__", *node.args, at=node)
        if applied is not None:
            return applied
    member = method_reference(compiler, node.func)
    if member is not None:
        method, home, receiver, after = member.method, member.home, member.receiver, member.after
        if call_syntax.expanded(node):
            return call_syntax.application(compiler, node)
        arguments = node.args
        qualified = receiver is None
        kind = method.kind if method is not None else "instance"
        class_symbol = Symbol(home.name) if kind == "class" and qualified else None
        if qualified and kind == "instance":
            if not arguments:
                return call_syntax.application(compiler, node)
            receiver, *arguments = arguments
        sources = [*([] if receiver is None else [receiver]), *arguments, *(keyword.value for keyword in node.keywords)]
        supplied = {id(source): Variable(compiler._temp("method-operand")) for source in sources}
        evaluated = [(compiler.expression(source), supplied[id(source)]) for source in sources]
        if kind == "class" and receiver is not None:
            # An instance reaches its class method through the class symbol of
            # its own type, so a subclass's override is the one selected.
            evaluated = [(_expr(S["get-type"], atom) if variable is supplied[id(receiver)] else atom, variable)
                         for atom, variable in evaluated]
        params = tuple(method.call_signature.parameters.values()) if method is not None else ()
        direct = method is not None and not node.keywords and len(arguments) == len(params) and all(
            parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
            for parameter in params
        )
        if kind == "static":
            head = Symbol(method.name if direct else method.unbound_apply_name)
        elif qualified and kind == "instance":
            head = Symbol(method.name if direct else method.apply_name)
        else:
            head = lazy('metta._declare.methods').selector(home, member.name, after=after, applied=not direct)
        operands: list[Atom] = [] if kind == "static" else [class_symbol if class_symbol is not None else supplied[id(receiver)]]
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
        routed = builtin(compiler, function, node)
        if routed is not None:
            return routed
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
    if method is after is None:
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


# ----------------------------------------------------------- special methods
# Python routes its own syntax to a special method of the operand's type: the
# operator inventory joins each binary, comparison, unary, subscript and
# containment form to its member, its reflected partner and its in-place
# partner, and the builtin calls below are the language reference's routing.
# When the operand's STATIC type is a declared class that defines the member,
# the syntax lowers to that method's own dispatch entry, the same entry an
# explicit call reaches; an operand of unknown type keeps the builtin.

#: Builtin calls the reference routes to a special method, written once.
# closed-set: decides; policy=which builtin call reaches which special method of a declared class; reads=https://docs.python.org/3.14/reference/datamodel.html#special-method-names, the Python Language Reference section 3.3
_BUILTIN_PROTOCOLS: dict[Any, str] = {
    builtins.len: "__len__",
    builtins.abs: "__abs__",
    builtins.str: "__str__",
    builtins.repr: "__repr__",
    builtins.int: "__int__",
    builtins.float: "__float__",
    builtins.round: "__round__",
    builtins.iter: "__iter__",
    builtins.next: "__next__",
    builtins.reversed: "__reversed__",
}

#: The reference's reflection for rich comparisons: `__lt__` and `__gt__` are
#: each other's reflection, `__le__` and `__ge__` likewise, `__eq__` and
#: `__ne__` their own [source: Python Language Reference section 3.3.1,
#: object.__lt__ and its siblings].
# closed-set: decides; policy=which comparison a reflected operand answers; reads=https://docs.python.org/3.14/reference/datamodel.html#object.__lt__
_REFLECTED_COMPARISONS: dict[str, str] = {
    "__eq__": "__eq__", "__ne__": "__ne__",
    "__lt__": "__gt__", "__gt__": "__lt__",
    "__le__": "__ge__", "__ge__": "__le__",
}


def protocol_member(compiler: CompilerContext, node: ast.expr, dunder: str) -> Any:
    """The declared class's method for a special name, when the operand's static type declares one."""
    owner = record_type(compiler, node)
    if owner is None:
        return None
    method = lazy('metta._declare.methods').selected(owner, dunder)
    return None if method is None or method.abstract else (owner, method)


def protocol_call(compiler: CompilerContext, receiver: ast.expr, dunder: str, *operands: ast.expr,
                  at: ast.AST) -> Atom | None:
    """Lower syntax to the receiver's special method, as the call Python itself makes."""
    if protocol_member(compiler, receiver, dunder) is None:
        return None
    synthesized = ast.Call(
        func=ast.Attribute(value=receiver, attr=dunder, ctx=ast.Load()), args=list(operands), keywords=[],
    )
    ast.copy_location(synthesized, at)
    ast.copy_location(synthesized.func, at)
    return call(compiler, synthesized)


def operator(compiler: CompilerContext, node: ast.BinOp) -> Atom | None:
    """`a + b` asks the left operand's `__add__`, then the right's `__radd__`."""
    entry = operators.BY_NODE.get(type(node.op).__name__)
    if entry is None:
        return None
    lowered = protocol_call(compiler, node.left, entry.dunder, node.right, at=node)
    if lowered is None and entry.reflected is not None:
        lowered = protocol_call(compiler, node.right, entry.reflected, node.left, at=node)
    return lowered


def augmented(compiler: CompilerContext, node: ast.AugAssign) -> Atom | None:
    """`a += b` asks `__iadd__`, then `__add__`, and rebinds the target to the answer."""
    if not isinstance(node.target, ast.Name):
        return None
    entry = operators.BY_NODE.get(type(node.op).__name__)
    if entry is None or not entry.augmented:
        return None
    read = ast.copy_location(ast.Name(id=node.target.id, ctx=ast.Load()), node.target)
    inplace = f"__i{entry.dunder[2:]}"
    for dunder in ((inplace, entry.dunder) if ("object", inplace) in BY_OPERATOR else (entry.dunder,)):
        lowered = protocol_call(compiler, read, dunder, node.value, at=node)
        if lowered is not None:
            return lowered
    return None


def comparison(compiler: CompilerContext, op: ast.cmpop, left: ast.expr, right: ast.expr, *, at: ast.AST) -> Atom | None:
    """One comparison link through the operand's own comparison method."""
    if isinstance(op, (ast.In, ast.NotIn)):
        lowered = protocol_call(compiler, right, "__contains__", left, at=at)
        if lowered is not None and isinstance(op, ast.NotIn):
            return _expr(S["not"], lowered)
        return lowered
    entry = operators.BY_NODE.get(type(op).__name__)
    if entry is None or entry.dunder not in _REFLECTED_COMPARISONS:
        return None
    forward = entry.dunder
    lowered = protocol_call(compiler, left, forward, right, at=at)
    if lowered is None:
        lowered = protocol_call(compiler, right, _REFLECTED_COMPARISONS[forward], left, at=at)
    if lowered is None and forward == "__ne__":
        # The reference derives != from == when no __ne__ is written.
        equal = comparison(compiler, ast.Eq(), left, right, at=at)
        if equal is not None:
            lowered = _expr(S["not"], equal)
    return lowered


def unary(compiler: CompilerContext, node: ast.UnaryOp) -> Atom | None:
    entry = operators.BY_NODE.get(type(node.op).__name__)
    if entry is None:
        return None
    return protocol_call(compiler, node.operand, entry.dunder, at=node)


def truth(compiler: CompilerContext, node: ast.expr) -> Atom | None:
    """The reference's truth test: `__bool__`, else `__len__` against zero."""
    lowered = protocol_call(compiler, node, "__bool__", at=node)
    if lowered is not None:
        return lowered
    length = protocol_call(compiler, node, "__len__", at=node)
    if length is not None:
        return _expr(S["not"], _expr(S["=="], length, Grounded(0)))
    return None


def subscript(compiler: CompilerContext, node: ast.Subscript) -> Atom | None:
    if isinstance(node.slice, ast.Slice):
        return None
    return protocol_call(compiler, node.value, "__getitem__", node.slice, at=node)


def subscript_write(compiler: CompilerContext, node: ast.Assign | ast.AnnAssign | ast.AugAssign) -> Atom | None:
    """`a[k] = v` is `__setitem__`; `a[k] += v` reads `__getitem__` first, as Python does."""
    target = node.targets[0] if isinstance(node, ast.Assign) else node.target
    if not isinstance(target, ast.Subscript) or isinstance(target.slice, ast.Slice) or node.value is None:
        return None
    if isinstance(node, ast.Assign) and len(node.targets) != 1:
        return None
    if protocol_member(compiler, target.value, "__setitem__") is None:
        return None
    value: ast.expr = node.value
    if isinstance(node, ast.AugAssign):
        read = ast.copy_location(ast.Subscript(value=target.value, slice=target.slice, ctx=ast.Load()), target)
        value = ast.copy_location(ast.BinOp(left=read, op=node.op, right=node.value), node)
    return protocol_call(compiler, target.value, "__setitem__", target.slice, value, at=node)


def subscript_delete(compiler: CompilerContext, target: ast.Subscript) -> Atom | None:
    if isinstance(target.slice, ast.Slice):
        return None
    return protocol_call(compiler, target.value, "__delitem__", target.slice, at=target)


def builtin(compiler: CompilerContext, function: Any, node: ast.Call) -> Atom | None:
    """A builtin call routed to the argument's special method: `len(a)` is `a.__len__()`."""
    if not node.args or node.keywords:
        return None
    subject, *rest = node.args
    if function is builtins.bool and not rest:
        return truth(compiler, subject)
    dunder = _BUILTIN_PROTOCOLS.get(function)
    if dunder is None:
        return None
    lowered = protocol_call(compiler, subject, dunder, *rest, at=node)
    if lowered is None and function is builtins.str:
        # str() falls back to __repr__, the reference's own rule.
        lowered = protocol_call(compiler, subject, "__repr__", *rest, at=node)
    return lowered


def iteration_source(compiler: CompilerContext, node: ast.expr) -> ast.expr:
    """`for x in a` reads a declared class through `__iter__`, written as a generator."""
    member = protocol_member(compiler, node, "__iter__")
    if member is None:
        return node
    owner, method = member
    if not method.generator:
        msg = (
            f"{owner.name}.__iter__ returns an iterator object; write it as a generator "
            f"(yield each element) so the loop reads its answers"
        )
        raise CompileError(msg, construct="for", line=getattr(node, "lineno", None))
    synthesized = ast.Call(func=ast.Attribute(value=node, attr="__iter__", ctx=ast.Load()), args=[], keywords=[])
    ast.copy_location(synthesized, node)
    ast.copy_location(synthesized.func, node)
    return synthesized


def context_manager(compiler: CompilerContext, node: ast.With) -> list[ast.stmt] | None:
    """`with a as v: body` is bind, enter, and try/finally with exit, the reference's expansion.

    `__exit__` receives three `None` arguments: no exception reaches it, so a
    manager that reads them keeps the host `with`.
    """
    if any(protocol_member(compiler, item.context_expr, "__enter__") is None for item in node.items):
        return None
    body: list[ast.stmt] = list(node.body)
    for item in reversed(node.items):
        manager = f"with-manager-{next_aux_serial()}"

        def name(ctx: ast.expr_context, manager: str = manager, at: ast.expr = item.context_expr) -> ast.Name:
            return ast.copy_location(ast.Name(id=manager, ctx=ctx), at)

        enter = ast.Call(func=ast.Attribute(value=name(ast.Load()), attr="__enter__", ctx=ast.Load()), args=[], keywords=[])
        exit_call = ast.Call(
            func=ast.Attribute(value=name(ast.Load()), attr="__exit__", ctx=ast.Load()),
            args=[ast.Constant(value=None) for _ in range(3)], keywords=[],
        )
        entered: ast.stmt = (
            ast.Assign(targets=[item.optional_vars], value=enter) if item.optional_vars is not None
            else ast.Expr(value=enter)
        )
        body = [
            ast.Assign(targets=[name(ast.Store())], value=item.context_expr),
            entered,
            ast.Try(body=body, handlers=[], orelse=[], finalbody=[ast.Expr(value=exit_call)]),
        ]
        for statement in body:
            ast.copy_location(statement, node)
            ast.fix_missing_locations(statement)
    return body


def keyword_pattern(compiler: CompilerContext, node: ast.MatchClass, pattern: Any) -> list[Atom]:
    """`case C(x=0, y=y)` places keyword patterns through `__match_args__` on a value class."""
    owner = declared(static_value(compiler, node.cls))
    positions = getattr(owner.cls, "__match_args__", None) if owner is not None and owner.grain == "value" else None
    if positions is None:
        msg = (
            "keyword class patterns need a declared value class, whose __match_args__ gives each "
            "field a position; match the constructor's positional fields, or read an entity's "
            "fields in a guard"
        )
        raise CompileError(msg, construct="class pattern", line=node.lineno)
    slots: list[Atom] = [Variable("_") for _ in positions]
    for index, sub in enumerate(node.patterns):
        slots[index] = pattern(sub)
    for name, sub in zip(node.kwd_attrs, node.kwd_patterns, strict=True):
        if name not in positions:
            msg = f"{owner.name} has no positional field {name!r}; its fields are {', '.join(positions)}"
            raise CompileError(msg, construct="class pattern", line=node.lineno)
        index = positions.index(name)
        if index < len(node.patterns):
            msg = f"{name!r} is matched both positionally and by keyword"
            raise CompileError(msg, construct="class pattern", line=node.lineno)
        slots[index] = pattern(sub)
    return slots
