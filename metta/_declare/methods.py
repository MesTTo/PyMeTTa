"""Purpose: publish receiver methods as equations and owned C3 reference rows.

Owns resources:
  - class declarations own method equations, application helpers and imported
    entries; bound values retain the receiver and its lexical space [tested:
    test_class_bound_methods_keep_the_receiver_and_program_alive; commit=ba819bfa2aa69d231d8ebae7d74b085f838840de]
Guarantees:
  - compiled and refused bodies receive one dictionary after the canonical
    head has matched ordered keyword terms [tested:
    test_compiled_collectors_match_native_equation_heads;
    test_refused_method_collectors_enter_the_host_body; commit=1796cf0f581aa767db9289b807f66238cb747065]
  - one canonical image owns the live parameter contract used by bound and
    unbound entries, whose shared binder captures no Python method [tested:
    test_method_defaults_are_read_from_one_native_signature;
    test_class_methods_keep_full_python_signatures_and_native_bodies;
    commit=71a6b9f41b19452d50934448a6d77432887f5193]
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
  - a special method compiles under its word and Python's own operator on the
    instance reaches that equation; a property, cached property, static,
    class, cache-wrapped, single-dispatch and partial member publishes the
    functions it holds under the descriptor's own role; `@dataclass(order=True)`
    and `functools.total_ordering` derive the comparisons they wrote from the
    class's accessors; an abstract member publishes its arrow and a concrete
    subclass that leaves it unwritten refuses, as does a redefinition of a
    final member and a `__del__` [tested:
    test_operators_on_a_declared_value_lower_to_its_special_methods,
    test_comparisons_derive_from_dataclass_order_and_total_ordering,
    test_properties_static_and_class_methods_and_memoised_members,
    test_abstract_final_override_dispatch_and_partial_members; commit=WORKTREE]
Decides:
  - which special methods compile (_COMPILED_DUNDERS) and the formulas
    total_ordering's partners derive from (_TOTAL_ORDERING), both read from
    the pinned CPython sources named beside them
"""

from __future__ import annotations

import dataclasses
import functools
import inspect
import itertools
import sys
import types
import typing
from collections.abc import Callable, Iterator
from typing import Any

from metta._atoms._python_protocols import BY_OPERATOR
from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._atoms.names import attribute_name, binding_name
from metta._catalog import call_signatures, call_values
from metta._catalog.annotations import resolved_annotations
from metta._catalog.build import build
from metta._catalog.documentation import documentation_atom
from metta._catalog.project import project
from metta._compile.records import _BUILTIN_PROTOCOLS, field_call
from metta._declare import call_syntax, classes, define, field_values, operations, projections
from metta._errors.errors import CompileError
from metta.vocabularies import EffectClass

#: The special methods Python routes syntax or a builtin call to, which a
#: declaration compiles like any method under the dunder's word: the operator
#: inventory's members with their reflected and in-place partners, the
#: builtin-routed members the compiler consults, and the four the reference
#: reaches through `with`, `divmod` and a mapping's missing key
#: [source: https://docs.python.org/3.14/reference/datamodel.html#special-method-names].
# closed-set: decides; policy=which special methods compile to equations rather than run at declaration; reads=extensions/python/metta/_atoms/_python_protocols.py:BY_OPERATOR, extensions/python/metta/_compile/records.py:_BUILTIN_PROTOCOLS
_COMPILED_DUNDERS: frozenset[str] = frozenset(
    {member for _owner, member in BY_OPERATOR}
    | {row.reflected[1] for row in BY_OPERATOR.values() if row.reflected is not None}
    | {f"__i{member[2:]}" for _owner, member in BY_OPERATOR if ("object", f"__i{member[2:]}") in BY_OPERATOR}
    | set(_BUILTIN_PROTOCOLS.values())
    | {"__bool__", "__enter__", "__exit__", "__divmod__", "__rdivmod__", "__missing__"}
)

