"""Purpose: pin signature-aware Python call-site keyword notation.
Guarantees:
  - Defined, bound definition, bound operation, and compiled calls emit values
    in the target's declared positional order [tested:
    test_known_call_site_keywords_bind_to_positional_metta_arguments;
    commit=WORKTREE]
  - a bare Symbol refuses keywords with a positional remedy while Grounded
    heads retain the Python-call transport [tested:
    test_unknown_symbol_keywords_refuse_with_the_positional_remedy;
    commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import pytest

from metta import G, S, fn
from metta.vocabularies import EffectClass


def _ordered_pair(left, right):
    return S.pair(left, right)


def _compiled_keyword_call(value):
    return _ordered_pair(right=S.right(value), left=S.left(value))


def _compiled_fn_keyword_call(value):
    return fn.ordered_pair(right=S.right(value), left=S.left(value))


def test_known_call_site_keywords_bind_to_positional_metta_arguments(metta):
    """Direct, bound, registered, and compiled known signatures share order."""
    space = metta._new_space()
    ordered_pair = space.define(_ordered_pair, name="ordered-pair")
    compiled = space.define(_compiled_keyword_call)
    compiled_fn = space.define(_compiled_fn_keyword_call)

    assert ordered_pair(right=S.R, left=S.L) == [S.pair(S.L, S.R)]
    assert space.fn.ordered_pair(right=S.R, left=S.L) == [S.pair(S.L, S.R)]
    assert compiled(S.value) == [S.pair(S.left(S.value), S.right(S.value))]
    assert str(compiled.body) == "(ordered-pair (left $value) (right $value))"
    assert compiled_fn(S.value) == [S.pair(S.left(S.value), S.right(S.value))]
    assert str(compiled_fn.body) == "(ordered-pair (left $value) (right $value))"

    @space.op(effect=EffectClass.pureStructural)
    def registered_pair(left, right):
        return S.pair(left, right)

    assert space.fn.registered_pair(right=S.R, left=S.L) == [S.pair(S.L, S.R)]


def test_unknown_symbol_keywords_refuse_with_the_positional_remedy():
    """Unknown Symbol heads are not allowed to invent a Kwargs term."""
    with pytest.raises(TypeError, match=r"no known signature.*positionally"):
        S.head(x=S.value)

    python_head = G(round)
    assert str(python_head(3.14159, ndigits=2)) == (
        "(<builtin_function_or_method> 3.14159 (Kwargs (ndigits 2)))"
    )
