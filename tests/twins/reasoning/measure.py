"""Purpose: express the measure example through the Python surface.

The weighted-superposition algebra stays in the shipped ``lib_measure`` library.

Guarantees:
  - all sixteen source claims run against the imported library, including the
    three probabilistic membership claims and the nondeterministic ``ws-choose``
    reading [measured: twin completed; command=PYTHONPATH=bindings/python python -c "import runpy; from petta import MeTTa; runpy.run_path('bindings/python/tests/twins/reasoning/measure.py') ['twin'](MeTTa(petta_path='.'))"; fixture=fresh isolated process; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import S

#: The imported library and its hyphenated function names have no bound
#: attribute surface on this branch, so they descend to the existing naming
#: doors. The claims themselves use Python calls, structure, and assertions.
RUNG = "the imported library and its hyphenated functions use the current naming doors"

#: The import target required by the current import form.
SELF = S["&self"]

#: Successful costs from two complete concurrent ten-round observations plus
#: eight subsequent complete gate-protocol observations
#: [measured: 94568..94700 over 28 observations; command=python bindings/python/tools/twin_coverage.py --observe --rounds 10, repeated twice, then python bindings/python/tools/twin_coverage.py, repeated eight times; fixture=full-lane/218/workers=32; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22].
BUDGET = {
    "minimum": 94568,
    "maximum": 94700,
    "observations": 28,
    "protocol": "full-lane/218/workers=32",
}


def _rows(pairs):
    """Read a weighted-pair expression as ordinary Python nested sequences."""
    return tuple(tuple(pair) for pair in pairs)


def twin(m):
    """Import the measure algebra and check its deterministic and sampled faces."""
    m.eval(S["import!"](SELF, S.library(S.lib_measure)))

    ws_total = m.fn("ws-total")
    ws_normalize = m.fn("ws-normalize")
    ws_best = m.fn("ws-best")
    ws_top = m.fn("ws-top")
    ws_collapse = m.fn("ws-collapse")
    ws_expect = m.fn("ws-expect")
    ws_filter = m.fn("ws-filter")
    ws_flip = m.fn("ws-flip")
    ws_softmax = m.fn("ws-softmax")
    ws_sample = m.fn("ws-sample!")
    ws_choose = m.fn("ws-choose")

    assert ws_total(((0.5, S.a), (0.25, S.b), (0.25, S.c))) == 1.0
    assert _rows(ws_normalize(((2.0, S.a), (2.0, S.b)))) == (
        (0.5, S.a),
        (0.5, S.b),
    )
    assert ws_best(((0.2, S.low), (0.7, S.high), (0.1, S.mid))) == S.high
    assert _rows(ws_top(((0.2, S.low), (0.7, S.high), (0.1, S.mid)), 2)) == (
        (0.7, S.high),
        (0.2, S.low),
    )
    assert _rows(ws_collapse(((0.3, S.x), (0.4, S.y), (0.2, S.x)))) == (
        (0.5, S.x),
        (0.4, S.y),
    )
    assert ws_expect(((0.5, 10), (0.5, 20))) == 15.0
    assert _rows(ws_filter(((0.9, S.keep), (0.05, S.drop)), 0.1)) == (
        (0.9, S.keep),
    )
    assert _rows(ws_flip(((S.cat, 0.9), (S.dog, 0.4)))) == (
        (0.9, S.cat),
        (0.4, S.dog),
    )

    @m.define(name="first-weight")
    def first_weight(pairs):
        """Return the first pair's weight through Python sequence indexing."""
        return pairs[0][0]

    cold = ws_softmax(((1.0, S.low), (3.0, S.high)), 0.1)
    assert ws_best(cold) == S.high
    assert first_weight(ws_softmax(((1.0, S.a), (3.0, S.b)), 0.1))[0] > 0.0
    assert abs(
        first_weight(ws_softmax(((1.0, S.a), (3.0, S.b)), 1000.0))[0] - 0.5
    ) < 0.01
    assert abs(
        ws_total(ws_softmax(((2.0, S.a), (5.0, S.b), (1.0, S.c)), 0.7)) - 1.0
    ) < 1.0e-9

    assert ws_sample(((0.5, S.heads), (0.5, S.tails))) in (S.heads, S.tails)
    assert ws_sample(((1.0, S.sure),)) == S.sure
    assert ws_sample(((0.1, S.a), (0.2, S.b), (0.7, S.c))) in (S.a, S.b, S.c)

    assert _rows(ws_choose.all(((0.6, S.yes), (0.4, S.no)))) == (
        (0.6, S.yes),
        (0.4, S.no),
    )
