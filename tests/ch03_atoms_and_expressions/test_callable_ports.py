"""Purpose: select named native call ports from their current Python contracts.

Guarantees:
  - named references bind complete signatures independently of their native
    parameter count [tested: test_named_callable_uses_its_complete_signature;
    commit=WORKTREE]
  - native contract edits govern retained references, including ambiguity
    between overlapping variadic ports [tested:
    test_named_callable_observes_signature_replacement;
    test_overlapping_variadic_ports_require_an_explicit_native_image;
    commit=WORKTREE]
"""

import inspect
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Expression, G, MeTTa, S, V, convert
from metta._catalog import call_signatures


def _port(home, name, signature):
    variables = tuple(V[f"port-{index}"] for index, _ in enumerate(signature.parameters))
    call = S[name](*variables)
    image = S["|->"](Expression(variables), S.evalc(call, home))
    contract = S["@python-callable"](image, call_signatures.project(signature, G), S.one)
    home.add(S["="](call, S.noeval(S.received(*variables))), contract)
    return image, contract


def _signature(value, /, offset=2, *extra, scale=3, **options):
    return value, offset, extra, scale, options


@pytest.mark.parametrize(("arguments", "keywords"), [
    ((1,), {}),
    ((1, 4), {}),
    ((1, 4, 5, 6), {"scale": 7, "bonus": 8}),
    ((1,), {"value": 9, "offset": 4, "scale": 7}),
    ((1, 2, 3, 4, 5, 6, 7, 8), {"left": 9, "right": 10}),
])
def test_named_callable_uses_its_complete_signature(arguments, keywords):
    """Canonical slots collect both variadics even when call counts differ."""
    with MeTTa() as context:
        home = context.self
        signature = inspect.signature(_signature)
        _port(home, "complete-port", signature)
        callback = convert.build(S["complete-port"], Callable[..., Any], space=home)
        assert inspect.signature(callback) == signature
        actual = callback(*arguments, **keywords)
        assert tuple(part.value for part in actual.args) == _signature(*arguments, **keywords)


@given(st.lists(st.integers(), max_size=8), st.dictionaries(
    st.sampled_from(("value", "offset", "scale", "bonus")), st.integers(),
))
def test_named_callable_binding_agrees_with_python(arguments, keywords):
    """Selection preserves Python's successes and exact binding failures."""
    signature = inspect.signature(_signature)
    with MeTTa() as context:
        home = context.self
        _port(home, "property-port", signature)
        callback = convert.build(S["property-port"], Callable[..., Any], space=home)
        try:
            signature.bind(*arguments, **keywords)
        except TypeError as expected:
            with pytest.raises(TypeError) as actual:
                callback(*arguments, **keywords)
            assert str(actual.value) == str(expected)
        else:
            assert tuple(part.value for part in callback(*arguments, **keywords).args) == _signature(*arguments, **keywords)


def test_named_callable_observes_signature_replacement():
    """A retained named reference uses a rewritten default on its next call."""
    with MeTTa() as context:
        home = context.self
        signature = inspect.signature(_signature)
        image, contract = _port(home, "edited-port", signature)
        callback = convert.build(S["edited-port"], Callable[..., Any], space=home)
        assert callback(1).args[1] == 2
        parameters = tuple(signature.parameters.values())
        changed = signature.replace(parameters=[
            parameters[0], parameters[1].replace(default=13), *parameters[2:],
        ])
        home.remove(contract)
        home.add(S["@python-callable"](image, call_signatures.project(changed, G), S.one))
        assert callback(1).args[1] == 13


def test_overlapping_variadic_ports_require_an_explicit_native_image():
    """An arbitrary argument count cannot choose between two valid layouts."""
    with MeTTa() as context:
        home = context.self
        wide, _ = _port(home, "overlapping-ports", inspect.signature(_signature))
        narrow_signature = inspect.Signature([
            inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("extra", inspect.Parameter.VAR_POSITIONAL),
        ])
        _port(home, "overlapping-ports", narrow_signature)
        callback = convert.build(S["overlapping-ports"], Callable[..., Any], space=home)
        with pytest.raises(TypeError, match="more than one native call port"):
            callback(1, 2, 3)
        explicit = convert.build(wide, Callable[..., Any], space=home)
        assert tuple(part.value for part in explicit(1).args) == _signature(1)


def test_an_exact_positional_port_precedes_variadic_ports():
    """Native fixed-arity dispatch remains the more specific call contract."""
    with MeTTa() as context:
        home = context.self
        _port(home, "specific-port", inspect.signature(_signature))
        _port(home, "specific-port", inspect.Signature([
            inspect.Parameter("only", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ]))
        callback = convert.build(S["specific-port"], Callable[..., Any], space=home)
        assert callback(11) == S.received(11)
        assert tuple(part.value for part in callback(11, 12).args) == _signature(11, 12)


@pytest.mark.parametrize("converted", (False, True))
def test_compiled_calls_select_complete_native_ports(converted):
    """Compiled call frames use the same contracts as direct Python calls."""
    with MeTTa() as context:
        home = context.self
        _port(home, "compiled-complete-port", inspect.signature(_signature))
        target = S["compiled-complete-port"]
        if converted:
            target = convert.build(target, Callable[..., Any], space=home)

        @home.define
        def apply_complete_port(callback: Callable[..., Any]):
            return callback(1, 2, 3, scale=4, bonus=5)

        result = apply_complete_port(target).one()
        assert tuple(part.value for part in result.args) == _signature(1, 2, 3, scale=4, bonus=5)


def test_captured_complete_ports_preserve_positional_only_keyword_names():
    """Captured positional-only slots leave equal keyword labels available."""
    with MeTTa() as context:
        home = context.self
        _port(home, "captured-complete-port", inspect.signature(_signature))
        value = S.partial(S["captured-complete-port"], Expression([1]))
        callback = convert.build(value, Callable[..., Any], space=home)
        actual = callback(value=9, scale=7)
        assert tuple(part.value for part in actual.args) == _signature(1, value=9, scale=7)


def test_declared_port_families_reject_unaccepted_argument_frames():
    """Known contracts reject an invalid call before native evaluation."""
    with MeTTa() as context:
        home = context.self
        _port(home, "required-ports", inspect.signature(_signature))
        _port(home, "required-ports", inspect.Signature([
            inspect.Parameter("first", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("second", inspect.Parameter.POSITIONAL_ONLY),
        ]))
        callback = convert.build(S["required-ports"], Callable[..., Any], space=home)
        with pytest.raises(TypeError, match="no declared native call port accepts"):
            callback()


@pytest.mark.parametrize("signature", [
    inspect.signature(_signature),
    inspect.Signature([
        inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY),
        inspect.Parameter("scale", inspect.Parameter.POSITIONAL_OR_KEYWORD),
    ]),
])
def test_named_and_exact_contracts_preserve_keyword_key_effects(signature):
    """Selecting an unambiguous port does not run argument binding twice."""
    events = []

    class Keyword(str):
        def __hash__(self):
            events.append("hash")
            return str.__hash__(self)

        def __eq__(self, other):
            events.append("equal")
            return str.__eq__(self, other)

    keywords = {Keyword("scale"): 4}
    with MeTTa() as context:
        home = context.self
        image, _ = _port(home, "keyword-effects-port", signature)
        observations = []
        for value in (image, S["keyword-effects-port"]):
            callback = convert.build(value, Callable[..., Any], space=home)
            events.clear()
            result = callback(1, **keywords)
            observations.append((tuple(part.value for part in result.args), events.copy()))
        assert observations[0] == observations[1]
