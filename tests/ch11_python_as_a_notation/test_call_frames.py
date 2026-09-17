"""Purpose: keep compiled call values separate from native keyword syntax.

Guarantees:
  - positional and keyword values retain their place without another
    evaluation, including native expressions headed by Kwargs [tested:
    test_compiled_host_calls_keep_data_out_of_keyword_control;
    test_carried_native_calls_hold_completed_operand_values; commit=86756da11eade288973b0dfaab7486a29e598cfd]
  - reflected host applications read their current native argument frames
    [tested: test_reflected_host_application_frames_remain_editable;
    commit=86756da11eade288973b0dfaab7486a29e598cfd]
  - borrowed values remain identical through positional and keyword calls,
    including argument expansion [tested:
    test_host_call_frames_preserve_borrowed_value_identity; commit=fb170a48db042c9a002e06f6cb47389af7fd66fc]
"""

from collections.abc import Callable
from functools import partial
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Atom, Expression, G, MeTTa, S, py
from metta._catalog.call_values import pythonic


def _received(*args, **kwargs):
    return repr((args, kwargs))


def _direct(function: Callable[..., Any], value: Atom):
    return function(value)


def _expanded(function: Callable[..., Any], value: Atom):
    return function(*[value])


def _keyword(function: Callable[..., Any], value: Atom):
    return function(payload=value)


def _mixed(function: Callable[..., Any], value: Atom):
    return function(value, *[value], payload=value)


def _implicit(value: Atom):
    return _received(value)


def _explicit(value: Atom):
    return py(_received(value))


def _native_single(payload: Atom):
    return S.observed(payload)


def _native_triple(left: Atom, right: Atom, payload: Atom):
    return S.observed(left, right, payload)


@pytest.mark.parametrize("payload", [
    S.Kwargs(S.entry(3)),
    S.Kwargs(),
    S.Kwargs(S.malformed),
    S.Kwargs,
    S["+"](1, 2),
    G((1, S.Kwargs())),
])
@pytest.mark.parametrize("source", [_direct, _expanded, _keyword, _mixed, _implicit, _explicit])
def test_compiled_host_calls_keep_data_out_of_keyword_control(source, payload):
    """The callee receives the twin's Python value while call syntax keeps data separate."""
    received = pythonic(payload)
    with MeTTa() as context:
        compiled = context.self.define(source, name=f"framed-{source.__name__}")
        if source in (_implicit, _explicit):
            assert compiled(payload).one() == _received(received)
        else:
            for callback in (_received, partial(_received)):
                assert compiled(callback, payload).one() == source(callback, received)


@pytest.mark.parametrize("source", [_direct, _expanded, _keyword, _mixed])
def test_carried_native_calls_hold_completed_operand_values(source):
    """A source name reads its bound value even when that value is executable."""
    with MeTTa() as context:
        m = context.self

        native_argument_frame = m.define(
            _native_triple if source is _mixed else _native_single,
            name="native-argument-frame",
        )
        compiled = m.define(source, name=f"native-framed-{source.__name__}")
        for payload in (S["+"](1, 2), S.Kwargs(S.entry(3)), S.live_scalar):
            m.add(S["="](S.live_scalar, 19))
            try:
                actual = compiled(native_argument_frame, payload).one()
                expected = source(native_argument_frame, payload).one()
                assert actual == expected
            finally:
                m.remove(S["="](S.live_scalar, 19))


def test_reflected_host_application_frames_remain_editable():
    """Binding returns inspectable application data, not captured host arguments."""
    with MeTTa() as context:
        m = context.self
        m.define(_expanded, name="framed-reflection-installer")
        arguments = Expression([S.Kwargs(S.entry(3))])
        application = m.eval(S["_python-bind-call"](
            S[m.name], G(_received), arguments, G({}), G("value"),
        ))[0]
        assert m.eval(application) == [_received(["Kwargs", ["entry", 3]])]
        rewritten = application.map(lambda atom: G(7) if atom == G(3) else atom)
        assert m.eval(rewritten) == [_received(["Kwargs", ["entry", 7]])]


def test_host_call_frames_do_not_inspect_callable_signatures():
    """Opaque callability does not grant permission to read host metadata."""
    class Receiver:
        @property
        def __signature__(self):
            message = "a host call does not read __signature__"
            raise AssertionError(message)

        def __call__(self, *args, **kwargs):
            return _received(*args, **kwargs)

    with MeTTa() as context:
        invoke = context.self.define(_mixed, name="framed-opaque-callable")
        assert invoke(Receiver(), S.Kwargs()).one() == _received(
            pythonic(S.Kwargs()), pythonic(S.Kwargs()), payload=pythonic(S.Kwargs()),
        )


@pytest.mark.parametrize("source", [_direct, _expanded, _keyword, _mixed])
def test_host_call_frames_preserve_borrowed_value_identity(scratch_space, source):
    """A Python value leaves its envelope only after reaching its callee."""
    invoke = scratch_space.define(source, name=f"identity-frame-{source.__name__}")
    for value in ((1, 2), [], {}, set(), object(), S.Borrowed(S.payload)):
        seen = []

        def observe(*args, expected=value, seen=seen, **kwargs):
            items = (*args, *kwargs.values())
            seen.extend(items)
            return bool(items) and all(item is expected for item in items)

        assert invoke(observe, G(value)).one() is True, (source.__name__, type(value), seen)
        assert seen and all(item is value for item in seen)


def test_arbitrary_keyword_shaped_data_keeps_its_argument_place():
    """Nested data never becomes an argument packet or executable source."""
    leaves = st.one_of(
        st.integers(-100, 100).map(G),
        st.text(alphabet="abc", max_size=6).map(G),
        st.sampled_from(["Kwargs", "entry", "+"]).map(lambda name: S[name]),
    )
    trees = st.recursive(leaves, lambda inner: st.lists(inner, max_size=4).map(Expression), max_leaves=12)
    with MeTTa() as context:
        sources = (_direct, _expanded, _keyword, _mixed, _implicit, _explicit)
        compiled = [context.self.define(source, name=f"arbitrary-frame-{source.__name__}") for source in sources]

        @given(st.lists(trees, max_size=4))
        def check(parts):
            payload = Expression([S.Kwargs, *parts])
            received = pythonic(payload)
            for source, function in zip(sources, compiled, strict=True):
                if source in (_implicit, _explicit):
                    assert function(payload).one() == _received(received)
                else:
                    assert function(_received, payload).one() == source(_received, received)

        check()
