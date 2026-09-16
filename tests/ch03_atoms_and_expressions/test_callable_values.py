"""Purpose: preserve native callable values and their lexical program on return.

Guarantees:
  - storage and reconstruction retain named or parametric lexical homes,
    and calls read subsequent native body edits [tested:
    test_native_callable_values_keep_their_lexical_program; commit=ec999c898a35a79e88d4d9d3e7192abfe043f928]
  - an evaluated anonymous function's segment application executes the
    assembled call, including captured arguments [tested:
    test_evaluated_native_lambdas_apply_their_assembled_arguments; commit=8e2b7e3024713881f716e3d3a6a995bdf7231397]
  - carrying an implicit lexical home preserves the original native signature
    [tested: test_native_callable_contracts_survive_lexical_wrapping;
    commit=c5a7c9efd83f8fbdf3e002de3864a07c5bdded3b]
  - reading a contract preserves binder identity and authored call references
    [tested: test_contract_lookup_preserves_distinct_lambda_binders;
    test_callable_conversion_keeps_authored_heads_as_live_references;
    commit=b839edac553486424fdded82e37784e4528ca606]
"""

import inspect
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from typing import Annotated, Any

import pytest

from metta import G, MeTTa, S, Space, V, convert
from metta._atoms.factories import Expression
from metta._catalog import call_signatures
from metta._errors.errors import MettaError


@pytest.mark.parametrize("name", ("&callable-home", S["callable-home"](1)))
@pytest.mark.parametrize("shape", ("partial", "lambda"))
def test_native_callable_values_keep_their_lexical_program(name, shape):
    """A stored callback keeps its home and observes a native equation edit."""
    with MeTTa() as context:
        home = Space(name)
        try:
            home.run("(: native-add (-> Number Number Number)) (= (native-add $x $y) (+ $x $y))")
            value = (home.eval(S["native-add"](3))[0] if shape == "partial"
                     else home.parse("(|-> ($y) (native-add 3 $y))"))
            function = convert.build(value, Callable[[int], int], space=home)
            assert function(4) == 7
            other = context.self
            other.add(S.callback(convert.project(function).atom))
            stored = other.match(S.callback(V.value))[0].value
            recovered = convert.build(stored, Callable[[int], int])
            assert recovered(5) == 8
            home.remove(S["="](S["native-add"](V.x, V.y), S["+"](V.x, V.y)))
            home.add(S["="](S["native-add"](V.x, V.y), S["+"](S["+"](V.x, V.y), 10)))
            assert function(4) == 17
            assert recovered(5) == 18
        finally:
            home.drop()


def test_reconstructing_a_callable_does_not_declare_its_lexical_home():
    """An unresolved home stays absent when its callable image is read."""
    with MeTTa() as context:
        m = context.self
        home = S["unallocated-callable-home"](1)
        value = S["|->"](Expression([V.value]), S.evalc(S["+"](V.value, 1), home))
        assert m.eval(S["is-space"](home)) == [False]
        with pytest.raises(TypeError, match=r"lexical home.*registered space"):
            convert.build(value, Callable[[int], int], space=m)
        assert m.eval(S["is-space"](home)) == [False]


def test_a_kept_native_callable_retains_its_scoped_program():
    """The ordinary keep graph retains a callback's lexical space."""
    with MeTTa() as context:
        m = context.self
        with m.scope():
            with m.scope() as inner:
                home = m._new_space()
                home.run("(: retained-add (-> Number Number Number)) (= (retained-add $x $y) (+ $x $y))")
                value = home.eval(S["retained-add"](3))[0]
                callback = inner.keep(convert.build(value, Callable[[int], int], space=home))
            assert callback(4) == 7
        # The scope's release retires the home; its handle reads dropped on
        # every party (metta._spaces.lease), so the refusal is the handle's
        # before the engine's released_scope_space could be.
        with pytest.raises(MettaError, match=r"released_scope_space|its space was dropped"):
            callback(5)


def test_a_native_callable_stream_uses_the_scope_cursor_owner():
    """The stored answer contract selects a cursor that scope exit closes."""
    with MeTTa() as context:
        m = context.self
        m.run("(= (native-choices) (superpose (3 5 7)))")
        image = S["|->"](Expression([]), S.evalc(S["native-choices"](), m))
        signature = inspect.Signature(return_annotation=Iterator[int])
        m.add(S["@python-callable"](image, call_signatures.project(signature, G), S.stream))
        callback = convert.build(image, Callable[[], Iterator[int]])
        with m.scope():
            cursor = callback()
            assert next(cursor) == 3
        assert list(cursor) == []
        with callback() as fresh:
            assert list(fresh) == [3, 5, 7]


