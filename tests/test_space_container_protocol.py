"""Purpose: pin the honest Python container laws of native and provider spaces.
Guarantees:
  - len() uses a provider's Sized declaration and refuses to invent a count by
    enumeration [tested: test_provider_length_requires_and_uses_sized;
    commit=WORKTREE]
  - space handles stay truthy independently of contents, with existence asked
    through a query [tested: test_space_truth_does_not_ask_for_emptiness;
    commit=WORKTREE]
  - native iteration snapshots assembly order when the iterator is created
    [tested: test_native_iteration_snapshots_before_mutation; commit=WORKTREE]
"""  # noqa: D205, D415 -- the obligation block is a searchable contract, not a prose module summary

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest

from petta import S, V
from petta.foreign import SpaceProvider


class _SizedFacts(SpaceProvider):
    """A provider that declares both enumeration and constant-time size."""

    def __init__(self, *atoms: Any) -> None:
        self.stored = list(atoms)
        self.count_reads = 0
        self.enumeration_reads = 0

    def __len__(self) -> int:
        self.count_reads += 1
        return len(self.stored)

    def atoms(self) -> Iterator[Any]:
        self.enumeration_reads += 1
        return iter(self.stored)


class _EnumerableFacts(SpaceProvider):
    """Enumeration alone makes no complexity promise about counting."""

    def __init__(self, *atoms: Any) -> None:
        self.stored = list(atoms)
        self.enumeration_reads = 0

    def atoms(self) -> Iterator[Any]:
        self.enumeration_reads += 1
        return iter(self.stored)


def test_provider_length_requires_and_uses_sized(metta):  # noqa: D103 -- the test name states the behavioral contract
    sized = _SizedFacts(S.fact(1), S.fact(2))
    unsized = _EnumerableFacts(S.fact(1), S.fact(2))
    metta._register_space(sized, "&sized-container")
    metta._register_space(unsized, "&unsized-container")
    try:
        assert len(metta._at("&sized-container")) == 2
        assert sized.count_reads == 1
        assert sized.enumeration_reads == 0

        with pytest.raises(TypeError, match=r"does not implement __len__"):
            len(metta._at("&unsized-container"))
        assert unsized.enumeration_reads == 0
    finally:
        metta._unregister_space("&sized-container")
        metta._unregister_space("&unsized-container")


def test_space_truth_does_not_ask_for_emptiness(metta):  # noqa: D103 -- the test name states the behavioral contract
    provider = _SizedFacts()
    metta._register_space(provider, "&empty-container")
    try:
        space = metta._at("&empty-container")
        assert bool(space) is True
        assert provider.count_reads == 0
        assert bool(space.query(V.x)) is False
        assert provider.count_reads == 0
    finally:
        metta._unregister_space("&empty-container")


def test_native_iteration_snapshots_before_mutation(metta):  # noqa: D103 -- the test name states the behavioral contract
    space = metta._new_space()
    first, second, later = S.fact(1), S.fact(2), S.fact(3)
    space.add(first, second)

    snapshot = iter(space)
    space.remove(first)
    space.add(later)

    assert list(snapshot) == [first, second]
    assert list(space) == [second, later]
    assert "snapshot" in type(space).__iter__.__doc__.lower()
    assert "query" in type(space).__bool__.__doc__.lower()
