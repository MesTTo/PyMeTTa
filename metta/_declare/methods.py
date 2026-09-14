"""Purpose: publish receiver methods as equations and owned C3 reference rows.

Owns resources:
  - class declarations own method equations, application helpers and imported
    entries; bound values retain the receiver and its lexical space [tested:
    test_class_bound_methods_keep_the_receiver_and_program_alive; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
Guarantees:
  - one canonical image owns the live parameter contract used by bound and
    unbound entries, whose shared binder captures no Python method [tested:
    test_method_defaults_are_read_from_one_native_signature;
    test_class_methods_keep_full_python_signatures_and_native_bodies;
    commit=WORKTREE]
  - method receivers and packed parameters retain Python underscore identity
    [tested: test_class_underscore_fields_receivers_and_packed_parameters; commit=69d1511c099eb6aa80c38d898da49487c42470f0]
  - Python invocation reads the live native equation and preserves the source
    function separately as py [tested:
    test_class_method_calls_observe_the_live_equation_graph; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
  - dispatch selects a completed Python MRO while every defining method keeps
    one equation body [tested:
    test_class_open_recursion_and_cooperative_super_follow_c3; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
  - an unbound method retains its declaring program through the same native
    class/member relation as its constructor [tested:
    test_kept_unbound_methods_retain_their_class_program; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
"""

from __future__ import annotations

import functools
import inspect
import itertools
import sys
import types
import typing
from collections.abc import Iterator
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._atoms.names import attribute_name, binding_name
from metta._catalog import call_signatures, call_values
from metta._catalog.annotations import resolved_annotations
from metta._catalog.build import build
from metta._catalog.documentation import documentation_atom
from metta._catalog.project import project
from metta._declare import call_syntax, classes, define, field_values, operations, projections
from metta._errors.errors import CompileError
from metta.vocabularies import EffectClass


def selected(plan: Any, name: str, *, after: type | None = None) -> Method | None:
    """Read the first descriptor in the completed MRO, including a shadow."""
    order = plan.cls.__mro__
    if after is not None:
        order = order[order.index(after) + 1:]
    for cls in order:
        owner = classes.declaration(cls)
        if owner is not None and name in owner.methods:
            return owner.methods[name]
        if name in vars(cls):
            return None
    return None


def selector(plan: Any, name: str, *, after: type | None = None, applied: bool = False, value: bool = False) -> Symbol:
    """Name an ordinary entry, its Python argument binding, or a bound value."""
    word = attribute_name(name)
    if after is not None:
        anchor = classes.declaration(after)
        if anchor is None:
            msg = "a native super entry requires a declared anchor class"
            raise TypeError(msg)
        word = f"{anchor.name}:super:{word}"
    elif not (applied or value):
        word = f"{plan.name}:dispatch:{word}"
    if applied or value:
        word = f"{plan.name}:{'apply' if applied else 'bind'}:{word}"
    return Symbol(word)


