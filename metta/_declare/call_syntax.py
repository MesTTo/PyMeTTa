"""Purpose: link Python call-argument binding into native compiled programs.

Guarantees:
  - compiled parameter binding reads its home, image and frames as native
    data and returns source without evaluating the body [tested:
    test_native_parameter_binding_preserves_values_and_defers_the_body;
    test_native_parameter_binding_observes_graph_rewrites; commit=WORKTREE]
  - host applications retain editable native argument frames and the existing
    raw host codec [tested:
    test_compiled_host_calls_keep_data_out_of_keyword_control,
    test_reflected_host_application_frames_remain_editable,
    test_host_call_frames_do_not_inspect_callable_signatures; commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - method and constructor values keep positional data separate from keyword
    entries [tested:
    test_keyword_named_atoms_remain_positional_method_and_constructor_values;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - qualified class applications carry their class identity through native
    dispatch and scope retention [tested:
    test_kept_unbound_methods_retain_their_class_program; commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - positional expansion preserves native atoms in native and borrowed
    sequences [tested: test_expanded_arguments_preserve_native_atom_values;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - signature binding constructs a native application and never runs its body
    [tested: test_expanded_native_calls_read_the_live_contract; commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
  - named references defer port selection to their live native call contracts
    [source: extensions/python/metta/_catalog/call_values.py:NativeCallable._reference_layout;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
Owns resources:
  - consuming spaces own their ordinary operation registrations; keyword
    dictionaries are temporary values local to one call
    [tested: test_expanded_operation_contracts_follow_replacement_and_retirement;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
"""

from __future__ import annotations

import ctypes
import inspect
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, Handle, S, Symbol, Variable, _expr
from metta._binding import host
from metta._catalog import call_signatures, call_values
from metta._catalog.build import build
from metta._declare import operations

# Use the host's DICT_MERGE implementation. A Python loop adds key hashing
# and changes dict-subclass and keys-iterator effects; copying every prefix
# with ** would cost quadratic work and reject non-string keys too early.
# https://github.com/python/cpython/blob/v3.14.4/Objects/dictobject.c#L3722-L3836
_merge = ctypes.pythonapi._PyDict_MergeEx
_merge.argtypes = (ctypes.py_object, ctypes.py_object, ctypes.c_int)
_merge.restype = ctypes.c_int


def expand_positional(value: Atom, materializer: Atom) -> Atom:
    """Collect a call's positional values through the existing value codec."""
    collect = call_signatures.annotation_value(materializer)
    return Expression([call_values.argument(item) for item in collect(build(value))])


def merge_keywords(frame: Atom, value: Atom) -> Atom:
    """Read one mapping before the next source operand is evaluated."""
    if not isinstance(frame, Grounded) or not isinstance(frame.value, dict):
        msg = "keyword assembly requires its call-local dictionary"
        raise TypeError(msg)
    target = frame.value
    if isinstance(value, (Handle, Symbol)) or (isinstance(value, Expression) and call_values.is_parametric_space(value)):
        rows = call_values.lexical_space(value).atoms()
        entries = _native_entries(rows, pair=True)
    elif isinstance(value, Grounded):
        try:
            _merge(target, value.value, 2)
        except AttributeError as error:
            msg = "a ** argument must be a mapping"
            raise TypeError(msg) from error
        except KeyError as error:
            msg = f"got multiple values for keyword argument {error.args[0]!r}"
            raise TypeError(msg) from error
        return frame
    elif isinstance(value, Expression):
        entries = _native_entries(value.children, pair=False)
    else:
        msg = "a ** argument must be a mapping"
        raise TypeError(msg)
    for name, read in entries:
        if name in target:
            msg = f"got multiple values for keyword argument {name!r}"
            raise TypeError(msg)
        target[name] = read()
    return frame


def _native_entries(rows: Any, *, pair: bool) -> Any:
    for row in rows:
        if not isinstance(row, Expression):
            msg = "a native keyword mapping must contain key/value entries"
            raise TypeError(msg)
        parts = row.children if pair else row.args if row.head == S.entry else ()
        if len(parts) != 2:
            msg = "a native keyword mapping must contain key/value entries"
            raise TypeError(msg)
        key, value = parts
        yield key.value if isinstance(key, Grounded) else key, lambda value=value: value


