"""Purpose: bind value prefixes through live canonical native applications.

Owns resources: each test retires its MeTTa context and native declaration rows.
"""

import inspect
from collections.abc import Callable

import pytest

from metta import Atom, Expression, G, MeTTa, S, V, convert
from metta._catalog import call_signatures


def _bound_application(home, signature, captured):
    canonical = S["|->"](Expression([V.items]), S.evalc(S.noeval(S.original(V.items)), home))
    bound = S["|->"](Expression([S[":seg"](V.supplied)]),
                       S.evalc(S.noeval(S.bound(V.supplied)), home))
    contract = S["@python-callable"](canonical, call_signatures.project(signature, G), S.one)
    home.add(contract)
    home.add(S["@python-binding"](bound, canonical, len(captured)))
    positional = V.positional
    for value in reversed(captured):
        positional = S["cons-atom"](S.noeval(value), positional)
    application = S["|->"](Expression([V.positional, V.keywords]),
                             S.let(V.complete, positional, S.noeval(S.received(V.complete, V.keywords))))
    home.add(S["@python-application"](bound, application))
    return convert.build(bound, Callable[..., Atom], space=home), canonical, contract


@pytest.mark.parametrize("captured", ((), (S.Receiver,), tuple(G(index) for index in range(13))))
def test_bound_application_prefixes_keep_variadic_collectors(captured):
    """Every captured value and later operand reaches one ordered call frame."""
    signature = inspect.Signature([
        inspect.Parameter("items", inspect.Parameter.VAR_POSITIONAL),
        inspect.Parameter("flag", inspect.Parameter.KEYWORD_ONLY, default=3),
        inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD),
    ])
    with MeTTa() as context:
        callback, _canonical, _contract = _bound_application(context.self, signature, captured)
        assert inspect.signature(callback) == signature
        data = S["+"](2, 3)
        assert callback(data, 8, flag=5) == S.received(Expression([*captured, data, 8]),
                                                    Expression([Expression(["flag", 5])]))


@pytest.mark.parametrize("parameters", ((),
    (inspect.Parameter("flag", inspect.Parameter.KEYWORD_ONLY, default=3),),
    (inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD),)))
def test_impossible_prefix_publication_keeps_inspect_and_call_refusals_distinct(parameters):
    """A callable publishes before either public observation refuses its prefix."""
    with MeTTa() as context:
        callback, _canonical, _contract = _bound_application(context.self, inspect.Signature(parameters), (S.Receiver,))
        with pytest.raises(ValueError, match="invalid method signature"):
            inspect.signature(callback)
        with pytest.raises(TypeError, match="too many positional arguments"):
            callback()


def test_bound_signatures_observe_canonical_replacement():
    """One existing callable changes domain when its native signature changes."""
    variadic = inspect.Signature([inspect.Parameter("items", inspect.Parameter.VAR_POSITIONAL)])
    fixed = inspect.Signature([inspect.Parameter("first", inspect.Parameter.POSITIONAL_ONLY)])
    with MeTTa() as context:
        home = context.self
        callback, canonical, contract = _bound_application(home, variadic, (S.Receiver,))
        assert inspect.signature(callback) == variadic
        home.remove(contract)
        replacement = S["@python-callable"](canonical, call_signatures.project(fixed, G), S.one)
        home.add(replacement)
        assert inspect.signature(callback) == inspect.Signature()
        with pytest.raises(TypeError, match="too many positional arguments"):
            callback(1)
        assert callback() == S.received(Expression([S.Receiver]), Expression([]))


def test_forwarded_value_prefixes_can_exceed_the_formal_slot_count():
    """A named variadic application can receive more captures than native slots."""
    with MeTTa() as context:
        home = context.self
        home.run("(= (prefix-target $items) (noeval (raw $items))) "
                 "(: prefix-frames (-> Expression Expression %Undefined%)) "
                 "(= (prefix-frames $positional $keywords) (noeval (received $positional $keywords)))")
        canonical = S["|->"](Expression([V.items]), S.evalc(S["prefix-target"](V.items), home))
        signature = inspect.Signature([inspect.Parameter("items", inspect.Parameter.VAR_POSITIONAL)])
        home.add(S["@python-callable"](canonical, call_signatures.project(signature, G), S.one))
        home.add(S["@python-application"](canonical, S["prefix-frames"]))
        captures = Expression([S.A, S.B, S.C])
        callback = convert.build(S.partial(S["prefix-target"], captures), Callable[..., Atom], space=home)
        assert inspect.signature(callback) == signature
        assert callback(9) == S.received(Expression([*captures.children, 9]), Expression([]))


def test_raw_native_captures_still_hold_formal_slots():
    """A raw partial captures its complete collector value as one formal slot."""
    with MeTTa() as context:
        home = context.self
        home.run("(= (prefix-raw $items $flag) (noeval (received $items $flag)))")
        canonical = S["|->"](Expression([V.items, V.flag]), S.evalc(S["prefix-raw"](V.items, V.flag), home))
        signature = inspect.Signature([
            inspect.Parameter("items", inspect.Parameter.VAR_POSITIONAL),
            inspect.Parameter("flag", inspect.Parameter.KEYWORD_ONLY, default=3),
        ])
        home.add(S["@python-callable"](canonical, call_signatures.project(signature, G), S.one))
        captures = Expression([S.A, S.B])
        callback = convert.build(S.partial(S["prefix-raw"], Expression([captures])), Callable[..., Atom], space=home)
        assert tuple(inspect.signature(callback).parameters) == ("flag",)
        assert callback(flag=9) == S.received(captures, 9)