#: functools.total_ordering's derivations, one per root comparison, as CPython
#: writes them: (derived name, formula over the root and equality)
#: [source: https://github.com/python/cpython/blob/23116f998f6789d8c2fbe5ed5b8146854c8c2a4f/Lib/functools.py#L89-L170].
# closed-set: decides; policy=the comparison each total_ordering root derives and its formula; reads=the pinned CPython functools source above
_TOTAL_ORDERING: dict[str, tuple[tuple[str, str], ...]] = {
    "__lt__": (("__gt__", "not root and not eq"), ("__le__", "root or eq"), ("__ge__", "not root")),
    "__le__": (("__ge__", "not root or eq"), ("__lt__", "root and not eq"), ("__gt__", "not root")),
    "__gt__": (("__lt__", "not root and not eq"), ("__ge__", "root or eq"), ("__le__", "not root")),
    "__ge__": (("__le__", "not root or eq"), ("__gt__", "root and not eq"), ("__lt__", "not root")),
}

#: The strict comparison each dataclass(order=True) method is lexicographic on,
#: and whether equality of the whole tuple also satisfies it.
# closed-set: decides; policy=the strict comparison and the equal-tuple verdict behind each ordering method; reads=https://docs.python.org/3.14/library/dataclasses.html, order=True compares the fields as tuples
_ORDERINGS: dict[str, tuple[str, bool]] = {
    "__lt__": ("<", False), "__le__": ("<", True), "__gt__": (">", False), "__ge__": (">", True),
}


def _dunder(name: str) -> bool:
    return len(name) > 4 and name.startswith("__") and name.endswith("__")


def _word(name: str) -> str:
    """A special method's head word is the dunder's word; every other name maps mechanically."""
    return name[2:-2] if _dunder(name) else attribute_name(name)