class Method:
    """A source method and its native declaration, with Python descriptor binding."""

    def __init__(self, owner: Any, name: str, fn: types.FunctionType):
        self.owner, self.python_name, self.py = owner, name, fn
        self.name = f"{owner.name}-{attribute_name(name)}"
        self.private = name.startswith("_")
        self.generator = inspect.isgeneratorfunction(fn)
        # A class-local annotation has its completed class in scope, just as
        # the method's lexical __class__ cell does. The source function and its
        # globals remain the author's objects.
        source_fn = classes.contextual_function(owner.cls, fn)
        self.source_fn = source_fn
        self.hints = resolved_annotations(source_fn)
        signature = inspect.signature(source_fn)
        self.signature = signature.replace(parameters=[
            parameter.replace(annotation=self.hints.get(name, parameter.annotation))
            for name, parameter in signature.parameters.items()
        ], return_annotation=self.hints.get("return", signature.return_annotation))
        parameters = tuple(self.signature.parameters.values())
        if not parameters or parameters[0].kind not in (
            inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD
        ):
            msg = f"{owner.name}.{name} needs an explicit receiver parameter; use staticmethod for a function without one"
            raise CompileError(msg, construct="method receiver", line=1)
        self.receiver_name = parameters[0].name
        self.call_signature = self.signature.replace(parameters=parameters[1:])
        self.defaults = {
            name: call_values.argument(parameter.default)
            for name, parameter in self.call_signature.parameters.items()
            if parameter.default is not inspect.Parameter.empty
        }
        self.result_type = self.hints.get("return", Any)
        if self.generator:
            args = typing.get_args(self.result_type)
            self.result_type = args[0] if args else Any
        self.compiled: define.Compiled | None = None
        self.equations: tuple[Expression, ...] = ()
        self.projected: tuple[Expression, ...] = ()
        self.rows: list[tuple[str, int]] = []
        self.apply_name = f"{self.name}:apply"
        self.unbound_apply_name = f"{self.name}:apply-unbound"
        self.bind_name = f"{self.name}:bound"
        functools.update_wrapper(self, source_fn, updated=())
        self.__wrapped__ = fn

    def __get__(self, instance: Any, _cls: type | None = None) -> Method | BoundMethod:
        return self if instance is None else BoundMethod(self, instance)

    def __call__(self, /, *args: Any, **kwargs: Any) -> Any:
        return call_values.NativeCallable(self.bound_atom(), self.owner.space, Any)(*args, **kwargs)

    def __metta__(self) -> Atom:
        return self.bound_atom()

    @property
    def __signature__(self) -> inspect.Signature:
        return call_values.NativeCallable(self.__metta__(), self.owner.space, Any).__signature__

    @property
    def body(self) -> Atom:
        bodies = [row.args[1] for row in self.live_equations()]
        return bodies[0] if len(bodies) == 1 else _expr(S.superpose, Expression(bodies))

    def live_equations(self) -> tuple[Expression, ...]:
        head = _expr(Symbol(self.name), *(Variable(binding_name(name)) for name in self.signature.parameters))
        body = Variable("method-source-body")
        equation = _expr(S["="], head, body)
        return tuple(self.owner.space.eval(_expr(S.match, Symbol(self.owner.space.name), equation, _expr(S.noeval, equation))))

    def source(self) -> str:
        return "\n".join(map(str, self.live_equations()))

    def receiver(self, instance: Any) -> Atom:
        actual = classes.declaration(type(instance))
        if actual is None or self.owner.space.dropped:
            msg = f"{self.owner.name}.{self.python_name} has retired; declare the class before calling its methods"
            raise ReferenceError(msg)
        return project(instance).atom if actual.grain == "value" else actual.receiver(instance)

    def invoke(self, instance: Any, args: Any, kwargs: Any) -> Any:
        receiver = self.receiver(instance)
        return call_values.NativeCallable(self.bound_atom(receiver), self.owner.space, Any)(*args, **kwargs)

    def bound_atom(self, receiver: Atom | None = None) -> Atom:
        arguments = Variable("method-arguments")
        parameters = [] if receiver is not None else [Variable(binding_name(self.receiver_name))]
        receiver = receiver if receiver is not None else parameters[0]
        positional = _expr(S["cons-atom"], _expr(S.noeval, receiver), arguments)
        call = call_syntax.member_application(self.owner, Symbol(attribute_name(self.python_name)),
                                               positional, _expr(S.noeval, Expression([])))
        return _expr(S["|->"], Expression([*parameters, _expr(S[":seg"], arguments)]),
                     _expr(S.evalc, call, Symbol(self.owner.space.name)))

    def compile(self) -> None:
        owner = self.owner
        auxiliary: tuple[Expression, ...]
        try:
            compiled = define.compile_function(
                self.source_fn, known=owner.space.is_function,
                nondet=lambda name: any(method.generator and name in (
                    method.name, attribute_name(method.python_name)
                ) for plan in (owner, *owner.bases) for method in plan.methods.values()),
                metta_name=self.name, signature=self.signature,
                class_context=owner.cls, method_receiver=self.receiver_name,
            )
        except CompileError as error:
            print(f"{owner.name}.{self.python_name}: {error}\nkept as a host equation with effect oracleIO", file=sys.stderr)
            body = self.host_body()
            auxiliary = ()
        else:
            self.compiled = compiled
            owner.dependencies.update(compiled.class_dependencies)
            arguments = (*self.defaults.values(), *(
                (owner.keyword_arguments({}),) if any(
                    parameter.kind is inspect.Parameter.VAR_KEYWORD
                    for parameter in self.call_signature.parameters.values()
                ) else ()
            ))
            owner.import_dependencies(compiled.libraries, (compiled.body, *compiled.aux, *arguments))
            call_syntax.link(owner.space, compiled.runtime_ops)
            body, auxiliary = compiled.body, tuple(compiled.aux)
        head = _expr(Symbol(self.name), *(Variable(binding_name(name)) for name in self.signature.parameters))
        self.equations = (*auxiliary, _expr(S["="], head, body))
        self.projected = self.equations
        for equation in self.equations:
            self.rows.extend(classes._owned_add(owner.space, equation))
        inputs = [[Symbol(owner.name)], *(
            [S.Expression] if parameter.kind is inspect.Parameter.VAR_POSITIONAL else
            [S.SpaceType] if parameter.kind is inspect.Parameter.VAR_KEYWORD else
            field_values.type_atoms(parameter.annotation if parameter.annotation is not inspect.Parameter.empty else Any, retained=True)
            for parameter in self.call_signature.parameters.values()
        ), field_values.type_atoms(self.result_type, retained=True)]
        for chain in itertools.product(*inputs):
            owner.space.add(_expr(S[":"], Symbol(self.name), _expr(S["->"], *chain)))
        if self.private:
            owner.space.add(_expr(S.internal, Symbol(self.name)))
        documentation = documentation_atom(self.name, self.py, kind="function", parameters=tuple(self.signature.parameters), annotations=self.hints)
        if documentation is not None:
            owner.space.add(documentation)
        self.install_binding()

    def host_body(self) -> Atom:
        """A refused source uses the same equation and its owned host operation."""
        head = f"_host-{self.name}"

        def invoke(receiver: Atom, *arguments: Atom) -> Any:
            values = {self.receiver_name: build(receiver)}
            for (name, parameter), argument in zip(self.call_signature.parameters.items(), arguments, strict=True):
                annotation = (
                    tuple[Any, ...] if parameter.kind is inspect.Parameter.VAR_POSITIONAL else
                    dict[str, Any] if parameter.kind is inspect.Parameter.VAR_KEYWORD else
                    parameter.annotation if parameter.annotation is not inspect.Parameter.empty else Any
                )
                values[name] = build(argument, annotation)
            supplied = inspect.BoundArguments(self.signature, values)
            return self.py(*supplied.args, **supplied.kwargs)

        def scalar(*arguments: Atom) -> Atom:
            return self.owner.encode(invoke(*arguments))

        def stream(*arguments: Atom) -> Iterator[Atom]:
            for value in invoke(*arguments):
                yield self.owner.encode(value)

        self.owner.operation(stream if self.generator else scalar, name=head,
                             arities=[len(self.signature.parameters)], effect=EffectClass.oracleIO,
                             declarations=[_expr(S.arguments, Symbol(head), S.atoms)])
        self.owner.space.add(_expr(S.internal, Symbol(head)))
        return _expr(Symbol(head), *(Variable(binding_name(name)) for name in self.signature.parameters))

    def install_binding(self) -> None:
        """Bind Python call syntax, then evaluate its ordinary native application."""
        home = Symbol(self.owner.space.name)
        parameters = Expression([Variable(f"call-parameter-{index}") for index, _ in enumerate(self.signature.parameters)])
        canonical = _expr(S["|->"], parameters, _expr(S.evalc, _expr(Symbol(self.name), *parameters.children), home))
        binder = S["_python-bind-parameters"]
        call_syntax.link(self.owner.space, (binder.name,))
        member = Symbol(attribute_name(self.python_name))
        call_syntax.publish_member(self.owner, member, Symbol(self.unbound_apply_name))
        receiver = Variable("method-self")
        positional, keywords, complete = Variable("method-positionals"), Variable("method-keywords"), Variable("method-complete")
        apply = Symbol(self.apply_name)
        unbound = Symbol(self.unbound_apply_name)
        binding = call_values.apply_sources(binder, tuple(
            _expr(S.noeval, value) for value in (home, canonical, positional, keywords)
        ))
        call = Variable("method-bound-call")
        self.owner.space.add(_expr(S["="], _expr(unbound, positional, keywords),
                                   _expr(S.chain, binding, call, _expr(S.evalc, call, home))))
        self.owner.space.add(_expr(S[":"], unbound, _expr(S["->"], S.Expression, S.Expression, S["%Undefined%"])))
        self.owner.space.add(_expr(S["="], _expr(apply, receiver, positional, keywords),
                                   _expr(S.let, complete, _expr(S["cons-atom"], _expr(S.noeval, receiver), positional),
                                         _expr(unbound, complete, keywords))))
        self.owner.space.add(_expr(S[":"], apply, _expr(S["->"], Symbol(self.owner.name), S.Expression, S.Expression, S["%Undefined%"])))
        self.owner.space.add(_expr(S.internal, unbound))
        self.owner.space.add(_expr(S["="], _expr(Symbol(self.bind_name), receiver),
                                   _expr(S.noeval, self.bound_atom(receiver))))
        self.owner.space.add(_expr(S[":"], Symbol(self.bind_name), _expr(S["->"], Symbol(self.owner.name), S.Atom)))
        self.owner.space.add(_expr(S["@python-binding"], self.bound_atom(receiver), canonical, Grounded(1)))
        self.owner.space.add(_expr(S["@python-binding"], self.bound_atom(), canonical, Grounded(0)))
        self.owner.space.add(_expr(S["@python-callable"], canonical, call_signatures.project(self.signature, call_values.argument), S.stream if self.generator else S.one))
        for image, arguments in (
            (self.bound_atom(receiver), _expr(S["cons-atom"], _expr(S.noeval, receiver), positional)),
            (self.bound_atom(), _expr(S.noeval, positional)),
            (canonical, _expr(S.noeval, positional)),
        ):
            application = call_syntax.member_application(self.owner, member, arguments, _expr(S.noeval, keywords))
            applicator = _expr(S["|->"], Expression([positional, keywords]), _expr(S.evalc, application, Symbol(self.owner.space.name)))
            self.owner.space.add(_expr(S["@python-application"], image, applicator))
        if self.private:
            self.owner.space.add(_expr(S.internal, Symbol(self.apply_name), Symbol(self.bind_name)))


