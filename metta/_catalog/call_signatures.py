"""Purpose: carry Python call contracts as inspectable native parameter records.

Guarantees:
  - each native port retains its labels and answer cardinality, while
    repeated variadic labels remain positional [tested:
    test_expanded_operations_use_each_registered_arity;
    test_expanded_stacked_clauses_keep_positional_dispatch; commit=WORKTREE]
  - parameter order, kinds and defaults rebuild one inspect.Signature from
    the current native record [tested:
    test_native_call_contracts_preserve_python_argument_binding; commit=7109d9bb91bfc41aa18bf5f766f20904a9598fcc]
  - named annotation references and generic applications are data; unnamed
    host annotation objects retain their identity through Grounded [source:
    extensions/python/metta/_catalog/call_signatures.py:annotation; commit=7109d9bb91bfc41aa18bf5f766f20904a9598fcc]
"""

from __future__ import annotations

import builtins
import inspect
import sys
import types
import typing
from collections.abc import Callable
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, S, Symbol, Variable, _expr
from metta._atoms.registry import _lookup, constructor_for

_ABSENT = object()


def _named(value: Any) -> tuple[Atom | None, Any]:
    """Read a qualified annotation reference without invoking descriptors."""
    module, name = getattr(value, "__module__", None), getattr(value, "__qualname__", getattr(value, "__name__", None))
    held = sys.modules.get(module, _ABSENT) if isinstance(module, str) else _ABSENT
    if isinstance(module, str) and isinstance(name, str):
        for part in name.split("."):
            held = inspect.getattr_static(held, part, _ABSENT)
        if held is value:
            return _expr(S["host-type"], Symbol(module), Symbol(name)), held
    # Python publishes intrinsic singleton and type aliases in these modules,
    # including None and NoneType, whose own metadata supplies no usable path.
    for namespace in (builtins, types):
        for key, item in vars(namespace).items():
            if item is value:
                return _expr(S["host-type"], Symbol(namespace.__name__), Symbol(key)), item
    return None, held


def annotation(value: Any) -> Atom:
    """Project an annotation's exact Python species, independent of its arrow."""
    if value is inspect.Signature.empty:
        return _expr(S.absent)
    if value is Ellipsis:
        return S["..."]
    if isinstance(value, Atom):
        return _expr(S["native-type"], value)
    if isinstance(value, list):
        return _expr(S["annotation-list"], *(annotation(item) for item in value))
    if isinstance(value, type) and (registered := _lookup(value)) is not None:
        return _expr(S["record-type"], Symbol(registered.type_name))
    reference, named = _named(value)
    if reference is not None:
        return reference
    origin = typing.get_origin(value)
    if origin is not None:
        arguments = typing.get_args(value)
        if origin is typing.Literal:
            return _expr(S["host-literal"], Expression([annotation(item) for item in arguments]))
        if origin is typing.Annotated:
            return _expr(S.Annotated, annotation(arguments[0]), *(Grounded(item) for item in arguments[1:]))
        if origin in (typing.Union, types.UnionType):
            return _expr(S["host-union"], Expression([annotation(item) for item in arguments]))
        constructor = named if typing.get_origin(named) is origin else origin
        return _expr(S["host-apply"], annotation(constructor), Expression([annotation(item) for item in arguments]))
    return Grounded(value)