def _generated(fn: Any) -> bool:
    """A method dataclasses wrote from the field list rather than the author.

    `__repr__` arrives inside reprlib's recursion guard, so the wrapper is
    unwrapped before its code is read.
    """
    return inspect.isfunction(fn) and inspect.unwrap(fn).__code__.co_filename == "<string>"


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
    word = _word(name)
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
    """A source method and its native declaration, with Python descriptor binding.

    `kind` is the member's descriptor role: an instance method, a static
    method with no receiver, a class method whose receiver is the class
    symbol, or a property's getter, setter and deleter. A derived method
    (a dataclass ordering, a total_ordering partner, a single dispatch, a
    partial) carries the body builder that writes its equation from the
    class's own rows instead of compiling source.
    """

    def __init__(self, owner: Any, name: str, fn: Callable[..., Any], *, kind: str = "instance",
                 python_name: str | None = None, memo: bool = False, abstract: bool = False,
                 final: bool = False, signature: inspect.Signature | None = None,
                 derived: Callable[[Method], Atom] | None = None, bindings: dict[str, Any] | None = None):
        self.owner, self.python_name, self.py, self.kind = owner, python_name or name, fn, kind
        word = _word(self.python_name)
        self.name = f"retire-{owner.name}-{word[7:]}" if kind == "deleter" else f"{owner.name}-{word}"
        self.private = self.python_name.startswith("_") and not _dunder(self.python_name)
        self.memo, self.abstract, self.final, self.derived = memo, abstract, final, derived
        self.setter: Method | None = None
        self.deleter: Method | None = None
        self.generator = inspect.isgeneratorfunction(fn)
        # A class-local annotation has its completed class in scope, just as
        # the method's lexical __class__ cell does. The source function and its
        # globals remain the author's objects.
        source_fn = classes.contextual_function(owner.cls, typing.cast(types.FunctionType, fn), bindings=bindings)
        self.source_fn = source_fn
        self.hints = resolved_annotations(source_fn)
        signature = signature or inspect.signature(source_fn)
        self.signature = signature.replace(parameters=[
            parameter.replace(annotation=self.hints.get(name, parameter.annotation))
            for name, parameter in signature.parameters.items()
        ], return_annotation=self.hints.get("return", signature.return_annotation))
        parameters = tuple(self.signature.parameters.values())
        positional = (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        if kind == "static":
            self.receiver_name: str | None = None
            self.call_signature = self.signature
        else:
            if not parameters or parameters[0].kind not in positional:
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

    @property
    def is_property(self) -> bool:
        return self.kind == "property"

    def __get__(self, instance: Any, cls: type | None = None) -> Method | BoundMethod:
        if self.kind == "static":
            return self
        if self.kind == "class":
            return BoundMethod(self, cls if instance is None else type(instance))
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
        if self.kind == "class":
            # The class symbol of the actual class, so a subclass's override wins.
            actual = classes.declaration(instance if isinstance(instance, type) else type(instance)) or self.owner
            return Symbol(actual.name)
        actual = classes.declaration(type(instance))
        if actual is None or self.owner.space.dropped:
            msg = f"{self.owner.name}.{self.python_name} has retired; declare the class before calling its methods"
            raise ReferenceError(msg)
        return project(instance).atom if actual.grain == "value" else actual.receiver(instance)

    def invoke(self, instance: Any, args: Any, kwargs: Any) -> Any:
        receiver = self.receiver(instance)
        return call_values.NativeCallable(self.bound_atom(receiver), self.owner.space, Any)(*args, **kwargs)

    @property
    def member(self) -> Symbol:
        return Symbol(_word(self.python_name))

    def bound_atom(self, receiver: Atom | None = None) -> Atom:
        arguments = Variable("method-arguments")
        if self.receiver_name is None:
            positional: Atom = arguments
            parameters: list[Atom] = []
        else:
            parameters = [] if receiver is not None else [Variable(binding_name(self.receiver_name))]
            receiver = receiver if receiver is not None else parameters[0]
            positional = _expr(S["cons-atom"], _expr(S.noeval, receiver), arguments)
        call = call_syntax.member_application(self.owner, self.member, positional, _expr(S.noeval, Expression([])))
        return _expr(S["|->"], Expression([*parameters, _expr(S[":seg"], arguments)]),
                     _expr(S.evalc, call, Symbol(self.owner.space.name)))

    @property
    def receiver_type(self) -> Atom:
        """The arrow's first input: the class for a receiver, `Type` for a class method's class symbol."""
        return S.Type if self.kind == "class" else Symbol(self.owner.name)

    def compile(self) -> None:
        owner = self.owner
        result_types = tuple(field_values.type_atoms(self.result_type, retained=True))
        inputs = [*([] if self.receiver_name is None else [[self.receiver_type]]), *(
            [S.Expression] if parameter.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD) else
            field_values.type_atoms(parameter.annotation if parameter.annotation is not inspect.Parameter.empty else Any, retained=True)
            for parameter in self.call_signature.parameters.values()
        ), result_types]
        for chain in itertools.product(*inputs):
            owner.space.add(_expr(S[":"], Symbol(self.name), _expr(S["->"], *chain)))
        documentation = documentation_atom(self.name, self.py, kind="function", parameters=tuple(self.signature.parameters), annotations=self.hints)
        if documentation is not None:
            owner.space.add(documentation)
        if self.abstract:
            # The arrow is the whole declaration: a conforming subclass writes the equation.
            owner.space.add(_expr(S.abstract, Symbol(self.name)))
            return
        auxiliary: tuple[Expression, ...] = ()
        if self.derived is not None:
            body = self.derived(self)
        else:
            try:
                compiled = define.compile_function(
                    self.source_fn, known=owner.space.is_function,
                    nondet=lambda name: any(method.generator and name in (
                        method.name, _word(method.python_name)
                    ) for plan in (owner, *owner.bases) for method in plan.methods.values()),
                    metta_name=self.name,
                    # A class method's receiver is the defining class while its body
                    # compiles, a host binding rather than a parameter.
                    signature=self.call_signature if self.kind == "class" else self.signature,
                    class_context=owner.cls,
                    method_receiver=None if self.kind in ("class", "static") else self.receiver_name,
                    native_result_types=result_types,
                )
            except CompileError as error:
                print(f"{owner.name}.{self.python_name}: {error}\nkept as a host equation with effect oracleIO", file=sys.stderr)
                body = self.host_body(result_types)
            else:
                self.compiled = compiled
                owner.dependencies.update(compiled.class_dependencies)
                owner.import_dependencies(compiled.libraries, (compiled.body, *compiled.aux, *self.defaults.values()))
                call_syntax.link(owner.space, compiled.runtime_ops)
                body, auxiliary = compiled.body, tuple(compiled.aux)
        head = _expr(Symbol(self.name), *(Variable(binding_name(name)) for name in self.signature.parameters))
        self.equations = (*auxiliary, _expr(S["="], head, body))
        self.projected = self.equations
        for equation in self.equations:
            self.rows.extend(classes._owned_add(owner.space, equation))
        if self.private:
            owner.space.add(_expr(S.internal, Symbol(self.name)))
        if self.memo:
            # cache, lru_cache and cached_property are lib_memo's memoize; its
            # bound is the process budget of config-memoize, so maxsize is prose.
            owner.import_dependencies({"memo"}, (_expr(S.memoize, Symbol(self.name)),))
            owner.answer(_expr(S.memoize, Symbol(self.name)))
        self.install_binding()

    def host_body(self, result_types: tuple[Atom, ...]) -> Atom:
        """A refused source uses the same equation and its owned host operation."""
        head = f"_host-{self.name}"

        def invoke(*arguments: Atom) -> Any:
            values = {}
            for (name, parameter), argument in zip(self.signature.parameters.items(), arguments, strict=True):
                annotation = (
                    tuple[Any, ...] if parameter.kind is inspect.Parameter.VAR_POSITIONAL else
                    dict[str, Any] if parameter.kind is inspect.Parameter.VAR_KEYWORD else
                    parameter.annotation if parameter.annotation is not inspect.Parameter.empty else Any
                )
                values[name] = build(argument, annotation) if name != self.receiver_name else build(argument)
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
        scope = {name: binding_name(name) for name in self.signature.parameters}
        entry_bindings = call_syntax.parameter_scope(self.signature, scope)
        body: Atom = _expr(Symbol(head), *(Variable(variable) for variable in scope.values()))
        body = call_syntax.parameter_body(body, entry_bindings, result_types)
        if entry_bindings:
            self.owner.import_dependencies({"dict"}, (body,))
        return body

    def install_binding(self) -> None:
        """Bind Python call syntax, then evaluate its ordinary native application.

        A static method has no receiver, so only the unbound application and
        the canonical image are published; a class method's receiver is the
        class symbol, typed `Type`.
        """
        home = Symbol(self.owner.space.name)
        parameters = Expression([Variable(f"call-parameter-{index}") for index, _ in enumerate(self.signature.parameters)])
        canonical = _expr(S["|->"], parameters, _expr(S.evalc, _expr(Symbol(self.name), *parameters.children), home))
        binder = S["_python-bind-parameters"]
        call_syntax.link(self.owner.space, (binder.name,))
        member = self.member
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
        self.owner.space.add(_expr(S.internal, unbound))
        applications = [(self.bound_atom(), _expr(S.noeval, positional)), (canonical, _expr(S.noeval, positional))]
        if self.receiver_name is not None:
            self.owner.space.add(_expr(S["="], _expr(apply, receiver, positional, keywords),
                                       _expr(S.let, complete, _expr(S["cons-atom"], _expr(S.noeval, receiver), positional),
                                             _expr(unbound, complete, keywords))))
            self.owner.space.add(_expr(S[":"], apply, _expr(S["->"], self.receiver_type, S.Expression, S.Expression, S["%Undefined%"])))
            self.owner.space.add(_expr(S["="], _expr(Symbol(self.bind_name), receiver),
                                       _expr(S.noeval, self.bound_atom(receiver))))
            self.owner.space.add(_expr(S[":"], Symbol(self.bind_name), _expr(S["->"], self.receiver_type, S.Atom)))
            self.owner.space.add(_expr(S["@python-binding"], self.bound_atom(receiver), canonical, Grounded(1)))
            applications.insert(0, (self.bound_atom(receiver), _expr(S["cons-atom"], _expr(S.noeval, receiver), positional)))
        self.owner.space.add(_expr(S["@python-binding"], self.bound_atom(), canonical, Grounded(0)))
        self.owner.space.add(_expr(S["@python-callable"], canonical, call_signatures.project(self.signature, call_values.argument), S.stream if self.generator else S.one))
        for image, arguments in applications:
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
    """Inspect every own member before any class body is compiled.

    A plain function is a method; a special method Python routes syntax to
    compiles under its word; a property, a cached property, a static or class
    method, a cache wrapper, a single dispatcher and a partial are the
    descriptors the reference names, each read for the functions it holds;
    the comparisons dataclasses and total_ordering wrote derive from the
    class's own rows; every other special member runs at declaration.
    """
    for name, member in vars(plan.cls).items():
        for method in _members(plan, name, member):
            plan.methods[method.python_name] = method


