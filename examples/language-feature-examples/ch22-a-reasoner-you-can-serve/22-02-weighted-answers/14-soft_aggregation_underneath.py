"""examples/ch22-a-reasoner-you-can-serve/22-02-weighted-answers/14-soft_aggregation_underneath.metta in Python: how a soft score walks a term.

The similarity facts are ordinary atoms written into the space, and the
aggregation is chosen by NAME, so `S.min` and `S.mean` are symbols rather
than Python callables: the fold dispatches on the name it is handed.

`soft-symbol?` tests the WRITTEN representation rather than the metatype,
which is why `min` answers True: a metatype test would answer False for every
name the engine holds a function for.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from metta import G, S, lib


def twin(m):
    """A symbol test, two aggregations, and the walk under each."""
    m += lib.soft
    m += [S.similar(S.cat, S.feline, 0.8), S.similar(S.fish, S.shark, 0.5)]
    symbol, fold, walk = m.fn["soft-symbol?"], m.fn["soft-fold"], m.fn["soft-walk"]

    assert symbol(S.cat) == [True]
    assert symbol(S.min) == [True]
    assert symbol(1) == [False]
    assert symbol(G("text")) == [False]
    assert symbol(S.f(1)) == [False]

    # `min` is the fuzzy t-norm, so a term is as close as its WORST position.
    assert fold(S.min, (S.cat, S.fish), (S.feline, S.fish)) == [0.8]
    assert fold(S.min, (S.cat, S.fish), (S.feline, S.shark)) == [0.5]
    assert fold(S.min, (S.cat, S.fish), (S.dog, S.fish)) == [0.0]
    assert fold(S.min, (S.cat, S.fish), (S.cat, S.fish)) == [1.0]

    # `mean` averages instead, which is the aggregation ranking wants: one
    # unrelated symbol takes a strong match to zero under `min` and to a
    # middling number under `mean`.
    assert fold(S.mean, (S.cat, S.fish), (S.feline, S.shark)) == [0.65]
    assert fold(S.mean, (S.cat, S.fish), (S.dog, S.fish)) == [0.5]

    # The walk is the recursion each fold runs, with the accumulator exposed:
    # `min` starts at 1.0 and takes minima, `mean` starts at 0.0 and SUMS.
    assert walk(S.min, (S.cat, S.fish), (S.feline, S.shark), 1.0) == [0.5]
    assert walk(S.mean, (S.cat, S.fish), (S.feline, S.shark), 0.0) == [1.3]
    assert fold(S.mean, (S.cat, S.fish), (S.feline, S.shark))[0].value == (
        walk(S.mean, (S.cat, S.fish), (S.feline, S.shark), 0.0)[0].value / 2
    )

    # Which is where `min`'s early stop lives: once the accumulator is 0.0 no
    # later position can raise it, so the positions after the mismatch are
    # never scored.
    assert walk(S.min, (S.dog, S.whale, S.otter), (S.cat, S.shark, S.seal), 1.0) == [0.0]
    assert walk(S.min, (S.dog, S.whale), (S.cat, S.shark), 0.0) == [0.0]

    # Both walks over nothing answer the accumulator they were given.
    assert walk(S.min, (), (), 1.0) == [1.0]
    assert walk(S.mean, (), (), 0.0) == [0.0]

    # And the aggregation a space DECLARES is what `soft-score` folds with.
    assert m.fn["soft-score"](S.likes(S.cat, S.fish), S.likes(S.feline, S.shark)) == [0.5]
    m += S.soft_aggregate(S.mean)
    assert m.fn["soft-score"](
        S.likes(S.cat, S.fish), S.likes(S.feline, S.shark)
    ) == fold(S.mean, S.likes(S.cat, S.fish), S.likes(S.feline, S.shark))


#: MEASURED on this branch rather than inherited: this twin is new, so there is
#: no earlier pin to move
#: [measured 2026-09-07: 138416 inferences, 1.0160x the example's 136240; command=python
#: extensions/python/tools/twin_coverage.py --measure --rounds 3;
#: fixture=docs/every-atom-has-an-example at its example commits; commit=98397cdd04679cbf40b2d515076dadc09c1b0a32].
BUDGET = 138416
