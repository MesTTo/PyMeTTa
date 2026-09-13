"""Purpose: declare completed Python classes as engine values, entities or spaces.

Owns resources:
  - each declaration owns its class space while reachable from a declaring
    home or a kept Scope value; entity occurrences and private spaces follow
    explicit retirement and Scope cleanup [tested: test_class_grain_lifetimes;
    commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
Guarded by:
  - definitions._DEFINE_LOCK serializes declaration, instrumentation and proxy
    reconstruction; outer commit checks reject stale proxy publications
    [tested: test_concurrent_reconstruction_publishes_one_python_proxy,
    test_overlapping_transactions_cannot_publish_distinct_proxies; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
Guarantees:
  - Python field setters preserve computed syntax values at typed native
    writers [tested: test_field_assignment_keeps_computed_syntax_values;
    commit=310a9d8b547a77412a518a37ab79fba073eb22ac]
  - constructor arguments reach typed entries as values after their source
    computations finish [tested:
    test_constructor_arguments_preserve_values_and_run_factories; commit=310a9d8b547a77412a518a37ab79fba073eb22ac]
  - generated field and class-variable queries return the stored syntax
    rather than their lookup expression [tested:
    test_generated_syntax_field_queries_return_the_stored_value,
    test_generated_class_variable_queries_return_the_stored_atom; commit=397a0df18bea23dee8774a721c2bdcd7dfc38c5e]
  - imports follow the declared package foundations [tested:
    tests/checks/check_layering.py; commit=ab9d3489f87e0d7b7be4b3cd2025494cd62699fe]
  - mutable Python instances find their engine receiver through ordinary private
    proxy facts, including slotted and unhashable classes [tested:
    test_class_proxies_share_engine_fields; commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
  - compiled dependencies retain explicit private imports even when another
    space already made their names globally callable [tested:
    test_constructor_dependencies_survive_a_previous_global_import_leaving;
    commit=9b0a084e534ddf7dd67980ad84c27c8279b877f1]
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import sys
import textwrap
import types
import typing
from collections.abc import Sequence
from enum import Enum, Flag
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr, fresh
from metta._atoms.names import attribute_name
from metta._atoms.registry import _record_registration, _Registration
from metta._catalog.annotations import referenced_classes, type_atoms_for
from metta._catalog.build import build
from metta._catalog.call_values import apply_sources
from metta._catalog.documentation import attribute_docstrings, documentation_atom
from metta._catalog.project import declarations, project
from metta._declare import field_values, operations
from metta._errors.errors import EngineError
from metta._lazy import lazy
from metta._spaces.handle import SpaceHandle

_DECLARATIONS: dict[type, ClassDeclaration] = {}
_ABSENT = object()


def declaration(cls: Any) -> ClassDeclaration | None:
    """Read an exact class declaration; inherited conversion is not declaration."""
    return _DECLARATIONS.get(cls) if isinstance(cls, type) else None


def owner_of(space: Any) -> ClassDeclaration | None:
    """Find the declaration whose source home is this space."""
    return next((plan for plan in _DECLARATIONS.values() if plan.space._name == space._name), None)


def callable_dependencies(fn: Any) -> set[type]:
    """Return declared classes named by a callable's resolved signatures."""
    from metta._catalog.annotations import (  # noqa: PLC0415 -- the annotation layer also reads declarations
        resolved_annotations,
    )

    annotations = [annotation for signature in (fn, *typing.get_overloads(fn))
                   for annotation in resolved_annotations(signature).values()]
    return {cls for cls in referenced_classes(annotations) if declaration(cls) is not None}


@dataclasses.dataclass(frozen=True, slots=True)
class Field:
    """One declared field, independent of the grain that stores it."""

    name: str
    annotation: Any = Any
    default: Any = dataclasses.field(default_factory=lambda: _ABSENT)
    factory: Any = None
    init: bool = True
    kw_only: bool = False
    initvar: bool = False


def _user_bases(cls: type) -> tuple[type, ...]:
    space_class = lazy('metta._faces.space').Space
    bases = cls.__mro__
    return bases[:bases.index(space_class)] if space_class in bases else tuple(base for base in bases if base not in (object, tuple))


