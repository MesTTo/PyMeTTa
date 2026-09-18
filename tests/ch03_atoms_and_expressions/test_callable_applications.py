"""Purpose: apply native callables through editable positional and keyword frames.

Guarantees:
  - carried applications preserve value frames in their own home or another
    home, retaining fixed, patterned and segment binders [tested:
    test_native_application_frames_preserve_values_in_carried_homes,
    test_native_value_binding_keeps_lambda_parameter_patterns; commit=310a9d8b547a77412a518a37ab79fba073eb22ac]
  - native application facts preserve data, supplied arguments and lexical
    ownership [tested: test_native_application_frames_preserve_data_and_live_programs;
    test_native_application_frames_retain_scoped_streams; commit=1d6b29cc4c734796ba173ee06e3b20568a1acf85]
  - forwarding retains captures and ambiguous application facts refuse
    [tested: test_forwarded_application_frames_preserve_captured_arguments;
    test_native_application_mapping_lookup_preserves_distinct_binders;
    commit=1d6b29cc4c734796ba173ee06e3b20568a1acf85]
"""

import inspect
from collections.abc import Callable, Iterator
from typing import Any

import pytest

from metta import Atom, Expression, G, MeTTa, S, Space, V, convert
from metta._catalog import call_signatures
from metta._errors.errors import MettaError


def _declaration(home, signature, *, stream=False):
    image = S["|->"](
        Expression([S[":seg"](V.arguments)]),
        S.evalc(S.noeval(S.original(V.arguments)), home),
    )
    home.add(S["@python-callable"](image, call_signatures.project(signature, G), S.stream if stream else S.one))
    home.run("(: application-frames (-> Expression Expression %Undefined%)) "
             "(= (application-frames $positional $keywords) (noeval (received $positional $keywords)))")
    return image


@pytest.mark.parametrize("home_name", ("&application-home", S["application-home"](1)))
@pytest.mark.parametrize("kind", ("symbol", "lambda"))
@pytest.mark.parametrize("evaluated", (False, True))
def test_native_application_frames_preserve_data_and_live_programs(home_name, kind, evaluated):
    """Only explicit arguments enter the application; its native code owns defaults."""
    with MeTTa() as context:
        home = Space(home_name)
        try:
            signature = inspect.Signature([
                inspect.Parameter("value", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=S["native-default"]()),
                inspect.Parameter("rest", inspect.Parameter.VAR_POSITIONAL),
                inspect.Parameter("flag", inspect.Parameter.KEYWORD_ONLY, default=5),
                inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD),
            ])
            image = _declaration(home, signature)
            applicator = S["application-frames"]
            if kind == "lambda":
                applicator = S["|->"](Expression([V.positional, V.keywords]), applicator(V.positional, V.keywords))
            mapping = S["@python-application"](image, applicator)
            home.add(mapping)
            callback = convert.build(home.eval(image)[0] if evaluated else image, Callable[..., Atom], space=home)
            assert callback() == S.received(Expression([]), Expression([]))
            data = S.Kwargs(S.entry(3))
            assert callback(data, 1, flag=2, extra=data) == S.received(
                Expression([data, 1]), Expression([Expression(["flag", 2]), Expression(["extra", data])]),
            )
            assert callback(S["+"], 1, 2) == S.received(S["+"](1, 2), Expression([]))
            with pytest.raises(TypeError, match="multiple values"):
                callback(1, value=2)

            context.self.add(S.callback(convert.project(callback).atom))
            stored = context.self.match(S.callback(V.value))[0].value
            recovered = convert.build(stored, Callable[..., Atom])
            home.remove(mapping)
            replacement = S["|->"](Expression([V.positional, V.keywords]), S.noeval(S.replaced(V.positional, V.keywords)))
            home.add(S["@python-application"](image, replacement))
            assert recovered(value=data) == S.replaced(Expression([]), Expression([Expression(["value", data])]))
            home.remove(S["@python-application"](image, replacement))
            home.add(mapping)
            home.remove(S["="](S["application-frames"](V.positional, V.keywords), S.noeval(S.received(V.positional, V.keywords))))
            home.add(S["="](S["application-frames"](V.positional, V.keywords), S.noeval(S.rewritten(V.positional, V.keywords))))
            assert recovered(data) == S.rewritten(Expression([data]), Expression([]))
        finally:
            home.drop()


