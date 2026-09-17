"""Purpose: link Python call-argument binding into native compiled programs.

Guarantees:
  - native consumer validation derives from CallConsumer and retains its
    existing wire values [tested:
    test_call_consumer_source.CallConsumerSourceTests; commit=b8f5c6b9a3ef41b173d6af81e1b9bb526977a908]
  - _python-call-value observes one held immediate result: the binder wraps
    a one-answer native application in eval-one and leaves a stream bare;
    exceptions and cardinality failures propagate, while returned Error data
    stays a value [tested: test_call_value_holds_native_results,
    test_call_value_refuses_zero_and_multiple_answers,
    test_expanded_operations_use_each_registered_arity; commit=e01a1a46a1bcbce16862c3a2cd4175bb9127fd13].
  - host value calls preserve their exact result without inspecting a
    signature or consuming an iterator [tested:
    test_call_value_does_not_start_or_replace_deferred_host_results;
    commit=d78d867637047c164be4bc1ab63c40b46d2cff5d].
  - canonical keyword terms become one fresh dictionary per body activation
    [tested: test_compiled_collectors_match_native_equation_heads;
    test_compiled_generator_answers_share_one_keyword_dictionary; commit=1796cf0f581aa767db9289b807f66238cb747065]
  - Atom results retain held syntax after entry work executes [tested:
    test_compiled_collector_entry_preserves_held_result_syntax; commit=1796cf0f581aa767db9289b807f66238cb747065]
  - compiled parameter binding reads its home, image and frames as native
    data and returns source without evaluating the body [tested:
    test_native_parameter_binding_preserves_values_and_defers_the_body;
    test_native_parameter_binding_observes_graph_rewrites; commit=1796cf0f581aa767db9289b807f66238cb747065]
  - compiled value calls cross the seam with their keyword frame as pairs and
    hand the callee the twin's Python values, pythonic in and returned out,
    the codec py-operator shares; the iterable route keeps its
    editable frames and the raw host floor [tested:
    test_compiled_host_calls_keep_data_out_of_keyword_control,
    test_reflected_host_application_frames_remain_editable,
    test_host_call_frames_do_not_inspect_callable_signatures; commit=e01a1a46a1bcbce16862c3a2cd4175bb9127fd13]
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
  - the binder operation's existing catalog owns the shared native value
    equation; local type holdings follow operation replacement and withdrawal
    [source: extensions/python/metta/_declare/operations.py:_register_transaction,
    _holdings and _retire_previous; commit=d78d867637047c164be4bc1ab63c40b46d2cff5d].
  - consuming spaces own their ordinary operation registrations; keyword
    dictionaries are temporary values local to one call
    [tested: test_expanded_operation_contracts_follow_replacement_and_retirement;
    commit=bb0a3a3a43e5b9cd015c900df8a861f16a3af0ce]
"""

from __future__ import annotations

import ctypes
import inspect
from typing import Any, get_args

from metta._atoms.factories import (
    Atom,
    Expression,
    Grounded,
    Handle,
    S,
    Symbol,
    Variable,
    _expr,
    fresh,
)
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
    # A PEP 695 type alias carries its Literal in __value__, which pylint does not model.
    if not isinstance(consumer, Grounded) or consumer.value not in get_args(call_values.CallConsumer.__value__):  # pylint: disable=no-member
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
        application, stream = _native_application(home, function, positional.children, named)
    if consumer.value == "iterable":
        application = _expr(S.collapse, application if stream else _expr(S["py-iter-once"], application))
    return application


def _native_application(home: Atom, function: Atom, positional: tuple[Atom, ...],
                        named: dict[str, Atom]) -> tuple[Atom, bool]:
    native = call_values.rebuild(function, Any, call_values.lexical_space(home))
    if native is None:
        msg = "the value has no native callable image"
        raise TypeError(msg)
    application, _signature, stream = native.application(positional, named)
    return _expr(S.evalc, application, native.space), stream


def bind_value(home: Atom, function: Atom, positional: Atom, keywords: Atom) -> Atom:
    """Construct the immediate-value application without executing its body."""
    arguments, named = _argument_values(positional, keywords)
    if isinstance(function, Grounded):
        return call_values.apply_sources(S["_python-apply-host-value"], tuple(
            _expr(S.noeval, value) for value in (home, function, positional, keywords)
        ))
    application, stream = _native_application(home, function, arguments, named)
    # An explicit stream stays a stream under the value consumer, the
    # CallConsumer contract; every other native application is one value,
    # observed to exactly one answer where it evaluates.
    return application if stream else _expr(S["eval-one"], application)


def apply_host_value(_home: Atom, function: Atom, positional: Atom, keywords: Atom) -> Atom:
    """Call the exact host object once with values and retain its result image."""
    arguments, named = _argument_values(positional, keywords)
    if not isinstance(function, Grounded):
        msg = "a host value application requires a grounded callable"
        raise TypeError(msg)
    # The callable is the held object itself: build() reads a held object as
    # a value to rebuild, and a host island answered "no door namespace". Its
    # operands are the Python values the twin computes with, the codec every
    # prelude operator applies, so an island's `value * 2` over a compiled
    # local multiplies numbers rather than building `(* 1 2)`.
    target = host.unboxed(function.value)
    value = target(*(call_values.pythonic(argument) for argument in arguments),
                   **{name: call_values.pythonic(argument) for name, argument in named.items()})
    return call_values.returned(value)