def _hints(cls: type) -> dict[str, Any]:
    hints = {}
    for base in reversed(_user_bases(cls)):
        namespace = getattr(sys.modules.get(base.__module__), "__dict__", {}) | dict(vars(base))
        namespace.update({ancestor.__name__: ancestor for ancestor in cls.__mro__})
        own = types.SimpleNamespace(__annotations__=inspect.get_annotations(base))
        try:
            hints.update(typing.get_type_hints(own, globalns=namespace, localns=namespace, include_extras=True))
        except (NameError, TypeError) as error:
            msg = f"{cls.__qualname__} has an unresolved field annotation: {error}"
            raise TypeError(msg) from error
    return hints


def _fields(cls: type, hints: dict[str, Any]) -> tuple[Field, ...]:
    dataclass_fields = {
        field.name: Field(
                field.name,
                hints.get(field.name, Any).type
                if isinstance(hints.get(field.name), dataclasses.InitVar)
                else hints.get(field.name, Any),
                field.default if field.default is not dataclasses.MISSING else _ABSENT,
                field.default_factory if field.default_factory is not dataclasses.MISSING else None,
                field.init, field.kw_only,
                isinstance(hints.get(field.name), dataclasses.InitVar),
        )
        for field in getattr(cls, "__dataclass_fields__", {}).values()
        if typing.get_origin(hints.get(field.name)) is not typing.ClassVar
    }
    names = dict.fromkeys(dataclass_fields)
    names.update(dict.fromkeys(
        name for name, hint in hints.items()
        if typing.get_origin(hint) is not typing.ClassVar
    ))
    for base in reversed(_user_bases(cls)):
        owner = declaration(base)
        if owner is not None:
            names.update(dict.fromkeys(field.name for field in owner.fields))
        slots = vars(base).get("__slots__", ())
        for name in (slots,) if isinstance(slots, str) else slots:
            if name not in {"__dict__", "__weakref__"}:
                names.setdefault(_mangle(base, name))
        fn = vars(base).get("__init__")
        if owner is not None:
            fn = owner.initializer
        if not inspect.isfunction(fn):
            continue
        try:
            node = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        except (OSError, TypeError):
            continue
        receiver = next(iter(inspect.signature(fn).parameters), "self")
        parameter_hints = inspect.get_annotations(fn, eval_str=True)
        for assignment in ast.walk(node):
            if not isinstance(assignment, (ast.Assign, ast.AnnAssign)):
                continue
            targets = assignment.targets if isinstance(assignment, ast.Assign) else [assignment.target]
            for target in targets:
                if not isinstance(target, ast.Attribute) or not isinstance(target.value, ast.Name):
                    continue
                if target.value.id != receiver:
                    continue
                name = _mangle(base, target.attr)
                names.setdefault(name)
                value = assignment.value
                if isinstance(value, ast.Name) and value.id in parameter_hints:
                    hints.setdefault(name, parameter_hints[value.id])
                elif isinstance(value, ast.Constant) and value.value is not None:
                    hints.setdefault(name, type(value.value))
    defaults = getattr(cls, "_field_defaults", {})
    fields = []
    for name in names:
        if name in dataclass_fields:
            fields.append(dataclass_fields[name])
            continue
        default = defaults.get(name, inspect.getattr_static(cls, name, _ABSENT))
        if hasattr(type(default), "__get__"):
            default = _ABSENT
        fields.append(Field(name, hints.get(name, Any), default))
    return tuple(fields)


def _mangle(cls: type, name: str) -> str:
    return f"_{cls.__name__.lstrip('_')}{name}" if name.startswith("__") and not name.endswith("__") else name


def _sequence(expressions: Sequence[Atom], result: Atom) -> Atom:
    for index, expression in reversed(list(enumerate(expressions))):
        result = _expr(S.chain, expression, Variable(f"class-step-{index}"), result)
    return result


def _owned_add(space: Any, row: Atom) -> list[tuple[str, int]]:
    """Retain the exact occurrence a derived declaration adds to another home."""
    added = space._rt.must(
        "metta_py_decode_shared(Wire, _Row, _), "
        "metta_add_atom(Space, _Row, _Token, true), "
        "findall(_Token, nonvar(_Token), Tokens)",
        Space=space.name, Wire=row.to_wire(),
    )
    return [(space.name, token) for token in added["Tokens"]]


def _withdraw_rows(runtime: Any, rows: list[tuple[str, int]]) -> None:
    for space, token in reversed(rows):
        runtime.must("spaces:metta_remove_occurrence(Space, Token, _)", Space=space, Token=token)