@pytest.mark.parametrize("written", (False, True))
def test_forwarded_application_frames_preserve_captured_arguments(written):
    """A partial named reference prepends captures to the application's frame."""
    with MeTTa() as context:
        home = context.self
        home.run("(= (application-target $left $right) (noeval (ordinary $left $right))) "
                 "(: captured-frames (-> Expression Expression %Undefined%)) "
                 "(= (captured-frames $positional $keywords) (noeval (received $positional $keywords)))")
        canonical = S["|->"](Expression([V.left, V.right]), S.evalc(S["application-target"](V.left, V.right), home))
        signature = inspect.Signature([
            inspect.Parameter("left", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("right", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ])
        home.add(S["@python-callable"](canonical, call_signatures.project(signature, G), S.one))
        home.add(S["@python-application"](canonical, S["captured-frames"]))
        image = (S["|->"](Expression([V.right]), S["application-target"](S.Captured, V.right))
                 if written else S.partial(S["application-target"], Expression([S.Captured])))
        callback = convert.build(image, Callable[..., Atom], space=home)
        data = S.Kwargs(S.entry(3))
        assert callback(data) == S.received(Expression([S.Captured, data]), Expression([]))
        assert callback(right=data) == S.received(Expression([S.Captured]), Expression([Expression(["right", data])]))


def test_native_application_mapping_lookup_preserves_distinct_binders():
    """Application lookup is directional and never identifies the callable's binders."""
    with MeTTa() as context:
        home = context.self
        image = S["|->"](Expression([V.left, V.right]), S.evalc(S.noeval(S.ordinary(V.left, V.right)), home))
        signature = inspect.Signature([
            inspect.Parameter("left", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("right", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ])
        home.add(S["@python-callable"](image, call_signatures.project(signature, G), S.one))
        wrong = image.subs({V.right: V.left})
        replacement = S["|->"](Expression([V.positional, V.keywords]), S.noeval(S.received(V.positional, V.keywords)))
        home.add(S["@python-application"](wrong, replacement))
        callback = convert.build(image, Callable[..., Atom])
        assert callback(1, 2) == S.ordinary(1, 2)
        mapping = S["@python-application"](image, replacement)
        home.add(mapping)
        assert callback(1, 2) == S.received(Expression([1, 2]), Expression([]))
        home.add(mapping)
        with pytest.raises(TypeError, match="one native application"):
            callback(1, 2)


@pytest.mark.parametrize("name", ("self", "args", "kwargs"))
def test_native_application_keywords_do_not_bind_adapter_parameters(name):
    """Every keyword name belongs to the native signature, including self."""
    with MeTTa() as context:
        home = context.self
        signature = inspect.Signature([inspect.Parameter(name, inspect.Parameter.KEYWORD_ONLY)])
        image = _declaration(home, signature)
        home.add(S["@python-application"](image, S["application-frames"]))
        callback = convert.build(image, Callable[..., Atom])
        assert callback(**{name: 3}) == S.received(Expression([]), Expression([Expression([name, 3])]))


@pytest.mark.parametrize("kind", (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD))
def test_captured_application_parameters_keep_their_keyword_binding_rule(kind):
    """Capturing a positional-only parameter leaves its name available to **kwargs."""
    with MeTTa() as context:
        home = context.self
        canonical = S["|->"](Expression([V.receiver, V.options]), S.evalc(S.noeval(S.original(V.receiver, V.options)), home))
        bound = S["|->"](Expression([V.options]), S.evalc(S.noeval(S.original(S.Captured, V.options)), home))
        signature = inspect.Signature([
            inspect.Parameter("self", kind),
            inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD),
        ])
        home.add(S["@python-callable"](canonical, call_signatures.project(signature, G), S.one))
        home.add(S["@python-binding"](bound, canonical, 1))
        applicator = S["|->"](Expression([V.positional, V.keywords]), S.noeval(S.received(V.positional, V.keywords)))
        home.add(S["@python-application"](bound, applicator))
        callback = convert.build(bound, Callable[..., Atom])
        if kind is inspect.Parameter.POSITIONAL_ONLY:
            assert callback(self=3) == S.received(Expression([]), Expression([Expression(["self", 3])]))
        else:
            with pytest.raises(TypeError, match=r"multiple values.*self"):
                callback(self=3)


def test_native_application_frames_retain_scoped_streams():
    """The carried image retains its application's home and stream cleanup."""
    with MeTTa() as context:
        m = context.self
        with m.scope():
            with m.scope() as inner:
                home = m._new_space()
                signature = inspect.Signature(return_annotation=Iterator[Any])
                image = _declaration(home, signature, stream=True)
                applicator = S["|->"](Expression([V.positional, V.keywords]), S.superpose(Expression([3, 5])))
                home.add(S["@python-application"](image, applicator))
                callback = inner.keep(convert.build(image, Callable[[], Iterator[int]]))
            with callback() as cursor:
                assert list(cursor) == [3, 5]
            with m.scope():
                cursor = callback()
                assert next(cursor) == 3
            assert list(cursor) == []
        # The scope's release retires the home; its handle reads dropped on
        # every party (metta._spaces.lease), so the refusal is the handle's
        # before the engine's released_scope_space could be.
        with pytest.raises(MettaError, match=r"released_scope_space|its space was dropped"):
            callback()


@pytest.mark.parametrize("home_name", ("&carried-application-home", S["carried-application-home"](1)))
@pytest.mark.parametrize("foreign", (False, True))
def test_native_application_frames_preserve_values_in_carried_homes(home_name, foreign):
    """Lexical application retains argument data while selecting its own home.

    The collectors are Atom-typed, so written syntax enters the frames as
    written; an unannotated collector would evaluate `(+ 1 2)` to 3 first,
    as the same application does in MeTTa.
    """
    with MeTTa() as context:
        home = context.self
        destination = Space(home_name) if foreign else home
        try:
            signature = inspect.Signature([
                inspect.Parameter("values", inspect.Parameter.VAR_POSITIONAL, annotation=Atom),
                inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD, annotation=Atom),
            ])
            image = _declaration(home, signature)
            destination.run("(: carried-frames (-> Expression Expression %Undefined%)) "
                            "(= (carried-frames $positional $keywords) (noeval (received $positional $keywords)))")
            applicator = S["|->"](Expression([V.positional, V.keywords]),
                                  S.evalc(S["carried-frames"](V.positional, V.keywords), destination))
            home.add(S["@python-application"](image, applicator))
            callback = convert.build(image, Callable[..., Atom], space=home)
            data = S["+"](1, 2)
            assert callback(S["+"], 1, 2, syntax=data) == S.received(
                data, Expression([Expression(["syntax", data])]),
            )
        finally:
            if foreign:
                destination.drop()


@pytest.mark.parametrize("kind", ("fixed", "segment", "pattern"))
def test_native_value_binding_keeps_lambda_parameter_patterns(kind):
    """The original binder matches before values enter the lexical evaluator.

    The declared parameter is Atom-typed: the lambda has no arrow of its own,
    so the declaration is what holds `(+ 1 2)` as written through the binder.
    """
    data = S["+"](1, 2)
    with MeTTa() as context:
        home = context.self
        home.run("(: syntax-frame (-> Expression %Undefined%)) "
                 "(= (syntax-frame $value) $value)")
        parameter = (S[":seg"](V.payload) if kind == "segment" else
                     S.Box(V.payload) if kind == "pattern" else V.payload)
        image = S["|->"](Expression([parameter]), S.evalc(S["syntax-frame"](V.payload), home))
        signature = inspect.Signature([
            inspect.Parameter("payload", inspect.Parameter.VAR_POSITIONAL
                              if kind == "segment" else inspect.Parameter.POSITIONAL_ONLY, annotation=Atom),
        ])
        home.add(S["@python-callable"](image, call_signatures.project(signature, G), S.one))
        callback = convert.build(image, Callable[..., Atom], space=home)
        supplied = (S["+"], 1, 2) if kind == "segment" else (S.Box(data) if kind == "pattern" else data,)
        assert callback(*supplied) == data