class BoundMethod:
    """A Python bound method whose image retains the native receiver and home."""

    def __init__(self, method: Method, instance: Any):
        self.method, self.instance = method, instance
        functools.update_wrapper(self, method.py, updated=())

    @property
    def __signature__(self) -> inspect.Signature:
        return call_values.NativeCallable(self.__metta__(), self.method.owner.space, Any).__signature__

    def __call__(self, /, *args: Any, **kwargs: Any) -> Any:
        return self.method.invoke(self.instance, args, kwargs)

    def __metta__(self) -> Atom:
        return self.method.bound_atom(self.method.receiver(self.instance))

    @property
    def py(self) -> Any:
        return types.MethodType(self.method.py, self.instance)

    @property
    def body(self) -> Atom:
        return self.method.body

    def source(self) -> str:
        return self.method.source()


def prepare(plan: Any) -> None:
    """Inspect every own ordinary method before any class body is compiled."""
    for name, fn in vars(plan.cls).items():
        if inspect.isfunction(fn) and not (name.startswith("__") and name.endswith("__")):
            plan.methods[name] = Method(plan, name, fn)


def compile_methods(plan: Any) -> None:
    for method in plan.methods.values():
        method.compile()


def _entry_pattern(concrete: Any, target: Symbol, arity: int) -> Expression:
    fields = tuple(Variable(f"method-field-{index}") for index in range(
        len(concrete.stored_fields) if concrete.grain == "value" else 1
    ))
    receiver = concrete.term(*fields)
    arguments = tuple(Variable(f"method-argument-{index}") for index in range(arity - 1))
    return _expr(target, receiver, *arguments)