def test_a_native_lambda_binds_one_value_per_signature_parameter():
    """A fixed binder list keeps keyword-only and packed variadic values."""
    with MeTTa() as context:
        m = context.self
        image = S["|->"](
            Expression([V.value, V.extra, V.scale, V.options]),
            S.evalc(S.noeval(S.bound(V.value, V.extra, V.scale, V.options)), m),
        )
        signature = inspect.Signature([
            inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("extra", inspect.Parameter.VAR_POSITIONAL),
            inspect.Parameter("scale", inspect.Parameter.KEYWORD_ONLY, default=2),
            inspect.Parameter("options", inspect.Parameter.VAR_KEYWORD),
        ])
        m.add(S["@python-callable"](image, call_signatures.project(signature, G), S.one))
        callback = convert.build(image, Callable[..., Any])
        result = callback(1, 2, 3, scale=4, bonus=5)
        assert result.head == S.bound
        assert tuple(part.value for part in result.args) == (1, (2, 3), 4, {"bonus": 5})
        assert tuple(part.value for part in callback(1).args) == (1, (), 2, {})


def test_callable_conversion_keeps_nested_lexical_context():
    """Container and record fields carry the same lexical reconstruction input."""
    @dataclass(frozen=True)
    class LexicalCallbackBox:
        callback: Callable[[int], int]

    with MeTTa() as context:
        home = context.self
        home.run("(= (nested-increment $x) (+ $x 4))")
        image = home.parse("(|-> ($x) (nested-increment $x))")
        items = convert.build(Expression([image]), list[Callable[[int], int]], space=home)
        record = convert.build(S.LexicalCallbackBox(image), LexicalCallbackBox, space=home)
        annotated = convert.build(image, Annotated[Callable[[int], int], "callback"], space=home)
        callbacks = [items[0], record.callback, annotated]
        assert [callback(x=3) for callback in callbacks] == [7, 7, 7]
        home.remove(S["="](S["nested-increment"](V.x), S["+"](V.x, 4)))
        home.add(S["="](S["nested-increment"](V.x), S["+"](V.x, 10)))
        assert [callback(x=3) for callback in callbacks] == [13, 13, 13]


@pytest.mark.parametrize("shape", ("lambda", "partial", "symbol", "grounded"))
def test_a_callable_union_keeps_its_return_annotation(shape):
    """Selecting a callable alternative preserves recursive answer conversion."""
    with MeTTa() as context:
        home = context.self
        home.run("(: native-pair (-> Number Expression)) (= (native-pair $x) (noeval ($x 9)))")
        images = {
            "lambda": home.parse("(|-> ($x) (native-pair $x))"),
            "partial": S.partial(S["native-pair"], Expression([])),
            "symbol": S["native-pair"],
            "grounded": G(lambda x: [x, 9]),
        }
        callback = convert.build(images[shape], Callable[[int], list[int]] | None, space=home)
        assert callback(3) == [3, 9]


def test_a_callable_union_leaves_nonfunction_symbols_to_their_annotation():
    """A named callable alternative does not steal another symbol's meaning."""
    class CallableChoice(Enum):
        selected = 1

    with MeTTa() as context:
        annotation = Annotated[Callable[[int], int], "callback"] | CallableChoice
        assert convert.build(S.selected, annotation, space=context.self) is CallableChoice.selected


def test_an_evaluated_bound_lambda_keeps_its_native_signature():
    """Recovering a compiled closure keeps its editable source call contract."""
    with MeTTa() as context:
        home = context.self
        body = S.evalc(S["+"](V.x, V.y), home)
        canonical = S["|->"](Expression([V.x, V.y]), body)
        bound = S["|->"](Expression([V.y]), S.evalc(S["+"](3, V.y), home))
        signature = inspect.Signature([
            inspect.Parameter("x", inspect.Parameter.POSITIONAL_ONLY),
            inspect.Parameter("y", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=5),
        ], return_annotation=int)
        contract = S["@python-callable"](canonical, call_signatures.project(signature, G), S.one)
        home.add(contract)
        home.add(S["@python-binding"](bound, canonical, 1))
        evaluated = home.eval(Expression([canonical, G(3)]))[0]
        callback = convert.build(evaluated, Callable[..., int], space=home)
        assert callback() == 8
        assert callback(y=7) == 10
        parameters = tuple(signature.parameters.values())
        changed = signature.replace(parameters=[parameters[0], parameters[1].replace(default=9)])
        home.remove(contract)
        home.add(S["@python-callable"](canonical, call_signatures.project(changed, G), S.one))
        assert callback() == 12


