"""Purpose: examples/reasoning/measure.metta in Python: the weighted-superposition algebra.

`lib_measure` ships the algebra over `(weight value)` pairs: total, normalize,
best, top, collapse, expect, filter, flip, softmax, sample and choose. Nothing
is defined here but one helper, so every claim is a call on the imported
library through the bound function namespace, where a typo raises on the line
rather than answering nothing three calls later.

The answers are ordinary Python values once they cross: `one()` is the
cardinality door for the single answer each of these calls has, and
`ws-choose` is the one that answers nondeterministically, so it is read as the
sequence it is.
"""

from petta import S, fn

#: Inferences this twin spends, its own tripwire. A PLACEHOLDER: the wave's
#: integrator prices all 218 budgets in one pass on the merged tree, so no
#: figure measured in a single agent's worktree is pinned here. THIS TWIN'S
#: PREVIOUS PIN WAS AN EMPIRICAL ENVELOPE, minimum 94568, maximum 94700 over
#: 28 observations under `full-lane/218/workers=32`, so the re-pin owes it an
#: envelope rather than a point
#: [assumed: 1 is a placeholder rather than a measurement; commit=69ac4ed4182746f952374a5d2cba3aecf97d867b].
BUDGET = 1


def _rows(pairs):
    """Read a weighted-pair expression as ordinary Python nested sequences."""
    return tuple(tuple(pair) for pair in pairs)


def twin(m):
    """Import the measure algebra and check its deterministic and sampled faces."""
    m.eval(fn["import!"](m, S.library(S["lib_measure"])))

    ws_total = m.fn.ws_total
    ws_normalize = m.fn.ws_normalize
    ws_best = m.fn.ws_best
    ws_top = m.fn.ws_top
    ws_collapse = m.fn.ws_collapse
    ws_expect = m.fn.ws_expect
    ws_filter = m.fn.ws_filter
    ws_flip = m.fn.ws_flip
    ws_softmax = m.fn.ws_softmax
    ws_sample = m.fn.ws_sample
    ws_choose = m.fn.ws_choose

    assert ws_total(((0.5, S.a), (0.25, S.b), (0.25, S.c))).one() == 1.0
    assert _rows(ws_normalize(((2.0, S.a), (2.0, S.b))).one()) == (
        (0.5, S.a),
        (0.5, S.b),
    )
    assert ws_best(((0.2, S.low), (0.7, S.high), (0.1, S.mid))).one() == S.high
    assert _rows(ws_top(((0.2, S.low), (0.7, S.high), (0.1, S.mid)), 2).one()) == (
        (0.7, S.high),
        (0.2, S.low),
    )
    assert _rows(ws_collapse(((0.3, S.x), (0.4, S.y), (0.2, S.x))).one()) == (
        (0.5, S.x),
        (0.4, S.y),
    )
    assert ws_expect(((0.5, 10), (0.5, 20))).one() == 15.0
    assert _rows(ws_filter(((0.9, S.keep), (0.05, S.drop)), 0.1).one()) == (
        (0.9, S.keep),
    )
    assert _rows(ws_flip(((S.cat, 0.9), (S.dog, 0.4))).one()) == (
        (0.9, S.cat),
        (0.4, S.dog),
    )

    # Known issue: `@m.define` takes the Python name VERBATIM, where the `S`,
    # `V` and `fn` factories map every underscore to a hyphen, so a hyphenated
    # MeTTa name needs `name=` at this one door. It should read:
    #     @m.define
    #     def first_weight(pairs):
    @m.define(name="first-weight")
    def first_weight(pairs):
        """Return the first pair's weight through Python sequence indexing."""
        return pairs[0][0]

    cold = ws_softmax(((1.0, S.low), (3.0, S.high)), 0.1).one()
    assert ws_best(cold).one() == S.high
    sharp = ws_softmax(((1.0, S.a), (3.0, S.b)), 0.1).one()
    assert first_weight(sharp).one() > 0.0
    flat = ws_softmax(((1.0, S.a), (3.0, S.b)), 1000.0).one()
    assert abs(first_weight(flat).one() - 0.5) < 0.01
    spread = ws_softmax(((2.0, S.a), (5.0, S.b), (1.0, S.c)), 0.7).one()
    assert abs(ws_total(spread).one() - 1.0) < 1.0e-9

    assert ws_sample(((0.5, S.heads), (0.5, S.tails))).one() in (S.heads, S.tails)
    assert ws_sample(((1.0, S.sure),)).one() == S.sure
    assert ws_sample(((0.1, S.a), (0.2, S.b), (0.7, S.c))).one() in (S.a, S.b, S.c)

    # The nondeterministic reading: alternatives with their measure as data,
    # one answer each, which is what iterating the answers gives.
    assert _rows(ws_choose(((0.6, S.yes), (0.4, S.no)))) == (
        (0.6, S.yes),
        (0.4, S.no),
    )