def _flagged(plan: Any, name: str, fn: Any, **options: Any) -> Method:
    """A Method carrying the abstract and final marks its function or protocol class wrote."""
    protocol = vars(plan.cls).get("_is_protocol", False)
    return Method(
        plan, name, fn,
        abstract=bool(getattr(fn, "__isabstractmethod__", False) or protocol),
        final=bool(getattr(fn, "__final__", False)), **options,
    )


def _members(plan: Any, name: str, member: Any) -> list[Method]:
    cls = plan.cls
    if name == "__del__" and inspect.isfunction(member):
        msg = (
            f"{plan.name}.__del__ has no finaliser to run: the engine has no reference counting, "
            f"so release an instance with a scope or `with` instead"
        )
        raise CompileError(msg, construct="del method", line=member.__code__.co_firstlineno)
    if _dunder(name) and name not in _COMPILED_DUNDERS:
        # __init__, __new__, __init_subclass__, __hash__ and the rest run at declaration.
        return []
    if isinstance(member, property):
        if member.fget is None:
            return []
        getter = _flagged(plan, name, member.fget, kind="property")
        if member.fset is not None:
            getter.setter = Method(plan, name, member.fset, kind="setter", python_name=f"{name}!")
        if member.fdel is not None:
            getter.deleter = Method(plan, name, member.fdel, kind="deleter", python_name=f"retire-{name}")
        return [getter, *(companion for companion in (getter.setter, getter.deleter) if companion is not None)]
    if isinstance(member, functools.cached_property):
        return [Method(plan, name, member.func, kind="property", memo=True)]
    if isinstance(member, staticmethod):
        return [_flagged(plan, name, member.__func__, kind="static")]
    if isinstance(member, classmethod):
        fn = member.__func__
        receiver = next(iter(inspect.signature(fn).parameters), None)
        return [_flagged(plan, name, fn, kind="class", bindings={receiver: cls} if receiver else None)]
    if isinstance(member, functools._lru_cache_wrapper):
        return [Method(plan, name, member.__wrapped__, memo=True)]
    if isinstance(member, functools.singledispatchmethod):
        return _single_dispatch(plan, name, member)
    if isinstance(member, functools.partialmethod):
        return [_partial(plan, name, member)]
    if not inspect.isfunction(member):
        return []
    if _dunder(name):
        derived = _derived_comparison(plan, name, member)
        if derived is None and _generated(member):
            # dataclasses' __eq__ on a value is the term's own structural equality.
            return []
        return [_flagged(plan, name, member, derived=derived)]
    return [_flagged(plan, name, member)]