class ClassDeclaration:
    """The inspected class shape and its class space, never an instance store."""

    def __init__(self, cls: type, space: Any, *, accessors: bool):
        self.cls = cls
        self.name = cls.__qualname__.split("<locals>.")[-1]
        previous = lazy('metta.integrate')._type_registration(cls)
        if previous is not None:
            self.name = previous.type_name
        self.previous_registration = previous
        self.originals: dict[str, Any] = {}
        self.operations: dict[str, Any] = {}
        self.field_adopter: Symbol | None = None
        self.borrowers: set[str] = set()
        self.bases: tuple[ClassDeclaration, ...] = ()
        self.references: tuple[ClassDeclaration, ...] = ()
        self.reference_rows: list[tuple[str, int]] = []
        self.inherited_rows: dict[ClassDeclaration, list[tuple[str, int]]] = {}
        self.public_accessors = accessors
        self.hints = _hints(cls)
        self.classvars = {
            name: typing.get_args(hint)[0] for name, hint in self.hints.items()
            if typing.get_origin(hint) is typing.ClassVar
        }
        space_class = lazy('metta._faces.space').Space
        dataclass_parameters = getattr(cls, "__dataclass_params__", None)
        if issubclass(cls, space_class):
            self.grain = "prototype"
        elif issubclass(cls, Enum) or (issubclass(cls, tuple) and hasattr(cls, "_fields")) or (
            dataclass_parameters is not None and dataclass_parameters.frozen
        ):
            self.grain = "value"
        else:
            self.grain = "entity"
        self.enum = issubclass(cls, Enum)
        self.fields = () if self.enum else _fields(cls, self.hints)
        self.stored_fields = tuple(field for field in self.fields if not field.initvar)
        self.field_map = {field.name: field for field in self.stored_fields}
        self.initializer = inspect.getattr_static(cls, "__init__", object.__init__)
        if "__init__" not in vars(cls):
            inherited = next((declaration(base) for base in cls.__mro__[1:] if declaration(base) is not None), None)
            if inherited is not None:
                self.initializer = inherited.initializer
            elif self.grain == "prototype":
                self.initializer = object.__init__
        self.generated_init = self.initializer is object.__init__ or (
            inspect.isfunction(self.initializer)
            and self.initializer.__code__.co_filename == "<string>"
        ) or (issubclass(cls, tuple) and not self.enum)
        self.post_init = inspect.getattr_static(cls, "__post_init__", None)
        if self.enum:
            self.signature = inspect.Signature([inspect.Parameter("member", inspect.Parameter.POSITIONAL_ONLY)])
        elif inspect.isfunction(self.initializer):
            signature = inspect.signature(self.initializer)
            parameters = list(signature.parameters.values())[1:]
            if self.generated_init:
                fields = {field.name: field for field in self.fields}
                parameters = [parameter.replace(annotation=fields[parameter.name].annotation)
                              if parameter.name in fields else parameter
                              for parameter in parameters]
            self.signature = signature.replace(parameters=parameters)
        elif dataclass_parameters is not None and not dataclass_parameters.init:
            self.signature = inspect.Signature()
        else:
            parameters = [
                inspect.Parameter(
                    field.name,
                    inspect.Parameter.KEYWORD_ONLY if field.kw_only else inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    default=field.default if field.default is not _ABSENT else (
                        field.factory if field.factory is not None else inspect.Parameter.empty
                    ),
                    annotation=field.annotation,
                ) for field in self.fields if field.init
            ]
            parameters.sort(key=lambda parameter: parameter.kind)
            self.signature = inspect.Signature(parameters)
        self.dependencies = set(referenced_classes([
            *self.hints.values(),
            *(parameter.annotation for parameter in self.signature.parameters.values()),
        ]))
        self.space = space_class(f"&{self.name}", _runtime=space._rt)
        self.defaults: dict[str, Atom] = {}

    def field(self, name: str) -> Field | None:
        return self.field_map.get(name)

    def accessor(self, name: str, *, write: bool = False) -> Symbol:
        return Symbol(f"{self.name}-{attribute_name(name)}{'!' if write else ''}")

    @staticmethod
    def storage_head(name: str) -> Symbol:
        """Keep a private field name outside the declaration namespace."""
        return Symbol(f"_field-{attribute_name(name)}")

    def defining_class(self, name: str, function: Any) -> type:
        """Resolve lexical private names against the actual defining class."""
        for base in self.cls.__mro__:
            owner = declaration(base)
            candidate = vars(base).get(name)
            if owner is not None:
                candidate = owner.originals.get(name, candidate)
            if candidate is function:
                return base
        return self.cls

    def term(self, *parts: Atom) -> Expression:
        return _expr(Symbol(self.name), *parts)

    def replace_attribute(self, name: str, value: Any) -> None:
        self.originals.setdefault(name, vars(self.cls).get(name, _ABSENT))
        type.__setattr__(self.cls, name, value)

    def restore(self) -> None:
        for name, previous in reversed(tuple(self.originals.items())):
            if previous is _ABSENT:
                type.__delattr__(self.cls, name)
            else:
                type.__setattr__(self.cls, name, previous)
        _DECLARATIONS.pop(self.cls, None)

    def operation(self, fn: Any, *, name: str, **options: Any) -> Any:
        """Own a generated host implementation for the declaration's lifetime."""
        if name in operations.REGISTRY:
            msg = f"class helper {name} is already registered; rename the class or unregister the conflicting operation"
            raise TypeError(msg)
        wrapped = self.space.op(fn, name=name, **options)
        registered = operations._registered_operation(wrapped)
        assert registered is not None
        self.operations[name] = registered.fn
        return wrapped

    def release_operations(self) -> None:
        """Retire generated implementations without erasing a later replacement."""
        # The class space is being released or has already completed native
        # teardown. Forget its holdings before unregistering global callbacks.
        operations._forget_space(self.space._name)
        for name, fn in tuple(self.operations.items()):
            current = operations.REGISTRY.get(name)
            if current is not None and current.fn is fn:
                operations.unregister(self.space._rt, name)
            del self.operations[name]

    def encode(self, value: Any) -> Atom:
        return field_values.encode(self, value)

    def field_types(self, annotation: Any) -> list[Atom]:
        return field_values.type_atoms(self, annotation)

    def synchronize_bases(self) -> None:
        bases = tuple(plan for base in self.cls.__mro__[1:] if (plan := declaration(base)) is not None)
        references = tuple(sorted(
            (plan for cls in self.dependencies if (plan := declaration(cls)) is not None
             and plan is not self and plan not in bases),
            key=lambda plan: plan.name,
        ))
        if bases == self.bases and references == self.references:
            return
        previous, previous_references = self.bases, self.references
        previous_rows = self.reference_rows.copy()
        previous_accessors = {owner: rows.copy() for owner, rows in self.inherited_rows.items()}

        def undo() -> None:
            self.bases, self.references = previous, previous_references
            self.reference_rows, self.inherited_rows = previous_rows, previous_accessors

        operations._record_registry_undo(undo, description=f"class hierarchy {self.name}")
        _withdraw_rows(self.space._rt, self.reference_rows)
        self.reference_rows = []
        for owner in self.bases:
            if owner not in bases:
                _withdraw_rows(self.space._rt, self.inherited_rows.pop(owner))
        for owner in (*bases, *references):
            self.reference_rows.extend(_owned_add(self.space, _expr(S["from"], Symbol(owner.space.name))))
            if owner in bases and owner not in self.bases:
                self.inherited_rows[owner] = self.install_accessors(owner)
        nearest = dict.fromkeys(
            candidate for base in self.cls.__bases__
            if (candidate := next((declaration(ancestor) for ancestor in base.__mro__ if declaration(ancestor) is not None), None)) is not None
        )
        for owner in nearest:
            self.reference_rows.extend(_owned_add(self.space, _expr(S[":<"], Symbol(self.name), Symbol(owner.name))))
        self.bases, self.references = bases, references

    def import_dependencies(self, libraries: Any, expressions: Any) -> None:
        """Reference only library names mentioned by this compiled source."""
        from metta._atoms.library import (  # noqa: PLC0415 -- load only dependencies the compiler reports
            lib,
        )

        if not libraries:
            return
        names = set()
        pending = list(expressions)
        while pending:
            atom = pending.pop()
            if isinstance(atom, Expression):
                pending.extend(atom.children)
            elif isinstance(atom, Symbol):
                names.add(atom.name)
        before = set(self.space._rt.apply_must("metta_host_reference_names", self.space.name))
        wanted = Expression([Symbol(name) for name in sorted(names - before)])
        head = Variable("library-head")
        # A lambda filters actual exports; it does not claim that every name
        # mentioned by the source belongs to every dependency library.
        mapping = _expr(S["|->"], Expression([head]), _expr(S.only, wanted, head))
        for name in sorted(libraries):
            self.space.from_(getattr(lib, name), mapping)
        after = set(self.space._rt.apply_must("metta_host_reference_names", self.space.name))
        for name in sorted(after - before):
            self.space.add(_expr(S.internal, Symbol(name)))

    def receiver(self, instance: Any) -> Expression:
        key = Variable("class-receiver")
        answers = self.space.eval(_expr(S.match, Symbol(self.space.name), _expr(S["_python-proxy"], key, Grounded(instance)), key))
        if len(answers) != 1 or not isinstance(answers[0], Expression):
            msg = f"{self.name} instance has retired or its construction rolled back"
            raise ReferenceError(msg)
        return answers[0]

    def require_live(self, receiver: Expression) -> None:
        if not self.space.eval(_expr(S.match, Symbol(self.space.name), _expr(S["owned-by"], receiver), Grounded(value=True))):
            msg = f"{receiver} has retired or its construction rolled back"
            raise ReferenceError(msg)

    def project_parts(self, instance: Any) -> tuple[Any, ...]:
        if self.enum:
            return (instance.value if isinstance(instance, Flag) else Symbol(instance.name),)
        if self.grain == "value":
            return tuple(getattr(instance, field.name) for field in self.stored_fields)
        return tuple(self.receiver(instance).args)

    def rebuild(self, *parts: Any) -> Any:
        if self.enum:
            enum = typing.cast(type[Enum], self.cls)
            return enum(parts[0]) if issubclass(enum, Flag) else enum[parts[0].name]
        if self.grain == "value":
            if issubclass(self.cls, tuple):
                return tuple.__new__(self.cls, parts)
            instance: Any = object.__new__(self.cls)
            for field, value in zip(self.stored_fields, parts, strict=True):
                object.__setattr__(instance, field.name, value)
            return instance
        receiver = self.term(*(part if isinstance(part, Atom) else project(part).atom for part in parts))

        def attach() -> Any:
            self.require_live(receiver)
            result = Variable("class-proxy")
            found = self.space.eval(_expr(S.match, Symbol(self.space.name), _expr(S["_python-proxy"], receiver, result), result))
            if found:
                return found[0].value
            instance: Any = object.__new__(self.cls)
            self.attach(instance, receiver)
            return instance

        # Foreign callers own separate Prolog engines. Lock before opening the
        # snapshot; the outer commit check also covers pre-existing snapshots.
        from metta._declare.definitions import _DEFINE_LOCK  # noqa: PLC0415 -- peer cycle

        with _DEFINE_LOCK:
            return self.space.transaction(attach)

    def attach(self, instance: Any, receiver: Expression) -> None:
        self.space._rt.must("metta_py_attach_proxy(Space, Wire)", Space=self.space.name,
                            Wire=_expr(S["_python-proxy"], receiver, Grounded(instance)).to_wire())
        if self.grain == "prototype":
            part = typing.cast(Symbol | Expression, receiver.args[0])
            SpaceHandle.__init__(instance, part, _runtime=self.space._rt)

    def answer(self, expression: Atom) -> Atom:
        answers = self.space.eval(expression)
        if len(answers) != 1:
            msg = f"{expression} must answer once during construction, got {len(answers)}"
            raise EngineError(msg)
        answer = answers[0]
        if isinstance(answer, Expression) and answer.head == S.Error:
            raise EngineError(str(answer))
        return answer

    def initialize(self, instance: Any, *args: Any, **kwargs: Any) -> None:
        bound = self.signature.bind(*args, **kwargs)
        sources = self.argument_sources(bound.arguments, self.encode)

        def construct() -> None:
            if self.grain == "value":
                receiver = self.answer(apply_sources(Symbol(f"_initialize-{self.name}"), sources))
                for field, part in zip(self.stored_fields, receiver.args, strict=True):
                    object.__setattr__(instance, field.name, build(part, field.annotation))
                return
            receiver = self.answer(_expr(Symbol(f"_mint-{self.name}")))
            if not isinstance(receiver, Expression):
                msg = f"minting {self.name} did not produce a constructor term: {receiver}"
                raise EngineError(msg)
            self.attach(instance, receiver)
            self.answer(apply_sources(Symbol(f"_initialize-{self.name}"), (_expr(S.noeval, receiver), *sources)))

        self.space.transaction(construct)

    def argument_sources(self, supplied: dict[str, Any], encode: Any) -> tuple[Atom, ...]:
        """Quote supplied values; omitted parameters retain their default code."""
        result: list[Atom] = []
        for name, parameter in self.signature.parameters.items():
            if name in supplied:
                value = supplied[name]
                if parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                    result.append(_expr(S.noeval, Expression([encode(part) for part in value])))
                elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
                    result.append(self.keyword_arguments({key: encode(part) for key, part in value.items()}))
                else:
                    result.append(_expr(S.noeval, encode(value)))
            elif parameter.kind is inspect.Parameter.VAR_POSITIONAL:
                result.append(_expr(S.noeval, Expression([])))
            elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
                result.append(self.keyword_arguments({}))
            else:
                result.append(self.defaults[name])
        return tuple(result)

    def keyword_arguments(self, values: dict[str, Atom]) -> Atom:
        """Build a keyword mapping through the class's private library import."""
        pairs = Expression([Expression([Grounded(key), value]) for key, value in values.items()])
        held = fresh()
        return _expr(S.let, held, _expr(S.noeval, pairs),
                     _expr(S.evalc, _expr(S["dict-space"], held), Symbol(self.space.name)))

    def install_storage(self) -> None:
        part = Variable("identity")
        ctor = self.term(part)
        home = Symbol(self.space.name)
        internal = [S["owned-by"], S["_python-proxy"]]
        equations: list[Atom] = []
        if self.grain != "value":
            deferred = _expr(S["scope-defer"], ctor, _expr(S.evalc, _expr(Symbol(f"retire-{self.name}"), ctor), home))
            internal.append(Symbol(f"_mint-{self.name}"))
            created = _expr(S["add-atom"], home, _expr(S["owned-by"], ctor))
            if self.grain == "entity":
                created = _expr(S["add-atom"], home, _expr(S["owned-by"], ctor), part)
                minted = _sequence([created, deferred], ctor)
            else:
                minted = _expr(S.chain, _expr(S["new-space"]), part, _sequence([
                    _expr(S["add-atom"], part, _expr(S["from"], home)),
                    _expr(S["add-atom"], part, _expr(S.internal, *(self.storage_head(field.name) for field in self.stored_fields))),
                    created, deferred
                ], ctor))
            equations.append(_expr(S["="], _expr(Symbol(f"_mint-{self.name}")), minted))
            removals = []
            if self.grain == "prototype":
                removals.append(_expr(S["drop-space"], part))
            removals.extend([
                _expr(S["remove-atom"], home, _expr(Variable("field"), ctor, Variable("value"))),
                _expr(S["remove-atom"], home, _expr(S["owned-by"], ctor)),
            ])
            equations.append(_expr(S["="], _expr(Symbol(f"retire-{self.name}"), ctor), _sequence(removals, Grounded(value=True))))
        self.install_accessors(self)
        for field in self.stored_fields:
            internal.append(self.storage_head(field.name))
            if not self.public_accessors:
                internal.append(self.accessor(field.name))
                if self.grain != "value":
                    internal.append(self.accessor(field.name, write=True))
        for name, annotation in self.classvars.items():
            value = project(getattr(self.cls, name)).atom
            head = Symbol(f"_classvar-{attribute_name(name)}")
            internal.append(head)
            if not self.public_accessors:
                internal.append(self.accessor(name))
            equations.extend([
                _expr(head, value),
                _expr(S["="], _expr(self.accessor(name)), _expr(S.match, home, _expr(head, Variable("value")), Variable("value"))),
            ])
            equations.extend(_expr(S[":"], self.accessor(name), _expr(S["->"], field_values.query_result_type(result_type)))
                             for result_type in type_atoms_for(annotation))
        for head in dict.fromkeys(internal):
            self.space.add(_expr(S.internal, head))
        for equation in equations:
            self.space.add(equation)

    def install_accessors(self, owner: ClassDeclaration) -> list[tuple[str, int]]:
        """Compile this receiver layout for its defining class's field names."""
        retained = []
        part, value, new = Variable("identity"), Variable("value"), Variable("new-value")
        values = {field.name: Variable(f"field-{index}") for index, field in enumerate(self.stored_fields)}
        pattern = self.term(*values.values()) if self.grain == "value" else self.term(part)
        home = part if self.grain == "prototype" else Symbol(self.space.name)
        for field in self.stored_fields:
            if owner.field(field.name) is None:
                continue
            getter, writer = owner.accessor(field.name), owner.accessor(field.name, write=True)
            prefix = (self.storage_head(field.name),) if self.grain == "prototype" else (self.storage_head(field.name), pattern)
            row = _expr(*prefix, value)
            body = values[field.name] if self.grain == "value" else _expr(S.match, home, row, value)
            rows = [_expr(S["="], _expr(getter, pattern), body)]
            result_types = self.field_types(field.annotation)
            if self.grain != "value":
                result_types = [field_values.query_result_type(type_) for type_ in result_types]
            rows.extend(_expr(S[":"], getter, _expr(S["->"], Symbol(self.name), type_))
                        for type_ in result_types)
            if self.grain != "value":
                adopted = field_values.adopted(self, field, new)
                stored = Variable("stored-value") if adopted is not new else new
                written = _sequence([
                    _expr(S["remove-atom"], home, row),
                    _expr(S["add-atom"], home, _expr(*prefix, stored)),
                ], Grounded(value=True))
                if adopted is not new:
                    written = _expr(S.chain, adopted, stored, written)
                live = _expr(S.collapse, _expr(S.match, Symbol(self.space.name),
                                             _expr(S["owned-by"], pattern), Grounded(value=True)))
                refusal = _expr(S.Error, _expr(writer, pattern, new),
                                _expr(S.ReferenceError, Grounded(
                                    f"{self.name} receiver has retired; construct a new instance before writing fields")))
                body = _expr(S.transaction, _expr(S["if"], _expr(S["=="], live, Expression([])), refusal, written))
                rows.append(_expr(S["="], _expr(writer, pattern, new), body))
                rows.extend(_expr(S[":"], writer, _expr(S["->"], Symbol(self.name), type_, S.Bool))
                            for type_ in self.field_types(field.annotation))
            for row in rows:
                if owner is self:
                    owner.space.add(row)
                else:
                    retained.extend(_owned_add(owner.space, row))
        return retained

    def instrument(self) -> None:
        if self.enum or issubclass(self.cls, tuple):
            self.replace_attribute("__metta__", lambda instance: project(instance).atom)
            return
        plan = self

        def initialize(instance: Any, *args: Any, **kwargs: Any) -> None:
            (declaration(type(instance)) or plan).initialize(instance, *args, **kwargs)

        receiver = "self"
        while receiver in self.signature.parameters:
            receiver += "_"
        typing.cast(Any, initialize).__signature__ = self.signature.replace(parameters=[inspect.Parameter(receiver, inspect.Parameter.POSITIONAL_ONLY), *self.signature.parameters.values()])
        self.replace_attribute("__init__", initialize)
        if self.grain == "value":
            self.replace_attribute("__metta__", lambda instance: project(instance).atom)
            return
        self.replace_attribute("__metta__", lambda instance: (declaration(type(instance)) or plan).receiver(instance))
        for field in self.stored_fields:
            def read(instance: Any, name: str = field.name) -> Any:
                actual = declaration(type(instance)) or plan
                receiver = actual.receiver(instance)
                return build(actual.answer(_expr(actual.accessor(name), receiver)), actual.field_map[name].annotation)

            def write(instance: Any, value: Any, name: str = field.name) -> None:
                actual = declaration(type(instance)) or plan
                actual.answer(apply_sources(actual.accessor(name, write=True), (
                    _expr(S.noeval, actual.receiver(instance)),
                    _expr(S.noeval, actual.encode(value)),
                )))

            self.replace_attribute(field.name, property(read, write))
        if "__match_args__" not in vars(self.cls):
            self.replace_attribute("__match_args__", tuple(field.name for field in self.stored_fields if not field.kw_only))
        if self.grain == "prototype":
            space_property = inspect.getattr_static(SpaceHandle, "_space")

            def checked_space(instance: Any) -> Any:
                plan.receiver(instance)
                return space_property.fget(instance)

            def drop(instance: Any) -> None:
                try:
                    receiver = plan.receiver(instance)
                except ReferenceError:
                    return
                SpaceHandle.drop(instance)
                plan.space.remove(_expr(Variable("field"), receiver, Variable("value")))
                plan.space.remove(_expr(S["owned-by"], receiver))

            self.replace_attribute("_space", property(checked_space))
            self.replace_attribute("drop", drop)


