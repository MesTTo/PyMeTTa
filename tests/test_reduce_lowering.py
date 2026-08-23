"""Purpose: prove Python left folds compile to the engine's foldl forms.
Guarantees:
  - imported and module-qualified ``functools.reduce`` lower a named reducer
    to three-argument ``foldl-atom`` and a lambda to its bound-variable
    template form [tested: test_reduce_lowers_named_and_lambda_reducers;
    commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
  - reduce recognition follows the imported callable's identity rather than
    claiming an unrelated function named reduce [tested:
    test_reduce_requires_the_functools_callable_identity; commit=b1de70215dd3f0c9d5437558c57c5911c13948b5]
"""  # noqa: D205, D415 -- the obligation block is a searchable contract, not a prose module summary

from __future__ import annotations

import functools
from functools import reduce as fold

from petta import Expression, S


def test_reduce_lowers_named_and_lambda_reducers(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()

    @m.define
    def combine(accumulator, item):
        return accumulator + item

    @m.define
    def named_fold(values):
        return fold(combine, values, 0)

    @m.define
    def template_fold(values, bias):
        return functools.reduce(
            lambda accumulator, item: accumulator + item + bias,
            values,
            0,
        )

    @m.define
    def generic_fold(reducer, values, initial):
        return functools.reduce(reducer, values, initial)

    values = Expression((1, 2, 3))
    assert list(named_fold(values)) == [6]
    assert list(template_fold(values, 1)) == [9]
    assert list(generic_fold(S["+"], values, 0)) == [6]
    assert str(named_fold.body) == "(foldl-atom $values 0 combine)"
    assert str(template_fold.body) == (
        "(foldl-atom $values 0 $accumulator $item "
        "(+ (+ $accumulator $item) $bias))"
    )
    assert str(generic_fold.body) == "(foldl-atom $values $initial $reducer)"


def test_reduce_requires_the_functools_callable_identity(metta):  # noqa: D103 -- the test name states the behavioral contract
    m = metta._new_space()

    def reduce(function, values, initial):
        return function(initial, values)

    @m.define
    def lookalike(values):
        return reduce(S.Add, values, 0)

    assert str(lookalike.body) == "(reduce Add $values 0)"