def _operands(method: Method) -> tuple[Variable, Variable]:
    receiver, other = list(method.signature.parameters)[:2]
    return Variable(binding_name(receiver)), Variable(binding_name(other))


def _field_pairs(plan: Any, left: Atom, right: Atom) -> list[tuple[Atom, Atom]]:
    """The class's compare fields read on both operands, in definition order."""
    names = [field.name for field in dataclasses.fields(plan.cls) if field.compare] if dataclasses.is_dataclass(plan.cls) else [
        field.name for field in plan.stored_fields
    ]
    return [(field_call(plan, name, left), field_call(plan, name, right)) for name in names]


def _all_equal(pairs: list[tuple[Atom, Atom]]) -> Atom:
    result: Atom = Grounded(value=True)
    for left, right in reversed(pairs):
        result = _expr(S["and"], _expr(S["=="], left, right), result)
    return result


def _lexicographic(pairs: list[tuple[Atom, Atom]], strict: str, *, or_equal: bool) -> Atom:
    """Tuple comparison as the reference defines it: the first differing field decides."""
    result: Atom = Grounded(value=or_equal)
    for left, right in reversed(pairs):
        result = _expr(S["or"], _expr(Symbol(strict), left, right), _expr(S["and"], _expr(S["=="], left, right), result))
    return result


def _equality(plan: Any, method: Method, left: Atom, right: Atom) -> Atom:
    """`self == other` inside a derived comparison: the class's eq when it writes one, else structural."""
    if selected(plan, "__eq__") is not None and selected(plan, "__eq__") is not method:
        return _expr(selector(plan, "__eq__"), left, right)
    return _expr(S["=="], left, right)


