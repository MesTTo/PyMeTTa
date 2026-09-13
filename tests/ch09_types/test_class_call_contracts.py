"""Purpose: verify structural call contracts across native storage and rewriting.

Guarantees:
  - ordinary Python annotation species survive a native storage roundtrip
    without opaque Signature objects [tested:
    test_native_call_contracts_preserve_annotation_species; commit=WORKTREE]
"""

import inspect
import typing
from collections import abc

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta import G, MeTTa, S
from metta._atoms.factories import Expression
from metta._catalog import call_signatures


@pytest.mark.parametrize("annotation", (
    int, float, None, type(None), typing.Any, typing.Self,
    list[int], tuple[str, ...], dict[str, int], set[float],
    typing.List, typing.List[int], typing.Callable,  # noqa: UP006 -- typing aliases are the values under test
    typing.Callable[[int], str], abc.Callable[[int], str],
    typing.Iterable[int], abc.Iterator[int],
    typing.Union[list[int], tuple[int, ...]],  # noqa: UP007 -- preserve the supplied annotation species
    typing.Literal["a", None, 3],  # noqa: PYI061 -- None inside Literal is the roundtrip witness
))
def test_native_call_contracts_preserve_annotation_species(annotation):
    """The stored record keeps exact Python annotations and remains digestible."""
    signature = inspect.Signature([
        inspect.Parameter("value", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=annotation)
    ], return_annotation=annotation)
    with MeTTa() as context:
        m = context.self
        m.add(call_signatures.project(signature, G))
        (record,) = m.atoms()
        reconstructed = call_signatures.build(record)
        assert reconstructed == signature
        assert reconstructed.bind(value=3).arguments == {"value": 3}
        with pytest.raises(TypeError):
            reconstructed.bind(3, value=4)
        assert len(m.digest()) == 64


def test_a_native_rewrite_changes_the_python_call_contract():
    """Matching parameter data changes the next binding without a host edit."""
    signature = inspect.Signature([
        inspect.Parameter("value", inspect.Parameter.KEYWORD_ONLY, default=2)
    ])
    with MeTTa() as context:
        m = context.self
        m.add(call_signatures.project(signature, G))
        m.run('''
          !(match &self
             (signature ((parameter "value" $kind $type (default 2))) $return)
             (progn
               (remove-atom &self
                 (signature ((parameter "value" $kind $type (default 2))) $return))
               (add-atom &self
                 (signature ((parameter "value" POSITIONAL_ONLY $type (default 8))) $return))))
        ''')
        (record,) = m.atoms()
        rebound = call_signatures.build(record)
        bound = rebound.bind()
        bound.apply_defaults()
        assert bound.args == (8,)
        with pytest.raises(TypeError, match="positional-only"):
            rebound.bind(value=3)


@pytest.mark.parametrize(("record", "reason"), (
    (S.signature, "needs .*signature"),
    (S.signature(S.parameter(), S.absent()), "parameter needs"),
    (S.signature(Expression([S.parameter(G("value"), S.UNKNOWN, S.absent(), Expression([]))]), S.absent()), "unknown Python parameter kind"),
    (S.signature(Expression([S.parameter(G("value"), S["KEYWORD_ONLY"], S.absent(), S.default())]), S.absent()), "signature default"),
    (S.signature(Expression([]), S["host-type"](S["absent.module"], S.Type)), "cannot be resolved"),
))
def test_malformed_native_call_contracts_refuse_before_binding(record, reason):
    """A graph edit cannot silently discard an invalid contract component."""
    with pytest.raises(TypeError, match=reason):
        call_signatures.build(record)


@given(st.lists(st.integers()), st.dictionaries(st.sampled_from(("value", "offset", "scale", "bonus")), st.integers()))
def test_native_call_contracts_preserve_python_argument_binding(positional, keywords):
    """Reconstructed contracts bind or refuse the same call as Python."""
    def source(value: int, /, offset: int = 2, *extra: int, scale: int = 3, **options: int) -> int:
        return value + offset + sum(extra) * scale + sum(options.values())

    signature = inspect.signature(source)
    native = call_signatures.build(call_signatures.project(signature, G))
    try:
        original = signature.bind(*positional, **keywords)
    except TypeError as error:
        with pytest.raises(TypeError) as refused:
            native.bind(*positional, **keywords)
        assert str(refused.value) == str(error)
    else:
        rebound = native.bind(*positional, **keywords)
        original.apply_defaults()
        rebound.apply_defaults()
        assert rebound.arguments == original.arguments
        assert source(*rebound.args, **rebound.kwargs) == source(*positional, **keywords)