def install(space: Any, cls: type, *, accessors: bool, methods: bool) -> type:
    """Publish one inspected class transactionally and retain its declaring space."""
    from metta._declare import (  # noqa: PLC0415 -- shared installer lock owns this cycle
        constructors,
        definitions,
    )

    integrate = lazy('metta.integrate')
    with definitions._DEFINE_LOCK:
        standing = declaration(cls)
        consumer = owner_of(space)
        if standing is not None and (space.name in standing.borrowers or consumer is standing):
            return cls

        def publish() -> type:
            plan = standing or ClassDeclaration(cls, space, accessors=accessors)
            if standing is None:
                operations._record_registry_undo(plan.restore, description=f"class instrumentation {plan.name}")
                _DECLARATIONS[cls] = plan
                expected = integrate._enlist_type_preimage(cls)
                names: tuple[str, ...]
                kinds: tuple[Any, ...]
                if plan.enum:
                    names, kinds = ("member",), ((int,) if issubclass(cls, Flag) else (Symbol,))
                elif plan.grain == "value":
                    names = tuple(field.name for field in plan.stored_fields)
                    kinds = tuple(field.annotation for field in plan.stored_fields)
                else:
                    names, kinds = ("receiver",), (Atom,)
                try:
                    _record_registration(cls, _Registration("expression", plan.project_parts, plan.rebuild, plan.name, names, kinds))
                finally:
                    expected[0] = integrate._type_registration(cls)
                space._rt.must("metta_py_declare_space(Model, Space, Argument)", Model="scoped", Space=plan.space.name, Argument="&self")
                plan.space.add(_expr(S["from"], _expr(S.library, S["lib_thread"]), _expr(S.only, Expression([S["scope-defer"], S["drop-space"]]))))
                plan.space.add(_expr(S.internal, S["scope-defer"], S["drop-space"]))
                plan.space.add(_expr(S[":"], Symbol(plan.name), S.Type))
                for row in declarations(cls):
                    plan.space.add(row)
                plan.install_storage()
                for known in tuple(_DECLARATIONS.values()):
                    known.synchronize_bases()
                constructors.install(plan)
                for known in tuple(_DECLARATIONS.values()):
                    known.synchronize_bases()
                if methods:
                    definitions._register_methods(plan)
                documentation = documentation_atom(
                    plan.name, cls, kind="record",
                    parameters=tuple(field.name for field in plan.stored_fields),
                    annotations=plan.hints, parameter_descriptions=attribute_docstrings(cls),
                )
                if documentation is not None:
                    plan.space.add(documentation)
                plan.instrument()
                plan.answer(_expr(S["scope-defer"], Symbol(plan.name),
                                  _expr(S["drop-space"], Symbol(plan.space.name))))
            if consumer is not None:
                previous = consumer.dependencies.copy()
                operations._record_registry_undo(lambda: setattr(consumer, "dependencies", previous), description=f"class dependency {consumer.name} on {plan.name}")
                consumer.dependencies.add(cls)
                consumer.synchronize_bases()
            else:
                operations._record_registry_undo(lambda: plan.borrowers.discard(space.name), description=f"class borrower {plan.name} in {space.name}")
                plan.borrowers.add(space.name)
                space.add(_expr(S["from"], Symbol(plan.space.name)))
            return cls

        return space.transaction(publish)