def bind_call(home: Atom, function: Atom, positional: Atom, keywords: Atom, consumer: Atom) -> Atom:
    """Bind a carried callable and return the expression its consumer needs."""
    if not isinstance(positional, Expression) or not isinstance(keywords, Grounded) or not isinstance(keywords.value, dict):
        msg = "call binding requires evaluated positional and keyword arguments"
        raise TypeError(msg)
    if not isinstance(consumer, Grounded) or consumer.value not in ("value", "iterable"):
        msg = "call binding requires its value or iterable consumer"
        raise TypeError(msg)
    if any(not isinstance(name, str) for name in keywords.value):
        msg = "keywords must be strings"
        raise TypeError(msg)
    named = {name: call_values.argument(value) for name, value in keywords.value.items()}
    application: Atom
    if isinstance(function, Grounded):
        pairs = Expression([Expression([Grounded(name), value]) for name, value in named.items()])
        mapping = _expr(S["py-dict"], _expr(S.noeval, pairs)) if named else keywords
        # host.apply already consumes separate frames. Expanding a positional
        # term into the grounded-call syntax would reinterpret a last Kwargs
        # value as control; its fields could also be evaluated a second time.
        application = call_values.apply_sources(Grounded(host.apply), (
            _expr(S.noeval, function), _expr(S.noeval, positional), mapping,
        ))
        stream = False
    else:
        native = call_values.rebuild(function, Any, call_values.lexical_space(home))
        if native is None:
            msg = "the value has no native callable image"
            raise TypeError(msg)
        application, _signature, stream = native.application(positional.children, named)
        application = _expr(S.evalc, application, native.space)
    if consumer.value == "iterable":
        application = _expr(S.collapse, application if stream else _expr(S["py-iter-once"], application))
    return application


def link(space: Any, required: Any) -> None:
    """Link only the shared argument operations requested by compiled source."""
    for name, function, arity in (
        ("_python-expand-positional", expand_positional, 2),
        ("_python-merge-keywords", merge_keywords, 2),
        ("_python-bind-call", bind_call, 5),
        ("_python-bind-parameters", bind_parameters, 4),
    ):
        if name not in required:
            continue
        existing = operations.REGISTRY.get(name)
        if existing is not None and existing.fn is not function:
            msg = f"the call-argument operation {name} already has another provider"
            raise TypeError(msg)
        space.op(function, name=name, arities=[arity], effect="oracleIO",
                 declarations=[_expr(S.arguments, Symbol(name), S.atoms)])
        space.add(_expr(S.internal, Symbol(name)))


def bind_arguments(signature: inspect.Signature, positional: Atom, keywords: Atom) -> inspect.BoundArguments:
    """Bind independent positional values and keyword entries."""
    if not isinstance(positional, Expression) or not isinstance(keywords, Expression):
        msg = "call arguments need a positional expression and a keyword-pair expression"
        raise TypeError(msg)
    named: dict[str, Atom] = {}
    arguments = positional.children
    for pair in keywords.children:
        if not isinstance(pair, Expression) or len(pair.children) != 2:
            msg = "keyword arguments need name/value pairs"
            raise TypeError(msg)
        key, value = pair.children
        if not isinstance(key, Grounded) or not isinstance(key.value, str):
            msg = "keyword names must be strings"
            raise TypeError(msg)
        if key.value in named:
            msg = f"got multiple values for keyword argument {key.value!r}"
            raise TypeError(msg)
        named[key.value] = value
    return signature.bind(*arguments, **named)


def bind_parameters(home: Atom, image: Atom, positional: Atom, keywords: Atom) -> Atom:
    """Bind compiled slots from a native image and its current parameter record."""
    signature = call_values.NativeCallable(image, call_values.lexical_space(home), Any).__signature__
    supplied = bind_arguments(signature, positional, keywords)
    defaults = {
        name: _expr(S.noeval, call_values.argument(parameter.default))
        for name, parameter in signature.parameters.items()
        if parameter.default is not inspect.Parameter.empty
    }
    sources = call_values.argument_sources(signature, supplied.arguments, call_values.argument, home, defaults)
    return call_values.apply_sources(image, sources)


def publish_binding(owner: Any, name: str, bind: Any, inputs: tuple[Atom, ...]) -> None:
    """Publish an owned binding operation and its native evaluation equation."""
    binder = Symbol(f"_{name}:bind")
    owner.operation(bind, name=binder.name, arities=[len(inputs)], effect="readOnlyLookup",
                    declarations=[_expr(S.arguments, binder, S.atoms)])
    owner.space.add(_expr(S.internal, binder))
    parameters = tuple(Variable(f"call-input-{index}") for index in range(len(inputs)))
    call = Variable("bound-call")
    owner.space.add(_expr(S["="], _expr(Symbol(name), *parameters),
                          _expr(S.chain, _expr(binder, *parameters), call,
                                _expr(S.evalc, call, owner.space))))
    owner.space.add(_expr(S[":"], Symbol(name), _expr(S["->"], *inputs, S["%Undefined%"])))


def member_application(owner: Any, member: Atom, positional: Atom, keywords: Atom) -> Atom:
    """Apply a class member through its native qualified selector and call frames."""
    return call_values.apply_sources(S["_class-apply"], (
        _expr(S.noeval, Symbol(owner.name)), _expr(S.noeval, member), positional, keywords,
    ))


def publish_member(owner: Any, member: Atom, target: Symbol) -> None:
    """Publish the class/member relation used by a carried constructor or method."""
    positional, keywords = Variable("class-positionals"), Variable("class-keywords")
    owner.space.add(_expr(S["="],
                          _expr(S["_class-apply"], Symbol(owner.name), member, positional, keywords),
                          _expr(target, positional, keywords)))
    owner.space.add(_expr(S.internal, S["_class-apply"]))
