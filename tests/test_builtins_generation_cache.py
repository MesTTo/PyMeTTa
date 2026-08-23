"""Purpose: pin generation-checked builtin catalogues at namespace reads.
Assumes:
  - petta_py_function_generation/1 is supplied by the sibling engine job;
    the through-test skips by that exact seam name until it is merged
Guarantees:
  - a cache hit performs one generation read, reuses an equal generation,
    and refills after a change [tested:
    test_cache_reads_compare_the_function_generation; commit=WORKTREE]
  - a raw equation written by evaluation and the same definition written from
    source text are visible through the next function-namespace access [tested:
    test_eval_definitions_reach_the_next_namespace_access; commit=WORKTREE]
"""  # noqa: D205, D415 -- the obligation block is a searchable contract, not a prose module summary

from __future__ import annotations

from typing import cast

import pytest

from petta import S, V, space
from petta._engine import Runtime
from petta._space import _space_builtins


class _GenerationRuntime:
    """A one-crossing model of the sibling engine seam."""

    def __init__(self) -> None:
        self.generation = 1
        self.names = ["alpha"]
        self.availability_reads = 0
        self.generation_reads = 0
        self.catalogue_reads = 0

    def once(self, goal: str):
        assert goal == "current_predicate(petta_py_function_generation/1)"
        self.availability_reads += 1
        return {"truth": True}

    def apply_must(self, predicate: str):
        assert predicate == "petta_py_function_generation"
        self.generation_reads += 1
        return self.generation

    def builtins(self):
        self.catalogue_reads += 1
        return list(self.names)


def test_cache_reads_compare_the_function_generation() -> None:
    """An unchanged hit is one cheap read; a changed hit refills once."""
    runtime = _GenerationRuntime()

    typed_runtime = cast("Runtime", runtime)

    assert _space_builtins(typed_runtime, "&self") == ["alpha"]
    assert (runtime.availability_reads, runtime.generation_reads, runtime.catalogue_reads) == (
        1,
        2,
        1,
    )

    assert _space_builtins(typed_runtime, "&self") == ["alpha"]
    assert (runtime.generation_reads, runtime.catalogue_reads) == (3, 1)

    runtime.generation += 1
    runtime.names.append("beta")
    assert _space_builtins(typed_runtime, "&self") == ["alpha", "beta"]
    assert (runtime.generation_reads, runtime.catalogue_reads) == (5, 2)


def test_eval_definitions_reach_the_next_namespace_access() -> None:
    """Exercise the sibling generation seam when this worktree contains it."""
    target = space()
    if not target._rt.once("current_predicate(petta_py_function_generation/1)"):
        pytest.skip(
            "petta_py_function_generation/1 is supplied by the sibling engine job"
        )

    assert "p14-generation-raw" not in target.builtins()
    equation = S["="](S["p14-generation-raw"](V.x), V.x)
    target.eval(S["add-atom"](target, equation))
    assert target.fn.p14_generation_raw(7).one() == 7

    assert "p14-generation-text" not in target.builtins()
    target.eval(
        "(add-atom &self (= (p14-generation-text $x) (+ $x 1)))"
    )
    assert target.fn.p14_generation_text(7).one() == 8