def release(space: Any) -> None:
    """Retire declarations unreachable from declaring homes or native Scope ownership."""
    plans = set(_DECLARATIONS.values())
    dependents: dict[ClassDeclaration, set[ClassDeclaration]] = {plan: set() for plan in plans}
    for plan in plans:
        plan.borrowers.discard(space._name)
        for provider in (*plan.bases, *plan.references):
            dependents[provider].add(plan)
    # Explicit space release, including Scope cleanup, invalidates dependent
    # class programs even while their importing spaces are still being closed.
    pending = {plan for plan in plans if plan.space._name == space._name}
    invalid = set()
    while pending:
        plan = pending.pop()
        invalid.add(plan)
        pending.update(dependents[plan] - invalid)
    # Registry dependencies form a graph, including cycles through field types.
    # https://github.com/sqlalchemy/sqlalchemy/blob/a303102a7bfbbb6da992a89b6610d71f080fb5eb/lib/sqlalchemy/orm/decl_api.py#L1361-L1378
    pending = {
        plan for plan in plans - invalid
        if plan.borrowers or (not plan.space.dropped and plan.space._scoped)
    }
    retained = set()
    while pending:
        plan = pending.pop()
        retained.add(plan)
        pending.update({*plan.bases, *plan.references} - retained)
    retired = plans - retained
    for plan in retired:
        for rows in plan.inherited_rows.values():
            _withdraw_rows(plan.space._rt, [row for row in rows if row[0] != space._name])
    for plan in retired:
        plan.release_operations()
        plan.restore()
        lazy('metta.integrate').unregister_type(plan.cls)
        if plan.previous_registration is not None:
            _record_registration(plan.cls, plan.previous_registration)
    for plan in retired:
        if plan.space._name != space._name:
            plan.space.drop()
