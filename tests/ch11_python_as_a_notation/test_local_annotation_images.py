"""Purpose: retain container values under local native annotation claims.

Guarantees:
  - local claims share the existing call boundary's structural and borrowed
    images while scalar and late-alias constraints remain observable
    [tested: sh extensions/python/test.sh tests/ch11_python_as_a_notation/test_local_annotation_images.py
    -n 0, eleven cases; commit=WORKTREE].
Owns resources:
  - pytest's metta fixture owns declarations; monkeypatch restores the
    annotation alias after every parameterized case.
"""

import pytest

from metta import Expression, G, S
from metta.convert import project

type Claim = object


def test_local_container_literal_retains_its_value(metta):
    """A list literal survives its written list assertion."""
    @metta.define
    def native_literal():
        values: list = [2]
        return values

    assert metta.eval(native_literal()) == [Expression([G(2)])]


@pytest.mark.parametrize("parameterized", [False, True])
@pytest.mark.parametrize("kind,value,arguments", [
    (list, [1, 2], int),
    (tuple, (1, 2), (int, ...)),
    (dict, {"one": 1}, (str, int)),
    (set, {1, 2}, int),
])
def test_local_alias_accepts_its_structural_and_borrowed_images(
    metta, monkeypatch, *, kind, value, arguments, parameterized,
):
    """One annotation admits its declared images and refuses a foreign typed value.

    The Python callable projects a container argument to its structural image,
    so the borrowed value crosses through the MeTTa-side call, which keeps its
    identity; a value typed %Undefined% is admitted by MeTTa typing, so the
    refused value is a Number.
    """
    annotation = kind[arguments] if parameterized else kind
    monkeypatch.setitem(globals(), "Claim", annotation)

    @metta.define
    def local_image(value):
        selected: Claim = value
        return selected

    structural = project(value, annotation).atom
    assert metta.eval(local_image(structural)) == [structural]
    borrowed, = metta.eval(S["local-image"](G(value)))
    assert borrowed.value is value
    assert metta.eval(S["local-image"](1.5)) == []


def test_local_type_alias_uses_the_same_container_image(metta):
    """A source type alias and its local claim admit the same expression."""
    @metta.define
    def local_alias(value):
        type Items = list
        selected: Items = value
        return selected

    value = Expression([G(3)])
    assert metta.eval(local_alias(value)) == [value]


def test_local_scalar_claim_still_filters_invalid_values(metta):
    """Admitting a container image does not remove a local scalar assertion."""
    @metta.define
    def local_number(value):
        selected: int = value
        return selected

    assert metta.eval(local_number(3)) == [3]
    assert metta.eval(S["local-number"]("wrong")) == []