def _derived_comparison(plan: Any, name: str, fn: Any) -> Callable[[Method], Atom] | None:
    written = fn.__code__.co_name
    if fn.__module__ == "functools" and getattr(functools, written, None) is fn:
        # functools.total_ordering wrote this one from the root the class
        # defined; it renames the function, so the code object names the source.
        root = f"__{written.rsplit('_from_', 1)[1]}__"
        formula = dict(_TOTAL_ORDERING[root])[name]

        def total_ordering(method: Method) -> Atom:
            left, right = _operands(method)
            base = _expr(selector(plan, root), left, right)
            equal = _equality(plan, method, left, right)
            not_base, not_equal = _expr(S["not"], base), _expr(S["not"], equal)
            return {
                "not root and not eq": _expr(S["and"], not_base, not_equal),
                "root or eq": _expr(S["or"], base, equal),
                "not root": not_base,
                "not root or eq": _expr(S["or"], not_base, equal),
                "root and not eq": _expr(S["and"], base, not_equal),
            }[formula]

        return total_ordering
    if not _generated(fn):
        return None
    if name in _ORDERINGS:
        strict, or_equal = _ORDERINGS[name]

        def ordering(method: Method) -> Atom:
            left, right = _operands(method)
            return _lexicographic(_field_pairs(plan, left, right), strict, or_equal=or_equal)

        return ordering
    if name == "__eq__" and plan.grain != "value":

        def equality(method: Method) -> Atom:
            left, right = _operands(method)
            return _all_equal(_field_pairs(plan, left, right))

        return equality
    return None


def _single_dispatch(plan: Any, name: str, member: functools.singledispatchmethod) -> list[Method]:
    """One equation choosing by the first argument's type over the registered implementations."""
    implementations: dict[type, Method] = {}
    for kind, fn in member.dispatcher.registry.items():
        implementation = Method(plan, name, fn, python_name=f"{name}:for:{kind.__name__}")
        implementation.private = True
        implementations[kind] = implementation

    def dispatch(method: Method) -> Atom:
        receiver, subject = _operands(method)
        rest = [Variable(binding_name(parameter)) for parameter in list(method.signature.parameters)[2:]]
        arms = [
            Expression([atom, _expr(Symbol(implementation.name), receiver, subject, *rest)])
            for registered, implementation in implementations.items() if registered is not object
            for atom in field_values.type_atoms(registered, retained=False)
        ]
        fallback = implementations[object]
        arms.append(Expression([Variable("_"), _expr(Symbol(fallback.name), receiver, subject, *rest)]))
        return _expr(S.case, _expr(S["get-type"], subject), Expression(arms))

    public = Method(plan, name, member.func, derived=dispatch)
    return [public, *implementations.values()]


def _partial(plan: Any, name: str, member: functools.partialmethod) -> Method:
    """A curried equation: the fixed arguments are written into the body."""
    if member.keywords:
        msg = f"{plan.name}.{name} fixes keyword arguments; a partial method fixes its leading positional arguments"
        raise CompileError(msg, construct="partial method", line=1)
    target = member.func
    parameters = list(inspect.signature(target).parameters.values())
    receiver, fixed, remaining = parameters[0], parameters[1:1 + len(member.args)], parameters[1 + len(member.args):]
    if len(fixed) != len(member.args):
        msg = f"{plan.name}.{name} fixes more arguments than {getattr(target, '__name__', 'its function')} takes"
        raise CompileError(msg, construct="partial method", line=1)
    signature = inspect.Signature([receiver, *remaining], return_annotation=inspect.signature(target).return_annotation)

    def curried(method: Method) -> Atom:
        called = next(
            (candidate for owner in (plan, *plan.bases) for candidate in owner.methods.values() if candidate.py is target),
            None,
        )
        if called is None:
            msg = f"{plan.name}.{name} is a partial of {getattr(target, '__name__', 'a function')}, which is not a method of the class"
            raise CompileError(msg, construct="partial method", line=1)
        variables = [Variable(binding_name(parameter)) for parameter in method.signature.parameters]
        return _expr(Symbol(called.name), variables[0], *(call_values.argument(value) for value in member.args), *variables[1:])

    return Method(plan, name, target, signature=signature, derived=curried)