def value_declarations() -> tuple[Expression, ...]:
    """Derive the held native value equation owned by its binder operation."""
    home, function, positional, keywords = (Variable(name) for name in (
        "call-home", "call-function", "call-positionals", "call-keywords",
    ))
    source = Variable("call-source")
    head = _expr(S["_python-call-value"], home, function, positional, keywords)
    binding = _expr(S["_python-bind-call-value"], home, function, positional, keywords)
    # The binder decides how many answers the source may have: a one-answer
    # native application arrives wrapped in eval-one, a stream and a host
    # application arrive bare, so the equation only evaluates the bound
    # source in the callable's home. No function frame around it: this
    # engine's eval and evalc are full evaluations and step only inside a
    # function frame, where chain observes the step, so a frame handed back
    # the callable's body after one step and a zero-answer body never reached
    # the cardinality check. Outside a frame eval-one observes the whole
    # answer set, and a body's noeval mask is what keeps returned syntax from
    # being reduced at the boundary.
    # [source: engine/metta/control.pl:metta_evalc_step/3;
    # engine/translator/special_forms.pl:translate_special_dl(noeval,...);
    # tested: test_call_value_holds_native_results,
    # test_call_value_refuses_zero_and_multiple_answers,
    # test_expanded_operations_use_each_registered_arity; commit=e01a1a46a1bcbce16862c3a2cd4175bb9127fd13]
    body = _expr(S.let, source, binding, _expr(S.evalc, source, home))
    # Four Atom operands, since the callable image and its operand frames
    # must reach the binder unevaluated, and an undefined result, since an
    # Atom result type hands the right-hand side back as written.
    return (
        _expr(S[":"], head.head, _expr(S["->"], *(S.Atom for _ in head.args), S["%Undefined%"])),
        _expr(S["="], head, body),
        _expr(S.internal, head.head),
    )


def link(space: Any, required: Any) -> None:
    """Link only the shared argument operations requested by compiled source."""
    required = set(required)
    if "_python-call-value" in required:
        required.update(("_python-bind-call-value", "_python-apply-host-value"))
    for name, function, arity in (
        ("_python-expand-positional", expand_positional, 2),
        ("_python-merge-keywords", merge_keywords, 2),
        ("_python-bind-call", bind_call, 5),
        ("_python-bind-parameters", bind_parameters, 4),
        ("_python-apply-host-value", apply_host_value, 4),
        ("_python-bind-call-value", bind_value, 4),
    ):
        if name not in required:
            continue
        existing = operations.REGISTRY.get(name)
        if existing is not None and existing.fn is not function:
            msg = f"the call-argument operation {name} already has another provider"
            raise TypeError(msg)
        declarations = [_expr(S.arguments, Symbol(name), S.atoms)]
        if function is bind_value:
            declarations.extend(value_declarations())
        space.op(function, name=name, arities=[arity], effect="oracleIO", declarations=declarations)
        space.add(_expr(S.internal, Symbol(name)))


def bind_arguments(signature: inspect.Signature, positional: Atom, keywords: Atom) -> inspect.BoundArguments:
    """Bind independent positional values and keyword entries."""
    arguments, named = _argument_values(positional, keywords)
    return signature.bind(*arguments, **named)


def _argument_values(positional: Atom, keywords: Atom) -> tuple[tuple[Atom, ...], dict[str, Atom]]:
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
            msg = "keywords must be strings"
            raise TypeError(msg)
        if key.value in named:
            msg = f"got multiple values for keyword argument {key.value!r}"
            raise TypeError(msg)
        named[key.value] = value
    return arguments, named


def bind_parameters(home: Atom, image: Atom, positional: Atom, keywords: Atom) -> Atom:
    """Bind compiled slots from a native image and its current parameter record."""
    signature = call_values.NativeCallable(image, call_values.lexical_space(home), Any).__signature__
    supplied = bind_arguments(signature, positional, keywords)
    defaults = {
        name: _expr(S.noeval, call_values.argument(parameter.default))
        for name, parameter in signature.parameters.items()
        if parameter.default is not inspect.Parameter.empty
    }
    sources = call_values.argument_sources(signature, supplied.arguments, call_values.argument, defaults)
    return call_values.apply_sources(image, sources)


def parameter_scope(signature: inspect.Signature, scope: dict[str, str]) -> dict[Variable, Atom]:
    """Separate incoming keyword terms from their mutable body-local values."""
    bindings: dict[Variable, Atom] = {}
    for name, parameter in signature.parameters.items():
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            incoming = Variable(scope[name])
            entries = fresh()
            local = fresh()
            scope[name] = local.name
            bindings[entries] = _expr(S.noeval, incoming)
            bindings[local] = _expr(S["dict-space"], entries)
    return bindings


def parameter_body(body: Atom, bindings: dict[Variable, Atom], result_types: tuple[Atom, ...] = ()) -> Atom:
    """Materialize parameters before the activation's shared computation."""
    if not bindings:
        return body
    held = S.Atom in result_types
    if held:
        # The native function frame executes entry work while return retains
        # the ordinary Atom-result quotation. Preserve an existing frame.
        # [source: engine/translator/analysis.pl:translate_equation_body_result/4;
        # commit=1796cf0f581aa767db9289b807f66238cb747065]
        body = (body.args[0] if isinstance(body, Expression) and body.head == S.function and len(body.args) == 1
                else _expr(S["return"], body))
    for variable, source in reversed(tuple(bindings.items())):
        body = _expr(S.let, variable, source, body)
    return _expr(S.function, body) if held else body


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
