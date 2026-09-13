"""Purpose: link Python call-argument binding into native compiled programs.

Guarantees:
  - signature binding constructs a native application and never runs its body
    [tested: test_expanded_native_calls_read_the_live_contract; commit=WORKTREE]
Owns resources:
  - consuming spaces own their ordinary operation registrations; keyword
    dictionaries are temporary values local to one call
    [tested: test_expanded_operation_contracts_follow_replacement_and_retirement;
    commit=WORKTREE]
"""

from __future__ import annotations

import ctypes
from typing import Any

from metta._atoms.factories import Atom, Expression, Grounded, Handle, S, Symbol, _expr
from metta._catalog import call_values
from metta._declare import operations

# Use the host's DICT_MERGE implementation. A Python loop adds key hashing
# and changes dict-subclass and keys-iterator effects; copying every prefix
# with ** would cost quadratic work and reject non-string keys too early.
# https://github.com/python/cpython/blob/v3.14.4/Objects/dictobject.c#L3722-L3836
_merge = ctypes.pythonapi._PyDict_MergeEx
_merge.argtypes = (ctypes.py_object, ctypes.py_object, ctypes.c_int)
_merge.restype = ctypes.c_int


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
        packet = _expr(S.Kwargs, *(Expression([Symbol(name), value]) for name, value in named.items()))
        application = _expr(function, *positional.children, *((packet,) if named else ()))
        stream = False
    else:
        native = call_values.rebuild(function, Any, call_values.lexical_space(home), arity=len(positional.children) + len(named))
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
        ("_python-merge-keywords", merge_keywords, 2),
        ("_python-bind-call", bind_call, 5),
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
