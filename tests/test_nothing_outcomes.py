"""Purpose: keep pruned evaluation and non-reduction as different observable outcomes.
Guarantees:
  - eager eval returns no atoms for Empty and the written atom for
    NotReducible, while eval_status names both paths [tested:
    test_eager_eval_keeps_empty_and_not_reducible_distinct; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - strict eager eval accepts Empty and raises StrictError carrying an
    unreduced term, including after using= substitution [tested:
    test_strict_eval_refuses_only_not_reducible; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
"""  # noqa: D205, D415 -- the obligation block is a searchable contract, not a prose module summary

from __future__ import annotations

import pytest

from metta import S
from metta.errors import StrictError


def test_eager_eval_keeps_empty_and_not_reducible_distinct(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()
    unreduced = S.UnknownHead(1)

    assert m.eval(S.empty()) == []
    assert m.eval(unreduced) == [unreduced]
    assert m.eval_status(S.empty()) == [("empty", None)]
    assert m.eval_status(unreduced) == [("not-reducible", unreduced)]


def test_strict_eval_refuses_only_not_reducible(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()
    with m.strict():
        assert m.eval(S.empty()) == []
        assert m.eval(S["+"](1, 2)) == [3]

    with pytest.raises(StrictError) as failure:
        with m.strict():
            m.eval(S.UnknownHead(S.placeholder), using={"placeholder": 7})

    assert failure.value.directive is None
    assert failure.value.term == S.UnknownHead(7)
    assert "not reducible" in str(failure.value)
