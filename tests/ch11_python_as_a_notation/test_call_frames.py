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
  - a positional call of a bound callee is the written application, and the
    engine's grounded call crosses through the seam's codec, so a Python
    callable sees the same values from MeTTa and from a compiled body: an
    expression as a tuple under its Symbol head, a symbol as a Symbol, None
    held, returned syntax held [tested:
    test_a_positional_call_of_a_bound_callee_is_the_written_application,
    test_grounded_applications_use_the_seam_codec; commit=fd0af38f748cedb593dd4e12c4dc19e8c283323a]
  - a `(Kwargs ...)` is keywords only where it is written last at a call
    site, after a grounded head, a Python-bound symbol or a bind! token, with
    the pair values evaluated and the names left as names; arriving in a
    value it is data, and after a MeTTa function it is that function's
    argument [tested: test_grounded_applications_read_keywords_only_where_written;
    commit=fd0af38f748cedb593dd4e12c4dc19e8c283323a]
"""

from collections.abc import Callable
from functools import partial
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import Atom, Expression, G, MeTTa, S, V, py
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
    """The callee receives the twin's Python value while call syntax keeps data separate.

    An expanded or keyword call crosses as call frames, which MeTTa has no
    syntax for, and a host island is applied by the seam; a plain positional
    call of a bound callee is MeTTa's own application, whose grounded call
    now crosses through the same codec (`host.grounded_apply`) and reads keywords only
    from a `(Kwargs ...)` written at the call site. Every route hands the
    callee the same Python values, a `Kwargs`-shaped value included.
    """
    received = pythonic(payload)
    with MeTTa() as context:
        compiled = context.self.define(source, name=f"framed-{source.__name__}")
        if source in (_implicit, _explicit):
            assert compiled(payload).one() == _received(received)
        else:
            for callback in (_received, partial(_received)):
                assert compiled(callback, payload).one() == source(callback, received)


@pytest.mark.parametrize("payload", [S.Kwargs(S.entry(3)), S["+"](1, 2), S.live_scalar])
def test_a_positional_call_of_a_bound_callee_is_the_written_application(payload):
    """`function(value)` on a parameter is `($function $value)`, whatever the callee holds.

    `(= (f $g $x) (repra ($g $x)))` is how the examples spell it, and an
    Atom-typed result shows that body as written. A native head applies
    natively and receives the bound value as it is; a grounded host callable
    is applied by the engine's own grounded call, exactly as the same
    application written in MeTTa, and that call hands the callee the seam's
    values, so the compiled body and the Python source agree too.
    """
    with MeTTa() as context:
        m = context.self
        compiled = m.define(_direct, name="positional-direct")
        native = m.define(_native_single, name="positional-native-frame")
        assert compiled(native, payload).one() == S.observed(payload)
        for callback in (_received, partial(_received)):
            written = m.eval(S.let(V.f, S.noeval(G(callback)),
                                   S.let(V.v, S.noeval(payload), Expression([V.f, V.v]))))
            assert compiled(callback, payload).one() == written[0].value
            assert compiled(callback, payload).one() == _direct(callback, pythonic(payload))


def test_grounded_applications_use_the_seam_codec():
    """A Python callable applied from MeTTa sees what a compiled body's host call sees."""
    with MeTTa() as context:
        m = context.self
        held = G(_received)
        for payload in (S["+"](1, 2), S.Kwargs(S.entry(3)), S.pair(S.a, Expression([1, 2]))):
            # A bound value crosses as the value it is: an expression is a
            # tuple under its Symbol head, never a list of strings.
            bound = m.eval(S.let(V.v, S.noeval(payload), Expression([held, V.v])))
            assert bound == [G(_received(pythonic(payload)))]
        # A symbol stays a Symbol.
        assert m.eval(Expression([held, S.hello])) == [G(_received(S.hello))]
        # A returned None is held as None, not read as the unit.
        answer = m.eval(Expression([G(lambda: None)]))
        assert len(answer) == 1
        assert answer[0].value is None
        # A returned expression stays data, and a returned tuple is the
        # expression it spells, so a callable returning its argument is the
        # identity on expressions.
        (held_syntax,) = m.eval(Expression([G(lambda: S["+"](1, 2))]))
        assert held_syntax.value == S["+"](1, 2)
        assert m.eval(Expression([G(lambda x: x), Expression([1, 2])])) == [Expression([1, 2])]


def test_grounded_applications_read_keywords_only_where_written():
    """`(Kwargs ...)` is keywords where it is written last and data wherever it arrives as a value."""
    with MeTTa() as context:
        m = context.self
        held = G(_received)
        # Written after a grounded head, the pairs are keywords.
        assert m.eval(Expression([held, 1, S.Kwargs(S.entry(3))])) == [G(_received(1, entry=3))]
        # Written after a symbol whose value is a Python callable, the idiom
        # `(= py-round (py-atom round))`, and after a bind! token.
        m.run("(= py-round (py-atom round))")
        assert m.run("!(py-round 3.14159 (Kwargs (ndigits 2)))") == [[G(3.14)]]
        m.run("!(bind! py-dict (py-atom dict))")
        # Only the pair VALUES evaluate; a pair NAME is a name even when a
        # function of that name exists.
        m.run("(= (reverse $x) 99)")
        assert m.run("!(py-dict (Kwargs (a 1) (b (+ 1 2))))")[0][0].value == {"a": 1, "b": 3}
        assert m.run("!(py-dict (Kwargs (reverse True)))")[0][0].value == {"reverse": True}
        # Arriving in a variable, the same expression is data.
        payload = S.Kwargs(S.entry(3))
        bound = m.eval(S.let(V.kw, S.noeval(payload), Expression([held, 1, V.kw])))
        assert bound == [G(_received(1, pythonic(payload)))]
        # Written after a MeTTa function, it is that function's argument.
        m.run("(= (keep $a $b) ($a $b))")
        assert m.run("!(keep 1 (Kwargs (entry 3)))") == [[Expression([1, payload])]]
        # A compiled body passing a Kwargs-shaped value passes data.
        compiled = m.define(_direct, name="keyword-shaped-direct")
        assert compiled(_received, payload).one() == _direct(_received, pythonic(payload))


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
        assert m.eval(application) == [_received((S.Kwargs, (S.entry, 3)))]
        rewritten = application.map(lambda atom: G(7) if atom == G(3) else atom)
        assert m.eval(rewritten) == [_received((S.Kwargs, (S.entry, 7)))]


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