@pytest.mark.parametrize("captured", (False, True))
def test_evaluated_native_lambdas_apply_their_assembled_arguments(captured):
    """An arrowless native closure applies its full call and keeps live lookup."""
    with MeTTa() as context:
        home = context.self
        original = S["="](S["anonymous-add"](V.base, V.value), S["+"](V.base, V.value))
        home.add(original)
        written = ("(|-> ($base $value) (anonymous-add $base $value))" if captured
                   else "(|-> ($value) (anonymous-add 10 $value))")
        value = home.eval(home.parse(written))[0]
        if captured:
            value = home.eval(Expression([value, 10]))[0]
        callback = convert.build(value, Callable[[int], int], space=home)
        assert callback(3) == 13
        home.remove(original)
        home.add(S["="](S["anonymous-add"](V.base, V.value), S["+"](S["+"](V.base, V.value), 100)))
        assert callback(3) == 113


@pytest.mark.parametrize("evaluated", (False, True))
def test_native_callable_contracts_survive_lexical_wrapping(evaluated):
    """A carried home retains the source contract and its later graph edits."""
    with MeTTa() as context:
        home = context.self
        equation = S["="](S["lexical-pair"](V.left, V.right), S["+"](S["*"](V.left, 10), V.right))
        home.add(equation)
        image = S["|->"](Expression([V.left, V.right]), S["lexical-pair"](V.left, V.right))
        signature = inspect.Signature([
            inspect.Parameter("left", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("right", inspect.Parameter.POSITIONAL_OR_KEYWORD, default=2),
        ], return_annotation=int)
        contract = S["@python-callable"](image, call_signatures.project(signature, G), S.one)
        home.add(contract)
        callback = convert.build(home.eval(image)[0] if evaluated else image, Callable[..., int], space=home)
        assert callback(left=3) == 32
        with home._new_space() as other:
            other.add(S.callback(convert.project(callback).atom))
            recovered = convert.build(other.match(S.callback(V.value))[0].value, Callable[..., int])
            assert recovered(right=4, left=3) == 34
            parameters = tuple(signature.parameters.values())
            changed = signature.replace(parameters=[parameters[0], parameters[1].replace(default=9)])
            home.remove(contract)
            home.add(S["@python-callable"](image, call_signatures.project(changed, G), S.one))
            assert callback(left=3) == recovered(left=3) == 39
            home.remove(equation)
            home.add(S["="](equation.args[0], S["+"](equation.args[1], 100)))
            assert callback(left=3) == recovered(left=3) == 139


@pytest.mark.parametrize("evaluated", (False, True))
def test_contract_lookup_preserves_distinct_lambda_binders(evaluated):
    """Matching a signature cannot equate the arguments of a reordered body."""
    with MeTTa() as context:
        home = context.self
        home.run("(= (native-pair $left $right) (+ (* $left 10) $right))")
        canonical = S["|->"](Expression([V.left, V.right]), S["native-pair"](V.left, V.right))
        signature = inspect.Signature([
            inspect.Parameter("left", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("right", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ])
        home.add(S["@python-callable"](canonical, call_signatures.project(signature, G), S.one))
        swapped = S["|->"](Expression([V.left, V.right]), S["native-pair"](V.right, V.left))
        callback = convert.build(home.eval(swapped)[0] if evaluated else swapped, Callable[[int, int], int], space=home)
        assert callback(3, 4) == 43


@pytest.mark.parametrize("warm", (False, True))
def test_callable_conversion_keeps_authored_heads_as_live_references(warm):
    """A matching contract for a callee does not inline its caller's body."""
    with MeTTa() as context:
        home = context.self
        home.run("""
          (= (declared-pair $left $right) (+ (* $left 10) $right))
          (= (forward-pair $left $right) (declared-pair $left $right))
        """)
        canonical = S["|->"](Expression([V.left, V.right]), S["declared-pair"](V.left, V.right))
        signature = inspect.Signature([
            inspect.Parameter("left", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("right", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ])
        home.add(S["@python-callable"](canonical, call_signatures.project(signature, G), S.one))
        if warm:
            assert home.eval(S["forward-pair"](3, 4)) == [34]
        callback = convert.build(S["forward-pair"], Callable[[int, int], int], space=home)
        assert callback(3, 4) == 34
        home.remove(S["="](S["forward-pair"](V.left, V.right), V.body))
        home.add(S["="](S["forward-pair"](V.left, V.right), 73))
        assert callback(3, 4) == 73