def annotation_value(atom: Atom) -> Any:
    """Rebuild the annotation described by a native call contract."""
    if isinstance(atom, Grounded):
        return atom.value
    if atom == S["..."]:
        return Ellipsis
    if not isinstance(atom, Expression):
        msg = f"a call annotation needs a native annotation record, got {atom}"
        raise TypeError(msg)
    head, arguments = atom.head, atom.args
    if head == S.absent and not arguments:
        return inspect.Signature.empty
    if head == S["native-type"] and len(arguments) == 1:
        return arguments[0]
    if head == S["annotation-list"]:
        return [annotation_value(item) for item in arguments]
    if head == S["record-type"] and len(arguments) == 1 and isinstance(arguments[0], Symbol):
        registered = constructor_for(arguments[0].name)
        if registered is not None:
            return registered[0]
    if head == S["host-type"] and len(arguments) == 2:
        module, name = arguments
        if isinstance(module, Symbol) and isinstance(name, Symbol):
            value = sys.modules.get(module.name, _ABSENT)
            for part in name.name.split("."):
                value = inspect.getattr_static(value, part, _ABSENT)
            if value is not _ABSENT:
                return value
    if head in (S["host-literal"], S["host-union"]) and len(arguments) == 1 and isinstance(arguments[0], Expression):
        values = tuple(annotation_value(item) for item in arguments[0].children)
        return typing.Literal[values] if head == S["host-literal"] else typing.Union[values]  # noqa: UP007 -- construct an arbitrary number of reflected alternatives
    if head == S.Annotated and len(arguments) >= 2:
        return typing.Annotated[tuple(annotation_value(item) for item in arguments)]
    if head == S["host-apply"] and len(arguments) == 2 and isinstance(arguments[1], Expression):
        origin = annotation_value(arguments[0])
        parameters = tuple(annotation_value(item) for item in arguments[1].children)
        return origin[parameters]
    msg = f"the native call annotation cannot be resolved: {atom}"
    raise TypeError(msg)


def project(signature: inspect.Signature, encode: Callable[[Any], Atom]) -> Atom:
    """Record each parameter's name, kind, annotation and optional default."""
    parameters = [
        _expr(S.parameter, Grounded(parameter.name), Symbol(parameter.kind.name), annotation(parameter.annotation),
              Expression([]) if parameter.default is inspect.Parameter.empty else _expr(S.default, encode(parameter.default)))
        for parameter in signature.parameters.values()
    ]
    return _expr(S.signature, Expression(parameters), annotation(signature.return_annotation))


def native(name: str, parameters: tuple[str | None, ...], *, home: Atom | None = None, stream: bool = False) -> Expression:
    """Describe the labels of one positional native call, without host defaults."""
    named = None not in parameters and len(set(parameters)) == len(parameters)
    labels = tuple(parameter if named and parameter is not None else f"x{index + 1}" for index, parameter in enumerate(parameters))
    variables = tuple(Variable(parameter) for parameter in labels)
    body = _expr(Symbol(name), *variables)
    if home is not None:
        body = _expr(S.evalc, body, home)
    image = _expr(S["|->"], Expression(variables), body)
    signature = inspect.Signature([
        inspect.Parameter(parameter, inspect.Parameter.POSITIONAL_OR_KEYWORD if named else inspect.Parameter.POSITIONAL_ONLY)
        for parameter in labels
    ])
    return _expr(S["@python-callable"], image, project(signature, Grounded), S.stream if stream else S.one)


def build(atom: Atom) -> inspect.Signature:
    """Validate and bind from the current parameter records, without a cache."""
    if not isinstance(atom, Expression) or atom.head != S.signature or len(atom.args) != 2 or not isinstance(atom.args[0], Expression):
        msg = "a callable contract needs (signature (parameter ...) return-annotation)"
        raise TypeError(msg)
    parameters = []
    for row in atom.args[0].children:
        if not isinstance(row, Expression) or row.head != S.parameter or len(row.args) != 4:
            msg = "a signature parameter needs a name, kind, annotation and optional default"
            raise TypeError(msg)
        name, kind, type_, default = row.args
        if not isinstance(name, Grounded) or not isinstance(name.value, str) or not isinstance(kind, Symbol) or not isinstance(default, Expression):
            msg = "a signature parameter needs a string name, a parameter-kind symbol and a default expression"
            raise TypeError(msg)
        parameter_kind = inspect.getattr_static(inspect.Parameter, kind.name, None)
        if not isinstance(parameter_kind, type(inspect.Parameter.POSITIONAL_ONLY)):
            msg = f"unknown Python parameter kind {kind}"
            raise TypeError(msg)
        value: Any = inspect.Parameter.empty
        if default.children:
            if default.head != S.default or len(default.args) != 1:
                msg = "a signature default is () or (default value)"
                raise TypeError(msg)
            value = default.args[0]
            if isinstance(value, Grounded):
                value = value.value
        parameters.append(inspect.Parameter(name.value, parameter_kind, default=value, annotation=annotation_value(type_)))
    return inspect.Signature(parameters, return_annotation=annotation_value(atom.args[1]))
