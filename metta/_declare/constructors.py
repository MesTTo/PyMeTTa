"""Purpose: compile class initialization with the ordinary statement compiler.

Guarantees:
  - constructor parameters retain Python underscore identity [tested:
    test_class_underscore_fields_receivers_and_packed_parameters; commit=WORKTREE]
  - default computations finish before field input contracts inspect their
    resulting values [tested:
    test_constructor_arguments_preserve_values_and_run_factories; commit=310a9d8b547a77412a518a37ab79fba073eb22ac]
  - defaults and factories run per construction and post-init reads the same
    field bindings as initialization [tested:
    test_class_value_post_init_and_write_refusal; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - mutable factories allocate once and publish their result inside the engine
    transaction [tested: test_class_constructor_rollback; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - Python initialization checks the same parameter contract as make-Class
    [tested: test_container_refinements_guard_native_and_host_field_writes;
    commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - a constructor image carries the class identity used by its native dispatch
    and deferred cleanup [tested: test_kept_class_values_own_their_constructor_program;
    commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
  - initialization retains its lexical class when deferred annotations are
    resolved [tested: test_class_declaration_resolves_its_deferred_annotation_namespace;
    commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import itertools
import textwrap
import types
from typing import Any

from metta._atoms.factories import Atom, Expression, S, Symbol, Variable, _expr
from metta._atoms.names import binding_name
from metta._catalog import call_signatures, call_values
from metta._compile.records import declared, field_key, value_receiver
from metta._declare import call_syntax, field_values
from metta._declare.classes import _ABSENT, contextual_function
from metta._errors.errors import CompileError, with_coordinates
from metta.vocabularies import EffectClass


def _factory(plan: Any, name: str, factory: Any) -> Atom:
    if plan.grain == "value" and factory in (list, tuple, dict, set):
        # All four empty containers use the catalog's immutable empty image.
        # Their annotations choose the Python species on reconstruction.
        return Expression([])
    owner = declared(factory)
    if owner is not None:
        plan.dependencies.add(owner.cls)
        return _expr(Symbol(f"make-{owner.name}"))
    head = f"_{plan.name}-default-{name}"

    def create() -> Any:
        return call_values.argument(factory())

    plan.operation(create, name=head, effect=EffectClass.oracleIO, arities=[0])
    plan.space.add(_expr(S.internal, Symbol(head)))
    return _expr(Symbol(head))


def _prepare_defaults(plan: Any) -> None:
    for name, parameter in plan.signature.parameters.items():
        field = next((field for field in plan.fields if field.name == name), None)
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            plan.defaults[name] = _expr(S.noeval, Expression([]))
        elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
            plan.defaults[name] = plan.keyword_arguments({})
        elif plan.generated_init and field is not None and field.factory is not None:
            plan.defaults[name] = _factory(plan, name, field.factory)
        elif parameter.default is not inspect.Parameter.empty:
            plan.defaults[name] = _expr(S.noeval, call_values.argument(parameter.default))


def _compiler(plan: Any, fn: types.FunctionType | None, params: dict[str, str], closer: Any, shared: Any = None, *, receiver: str = "class-receiver", member: str = "__init__") -> Any:
    from metta._declare.define import (  # noqa: PLC0415 -- class and function installers share the compiler
        _annotation_resolver,
        _Compiler,
        _function_namespace,
    )

    lexical_class = plan.cls if fn is None else plan.defining_class(member, fn)
    if fn is not None:
        fn = contextual_function(lexical_class, fn)
    namespace = _function_namespace(fn) if fn is not None else vars(__builtins__) if isinstance(__builtins__, types.ModuleType) else dict(__builtins__)
    namespace = namespace | {plan.cls.__name__: plan.cls}
    if fn is None:
        source, first, path = "", 1, f"<generated {plan.name}.__init__>"
        resolver = alternatives = annotation_value = None
    else:
        lines, first = inspect.getsourcelines(fn)
        source, path = textwrap.dedent("".join(lines)), inspect.getfile(fn)
        resolver, alternatives, annotation_value = _annotation_resolver(fn)
    compiler = _Compiler(
        f"_initialize-{plan.name}", params, plan.space.is_function,
        closer=closer, host=lambda name: name in namespace,
        host_value=namespace.get,
        function=fn, source=source, source_path=path, first_line=first,
        annotation_resolver=resolver, annotation_alternatives=alternatives,
        annotation_value=annotation_value,
        aux=None if shared is None else shared.aux,
        runtime_ops=None if shared is None else shared.runtime_ops,
        libraries=None if shared is None else shared.libraries,
        used=None if shared is None else shared.used,
        record_locals=({} if shared is None else shared.record_locals.copy()) | {receiver: plan.cls},
        number_locals=None if shared is None else shared.number_locals.copy(),
        container_locals=None if shared is None else shared.container_locals.copy(),
        dict_locals=None if shared is None else shared.dict_locals.copy(),
        class_context=lexical_class,
        class_dependencies=plan.dependencies, construction=(plan, receiver),
    )
    compiler.constructor_return = closer
    for name, parameter in plan.signature.parameters.items():
        if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            compiler.container_locals[name] = "tuple"
            continue
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            compiler.container_locals[name] = "dict"
            compiler.dict_locals.add(name)
            compiler.libraries.add("dict")
            continue
        if parameter.annotation in (int, float):
            compiler.number_locals.add(name)
        if declared(parameter.annotation) is not None:
            compiler.record_locals[name] = parameter.annotation
    return compiler


def _finish(compiler: Any) -> Atom:
    plan, receiver = compiler.construction
    return value_receiver(compiler) if plan.grain == "value" else Variable(compiler.scope[receiver])


def _post_init(plan: Any, previous: Any) -> Atom:
    fn = plan.post_init
    if fn is None or not plan.generated_init:
        return _finish(previous)
    parameters = list(inspect.signature(contextual_function(plan.cls, fn)).parameters)
    scope = previous.scope.copy()
    scope[parameters[0]] = scope[previous.construction[1]]
    initvars = [field for field in plan.fields if field.initvar]
    for name, field in zip(parameters[1:], initvars, strict=True):
        scope[name] = scope[field.name]
    compiler = _compiler(plan, fn, scope, _finish, previous, receiver=parameters[0], member="__post_init__")
    for name, field in zip(parameters[1:], initvars, strict=True):
        if field.annotation in (int, float):
            compiler.number_locals.add(name)
        if declared(field.annotation) is not None:
            compiler.record_locals[name] = field.annotation
    return _source_body(compiler)


def _source_body(compiler: Any) -> Atom:
    try:
        tree = ast.parse(compiler.source).body[0]
        return compiler.block(tree.body)
    except CompileError as error:
        raise with_coordinates(error, source=compiler.source,
                               first_line=compiler.first_line,
                               path=compiler.source_path,
                               function=compiler.function.__qualname__) from error


def _generated_body(plan: Any, compiler: Any) -> Atom:
    steps = []
    value: Atom
    for field in plan.stored_fields:
        if field.name in plan.signature.parameters:
            value = Variable(compiler.scope[field.name])
        elif field.factory is not None and not (
            dataclasses.is_dataclass(plan.cls) and plan.initializer is object.__init__
        ):
            value = _factory(plan, field.name, field.factory)
        elif field.default is not _ABSENT:
            value = _expr(S.noeval, plan.encode(field.default))
        else:
            continue
        if not isinstance(value, Variable):
            held = Variable(compiler._temp("field-value"))
            steps.append((held, value))
            value = held
        if plan.grain == "value":
            value = field_values.adopted(plan, field, value)
            target = Variable(compiler._bind(field_key(field.name)))
            if field.annotation in (int, float):
                compiler.number_locals.add(field_key(field.name))
        else:
            value = _expr(plan.accessor(field.name, write=True), Variable(compiler.scope[compiler.construction[1]]), value)
            target = Variable(compiler._temp("field-init"))
        steps.append((target, value))
    body = _post_init(plan, compiler)
    for target, value in reversed(steps):
        body = _expr(S.chain, value, target, body)
    return body


def image(plan: Any) -> Atom:
    """A constructor value calls the same native factory as written syntax."""
    arguments = Variable("constructor-arguments")
    application = call_syntax.member_application(plan, Expression([]),
                                                 _expr(S.noeval, arguments), _expr(S.noeval, Expression([])))
    return _expr(S["|->"], Expression([_expr(S[":seg"], arguments)]),
                 _expr(S.evalc, application, Symbol(plan.space.name)))


def _callable(plan: Any) -> None:
    signature = plan.signature.replace(parameters=[
        parameter.replace(default=plan.defaults[name])
        if parameter.default is not inspect.Parameter.empty else parameter
        for name, parameter in plan.signature.parameters.items()
    ], return_annotation=plan.cls)
    plan.space.add(_expr(S["@python-callable"], image(plan), call_signatures.project(signature, call_values.argument), S.one))

    def bind(positional: Atom, keywords: Atom) -> Atom:
        signature = call_values.NativeCallable(image(plan), plan.space, Any).__signature__
        supplied = call_syntax.bind_arguments(signature, positional, keywords)
        sources = plan.argument_sources(supplied.arguments, call_values.argument, signature=signature)
        return _expr(S.transaction, call_values.apply_sources(Symbol(f"make-{plan.name}"), sources))

    name = f"make-{plan.name}:apply"
    call_syntax.publish_binding(plan, name, bind, (S.Expression, S.Expression))
    call_syntax.publish_member(plan, Expression([]), Symbol(name))
    positional, keywords = Variable("constructor-positionals"), Variable("constructor-keywords")
    application = call_syntax.member_application(plan, Expression([]), _expr(S.noeval, positional), _expr(S.noeval, keywords))
    applicator = _expr(S["|->"], Expression([positional, keywords]),
                       _expr(S.evalc, application, Symbol(plan.space.name)))
    plan.space.add(_expr(S["@python-application"], image(plan), applicator))
    plan.space.add(_expr(S.internal, Symbol(name)))


def install(plan: Any) -> None:
    if plan.enum:
        member = Variable("member")
        plan.space.add(_expr(S["="], _expr(Symbol(f"make-{plan.name}"), member), plan.term(member)))
        _callable(plan)
        return
    _prepare_defaults(plan)
    names = tuple(plan.signature.parameters)
    fn = None if plan.generated_init else plan.initializer
    if fn is not None and not isinstance(fn, types.FunctionType):
        msg = f"{plan.name}.__init__ has no Python source; declare an explicit factory operation"
        raise CompileError(msg, construct="constructor source", line=1)
    receiver = next(iter(inspect.signature(contextual_function(plan.cls, fn)).parameters)) if fn is not None else "class-receiver"
    scope = {name: binding_name(name) for name in names} | {receiver: "class-receiver"}
    compiler = _compiler(plan, fn, scope, lambda current: _post_init(plan, current), receiver=receiver)
    body = _generated_body(plan, compiler) if plan.generated_init else _source_body(compiler)
    plan.import_dependencies(compiler.libraries, (body, *compiler.aux, *plan.defaults.values()))
    call_syntax.link(plan.space, compiler.runtime_ops)
    for equation in compiler.aux:
        plan.space.add(equation)
    initialized = Symbol(f"_initialize-{plan.name}")
    plan.space.add(_expr(S.internal, initialized))
    arguments = tuple(Variable(binding_name(name)) for name in names)
    receiver_atom = Variable("class-receiver")
    params = (receiver_atom, *arguments) if plan.grain != "value" else arguments
    plan.space.add(_expr(S["="], _expr(initialized, *params), body))
    factory = Symbol(f"make-{plan.name}")
    made = _expr(initialized, *arguments) if plan.grain == "value" else _expr(S.chain, _expr(Symbol(f"_mint-{plan.name}")), receiver_atom, _expr(initialized, receiver_atom, *arguments))
    plan.space.add(_expr(S["="], _expr(factory, *arguments), _expr(S.transaction, made)))
    for count in range(len(names)):
        if not all(name in plan.defaults for name in names[count:]):
            continue
        application = call_values.apply_sources(Symbol(f"make-{plan.name}:apply"), (
            _expr(S.noeval, Expression(arguments[:count])), _expr(S.noeval, Expression([])),
        ))
        plan.space.add(_expr(S["="], _expr(factory, *arguments[:count]), application))
    alternatives = [
        [S.Expression] if parameter.kind is inspect.Parameter.VAR_POSITIONAL else
        [S.SpaceType] if parameter.kind is inspect.Parameter.VAR_KEYWORD else
        field_values.type_atoms(parameter.annotation if parameter.annotation is not inspect.Parameter.empty else Any, retained=True)
        for parameter in plan.signature.parameters.values()
    ]
    for types_ in itertools.product(*alternatives):
        plan.space.add(_expr(S[":"], factory, _expr(S["->"], *types_, Symbol(plan.name))))
        initializer_types = (Symbol(plan.name), *types_) if plan.grain != "value" else types_
        plan.space.add(_expr(S[":"], initialized, _expr(S["->"], *initializer_types, Symbol(plan.name))))
    _callable(plan)