def _conform(plan: Any) -> None:
    """Sealed and abstract heads, checked when a class declares under its bases."""
    for base in plan.bases:
        if getattr(base.cls, "__final__", False):
            msg = f"{base.name} is @typing.final; {plan.name} cannot declare under it"
            raise CompileError(msg, construct="final class", line=1)
    for name, method in plan.methods.items():
        for base in plan.bases:
            sealed = base.methods.get(name)
            if sealed is not None and sealed.final:
                msg = f"{base.name}.{name} is @typing.final; {plan.name} cannot redefine it"
                raise CompileError(msg, construct="final method", line=1)
        if getattr(method.py, "__override__", False) and not any(name in vars(ancestor) for ancestor in plan.cls.__mro__[1:]):
            msg = f"{plan.name}.{name} is @typing.override but no base defines {name}; drop the decorator or define it on a base"
            raise CompileError(msg, construct="override declaration", line=1)
    concrete = not getattr(plan.cls, "__abstractmethods__", ()) and not vars(plan.cls).get("_is_protocol", False)
    if not concrete:
        return
    for base in plan.bases:
        for name, method in base.methods.items():
            if method.abstract:
                chosen = selected(plan, name)
                if chosen is None or chosen.abstract:
                    msg = f"{base.name}.{name} is abstract and {plan.name} writes no equation for it; define the method"
                    raise CompileError(msg, construct="abstract method", line=1)


def compile_methods(plan: Any) -> None:
    _conform(plan)
    for method in plan.methods.values():
        method.compile()


def _entry_pattern(concrete: Any, target: Symbol, arity: int, *, class_receiver: bool = False) -> Expression:
    fields = tuple(Variable(f"method-field-{index}") for index in range(
        len(concrete.stored_fields) if concrete.grain == "value" else 1
    ))
    receiver = Symbol(concrete.name) if class_receiver else concrete.term(*fields)
    arguments = tuple(Variable(f"method-argument-{index}") for index in range(arity - 1))
    return _expr(target, receiver, *arguments)


def _synchronize_selection(
    concrete: Any, home: Any, name: str, after: Any, *, public: set[str],
    rows: dict[tuple[str, Atom], Any], providers: dict[tuple[Any, Any], dict[str, list[Atom]]],
) -> None:
    """The rows and provider targets one MRO selection contributes to a home."""
    method = selected(concrete, name, after=after)
    if method is None or method.kind == "static":
        # A static method has no receiver to dispatch on: its callers name its equation.
        return
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
            source = f"{home.name}-adapt-{concrete.name}-{_word(name)}"
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
        pattern = _entry_pattern(concrete, target, arity, class_receiver=method.kind == "class")
        if method.private:
            body = _expr(Symbol(source), *pattern.args)
            if home is not method.owner:
                body = _expr(S.evalc, body, Symbol(method.owner.space.name))
            rows[home.space.name, _expr(S["="], pattern, body)] = home.space
            rows[home.space.name, _expr(S.internal, target)] = home.space
        else:
            providers.setdefault((home, method.owner), {}).setdefault(source, []).append(pattern)



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
                    _synchronize_selection(concrete, home, name, after, public=public, rows=rows, providers=providers)
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
    """Put each Method where its member was, so Python's own protocol reaches the equation.

    A property keeps a property, whose accessors invoke the getter, setter
    and deleter equations; a static or class method keeps its descriptor
    binding through Method.__get__; a special method is looked up on the
    type, so the descriptor there is what `a + b` and `len(a)` reach.
    """
    for name, method in plan.methods.items():
        if method.kind in ("setter", "deleter"):
            continue
        if method.kind == "property":
            def read(instance: Any, method: Method = method) -> Any:
                return method.invoke(instance, (), {})

            def write(instance: Any, value: Any, method: Method = method) -> None:
                assert method.setter is not None  # nosec B101 # installed only for a property that has one
                method.setter.invoke(instance, (value,), {})

            def delete(instance: Any, method: Method = method) -> None:
                assert method.deleter is not None  # nosec B101 # installed only for a property that has one
                method.deleter.invoke(instance, (), {})

            plan.replace_attribute(name, property(
                read, write if method.setter is not None else None, delete if method.deleter is not None else None,
                doc=method.py.__doc__,
            ))
            continue
        plan.replace_attribute(name, method)
