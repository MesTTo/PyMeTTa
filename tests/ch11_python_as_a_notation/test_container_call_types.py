"""Purpose: check container call types across native and borrowed values.

Guarantees:
  - one call declaration admits the structural image and its host container,
    including abstract membership and refinements [tested:
    test_container_parameters_accept_both_representations,
    test_abstract_container_parameters_use_python_membership,
    test_container_refinements_guard_each_representation; commit=f56380690de29cf449cd42ef1471151a3a3f27f9]
  - callable parameters and results preserve that contract at a higher-order
    call [tested: test_callable_parameters_admit_container_representations,
    test_callable_results_admit_container_representations; commit=f56380690de29cf449cd42ef1471151a3a3f27f9]
"""

from collections import UserDict, UserList, abc
from collections.abc import Callable
from typing import Annotated, Required, TypeVar

import annotated_types as at
import pytest

from metta import Expression, G, MeTTa, S
from metta._errors.errors import MettaResultError


@pytest.mark.parametrize(("annotation", "value", "image"), [
    (list[int], [1, 2], Expression([1, 2])),
    (tuple[int, ...], (1, 2), Expression([1, 2])),
    (tuple[int, str], (1, "two"), Expression([1, "two"])),
    (dict[str, int], {"one": 1, "two": 2}, Expression([S.entry("one", 1), S.entry("two", 2)])),
    (set[int], {1, 2}, Expression([1, 2])),
    (Required[list[int]], [1, 2], Expression([1, 2])),
    (TypeVar("Batch", bound=list[int]), [1, 2], Expression([1, 2])),
])
def test_container_parameters_accept_both_representations(annotation, value, image):
    """Borrowing a container does not create another answer alternative."""
    with MeTTa() as context:
        space = context.self

        @space.define
        def count(items: annotation) -> int:
            return len(items)

        assert list(count(G(value))) == [2]
        assert list(count(image)) == [2]
        with pytest.raises(MettaResultError, match=r"BadArgType|BadArgValue"):
            space.eval(S.count(G(42)), on_error="abort")


@pytest.mark.parametrize(("annotation", "value"), [
    (abc.Sequence[int], [1, 2]),
    (abc.Sequence[int], (1, 2)),
    (abc.Sequence[int], UserList([1, 2])),
    (abc.MutableSequence[int], UserList([1, 2])),
    (abc.Mapping[str, int], UserDict(one=1, two=2)),
    (abc.MutableMapping[str, int], UserDict(one=1, two=2)),
    (abc.Set[int], frozenset({1, 2})),
    (abc.MutableSet[int], {1, 2}),
])
def test_abstract_container_parameters_use_python_membership(annotation, value):
    """An ABC admits its virtual members as well as concrete MRO entries."""
    with MeTTa() as context:
        space = context.self

        @space.define
        def count(items: annotation) -> int:
            return len(items)

        assert list(count(G(value))) == [2]
        with pytest.raises(MettaResultError, match=r"BadArgType|BadArgValue"):
            space.eval(S.count(G(42)), on_error="abort")


@pytest.mark.parametrize("base", (list[int], abc.Sequence[int], list[int] | tuple[int, ...]))
def test_container_refinements_guard_each_representation(base):
    """The same native length constraint guards both physical images."""
    annotation = Annotated[base, at.MinLen(2)]
    with MeTTa() as context:
        space = context.self

        @space.define
        def count(items: annotation) -> int:
            return len(items)

        for value in (G([1, 2]), Expression([1, 2])):
            assert list(count(value)) == [2]
        for value in (G([1]), Expression([1])):
            with pytest.raises(MettaResultError, match="BadArgValue"):
                space.eval(S.count(value), on_error="abort")


def test_callable_parameters_admit_container_representations():
    """A callable's parameter keeps the same contract at a higher-order call."""
    with MeTTa() as context:
        space = context.self

        @space.define
        def count(items: list[int]) -> int:
            return len(items)

        @space.define
        def invoke(function: Callable[[list[int]], int]) -> int:
            return function([1, 2])

        assert space.eval(S.invoke(S.count)) == [2]


def test_callable_results_admit_container_representations():
    """A native function's returned list keeps its meaning inside Callable."""
    with MeTTa() as context:
        space = context.self

        @space.define
        def pair(value: int) -> list[int]:
            return [value, value + 1]

        @space.define
        def invoke(function: Callable[[int], list[int]]) -> list[int]:
            return function(3)

        assert space.eval(S.invoke(S.pair)) == [Expression([3, 4])]