def synchronize(plans: tuple[Any, ...]) -> None:
    """Materialize MRO-selected edges; each concrete declaration owns its rows."""
    for plan in plans:
        for method in plan.methods.values():
            projections.refresh(method, plans)
    for concrete in plans:
        rows: dict[tuple[str, Atom], Any] = {}
        providers: dict[tuple[Any, Any], dict[str, list[Atom]]] = {}
        names = dict.fromkeys(name for owner in (concrete, *concrete.bases) for name in owner.methods)
        # Every lookup has a class-qualified entry. A short alias may extend
        # the public face only when it does not replace an engine operation.
        public = {
            name for name in names if not name.startswith("_") and not concrete.space._rt.once(
                "(seam:builtin_type_declaration(Name,_) ; "
                "current_predicate(system:Name/_Arity),functor(_Head,Name,_Arity),"
                "predicate_property(system:_Head,built_in))",
                Name=attribute_name(name),
            )
        }
        for home in (concrete, *concrete.bases):
            if home is not concrete:
                providers.setdefault((home, concrete), {}).setdefault(concrete.name, []).append(Symbol(concrete.name))
            for name in names:
                for after in (None, home.cls):
                    method = selected(concrete, name, after=after)
                    if method is None:
                        continue
                    source, arity = method.name, len(method.signature.parameters)
                    expected = selected(home, name, after=after)
                    if expected is not None:
                        expected_parameters = tuple(expected.call_signature.parameters.values())
                        actual_parameters = tuple(method.call_signature.parameters.values())
                        positional = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
                        if all(parameter.kind in positional for parameter in expected_parameters) and (
                            len(actual_parameters) != len(expected_parameters)
                            or any(parameter.kind not in positional for parameter in actual_parameters)
                        ):
                            source = f"{home.name}-adapt-{concrete.name}-{attribute_name(name)}"
                            if after is not None:
                                source += "-super"
                            arity = len(expected.signature.parameters)
                            arguments = tuple(Variable(f"adapt-argument-{index}") for index in range(arity))
                            application = _expr(Symbol(method.apply_name), arguments[0], Expression(arguments[1:]), Expression([]))
                            rows[method.owner.space.name, _expr(S["="], _expr(Symbol(source), *arguments), application)] = method.owner.space
                            rows[method.owner.space.name, _expr(S[":"], Symbol(source), _expr(
                                S["->"], Symbol(concrete.name), *(S["%Undefined%"] for _ in arguments[1:]), S["%Undefined%"],
                            ))] = method.owner.space
                    entries = [
                        (selector(home, name, after=after), source, arity),
                        (selector(home, name, after=after, applied=True), method.apply_name, 3),
                        (selector(home, name, after=after, value=True), method.bind_name, 1),
                    ]
                    if after is None and name in public:
                        entries.append((Symbol(attribute_name(name)), method.name, len(method.signature.parameters)))
                    for target, source, arity in entries:
                        pattern = _entry_pattern(concrete, target, arity)
                        if method.private:
                            body = _expr(Symbol(source), *pattern.args)
                            if home is not method.owner:
                                body = _expr(S.evalc, body, Symbol(method.owner.space.name))
                            rows[home.space.name, _expr(S["="], pattern, body)] = home.space
                            rows[home.space.name, _expr(S.internal, target)] = home.space
                        else:
                            providers.setdefault((home, method.owner), {}).setdefault(source, []).append(pattern)
        # rename keeps unlisted heads. A finite case map selects only the
        # canonical providers and emits their complete target set in one row.
        # Parallel alias edges would make the reference reader traverse the
        # same provider graph once per method on every path through a diamond.
        for (home, provider), targets in providers.items():
            head = Variable("method-source-head")
            cases = [Expression([
                Symbol(source),
                _expr(S.superpose, Expression([_expr(S.noeval, pattern) for pattern in patterns])),
            ]) for source, patterns in targets.items()]
            cases.append(Expression([Variable("other-method-head"), _expr(S.empty)]))
            mapping = _expr(S["|->"], Expression([head]), _expr(S.case, head, Expression(cases)))
            row = _expr(S["from"], Symbol(provider.space.name), mapping)
            rows[home.space.name, row] = home.space
        previous = concrete.method_rows
        current = previous.copy()
        if previous.keys() != rows.keys():
            operations._record_registry_undo(
                functools.partial(setattr, concrete, "method_rows", previous),
                description=f"method entries {concrete.name}",
            )
            for key in previous:
                if key not in rows:
                    classes._withdraw_rows(concrete.space._rt, current.pop(key))
            for key, home in rows.items():
                if key not in previous:
                    current[key] = classes._owned_add(home, key[1])
            concrete.method_rows = current
    # Materialize the canonical bodies before a later descendant references
    # them. Planning reads source and never executes a method to initialize it.
    for plan in plans:
        for method in plan.methods.values():
            plan.space.effect_plan(_expr(Symbol(method.name), *(Variable(binding_name(name)) for name in method.signature.parameters)))


def instrument(plan: Any) -> None:
    for name, method in plan.methods.items():
        plan.replace_attribute(name, method)
