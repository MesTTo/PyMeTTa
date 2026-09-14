"""Purpose: retain Python subscription arity in native annotation records.

Guarantees:
  - callable contracts rebuild zero, one and several type arguments through
    their original annotation constructors [tested:
    test_callable_annotation_records_preserve_subscription_arity;
    test_live_callable_annotation_edits_keep_single_argument_wrappers;
    commit=WORKTREE]
"""

import inspect
import typing
from collections.abc import Callable

import pytest

from metta import Expression, G, MeTTa, S, V, convert
from metta._catalog import call_signatures


@pytest.mark.parametrize("annotation", (
    typing.Required[dict[str, int]],
    typing.NotRequired[dict[str, int]],
    typing.ReadOnly[dict[str, int]],
    typing.Final[int],
    typing.ClassVar[str],
    typing.TypeGuard[int],
    typing.TypeIs[str],
    typing.Unpack[tuple[int, ...]],
    list[int],
    set[str],
    tuple[int],
    tuple[()],
    tuple[int, str],
    dict[str, int],
    Callable[[], int],
    Callable[[int], str],
    Callable[..., int],
    typing.Literal[False],
    typing.Annotated[list[int], "data"],
))
def test_callable_annotation_records_preserve_subscription_arity(annotation):
    """Complete signatures round-trip every supplied annotation's actual species."""
    signature = inspect.Signature([
        inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY, annotation=annotation),
    ], return_annotation=annotation)
    assert call_signatures.build(call_signatures.project(signature, G)) == signature


def test_live_callable_annotation_edits_keep_single_argument_wrappers():
    """A retained native value observes a newly written parameter and return type."""
    with MeTTa() as context:
        home = context.self
        image = S["|->"](Expression([V.value]), S.evalc(S.noeval(V.value), home))
        original = inspect.Signature([
            inspect.Parameter("value", inspect.Parameter.POSITIONAL_ONLY, annotation=list[int]),
        ], return_annotation=list[int])
        row = S["@python-callable"](image, call_signatures.project(original, G), S.one)
        home.add(row)
        value = convert.build(image, Callable[..., object], space=home)
        assert inspect.signature(value) == original
        changed = original.replace(
            parameters=[next(iter(original.parameters.values())).replace(annotation=typing.Required[dict[str, int]])],
            return_annotation=typing.NotRequired[dict[str, int]],
        )
        home.remove(row)
        home.add(S["@python-callable"](image, call_signatures.project(changed, G), S.one))
        assert inspect.signature(value) == changed


@pytest.mark.parametrize("arguments", (Expression([]), Expression([G(int), G(str)])))
def test_callable_annotation_records_preserve_constructor_refusals(arguments):
    """An invalid application still raises the annotation constructor's own error."""
    image = S["host-apply"](call_signatures.annotation(typing.Required), arguments)
    with pytest.raises(TypeError, match="Required accepts only a single type"):
        call_signatures.annotation_value(image)
