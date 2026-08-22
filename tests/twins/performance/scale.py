"""examples/performance/scale.metta in Python: a million atoms, five index shapes.

`addK` bulk-loads a million `(r K (mod K 10))` atoms, and five query shapes then
ask the same store different questions: everything, a bound first argument, a
bound second, both bound, and a variable in HEAD position. The driver runs all
five and reports the counts, which is the claim.

Every definition stays in the engine, and every one of them is the benchmark:
`addK` writes with `add-atom`, the five queries match against `&self`, and the
driver names its hyphenated siblings. A compiled body has a Python name for none
of those (residue, P14.4). Reading the report is Python's: the answer is an
expression, so `list(...)` is its children.
"""

from petta import S, V, equation

#: Why this file sits below the top rung: every definition is the benchmark and
#: none of them compiles. `addK` writes with `add-atom`, the five queries match
#: a named space and collapse, and the driver names its hyphenated siblings; a
#: compiled body has a Python name for none of those.
RUNG = "every definition is the benchmark: add-atom, a named space, collapse, and hyphenated callees, none of which a compiled body can name"

#: The space every definition here writes into and matches, named as a symbol
#: because a term carries no handle.
SELF = S["&self"]

#: What a million atoms answer to the five shapes, in the driver's own order.
COUNTS = [S["all:"], 1_000_000, S["first:"], 1, S["second:"], 100_000,
          S["rel:"], 1, S["both:"], 1]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 24314635 to 24313586, -1049 (-0.0043%), by the twin
#: contract change: the `test` wrapper left the engine for Python's own
#: `assert` and reading the report became `list()` over the answer. Nothing else
#: could move: the million writes and the five matches over them are the
#: benchmark. Against the example's 25326596 the ratio is 0.9600 [measured
#: 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/performance/scale.metta`]. Prior: ADDED 2026-08-22 at 24314635 by
#: the wave-3 twin baseline.
BUDGET = 24313586


def twin(m):
    """Load a million atoms, then ask five differently-shaped questions."""
    m += equation(S.addK(V.K)).to(
        S["if"](V.K.eq(0),
                S.done,
                S["let*"](((V.K10, V.K % 10),
                           (V.t, S["add-atom"](SELF, S.r(V.K, V.K10)))),
                          S.addK(V.K - 1))))

    # Five shapes over one store: nothing bound, first bound, second bound,
    # both bound, and the relation itself a variable.
    m += equation(S["q-all"]()).to(S.collapse(S.match(SELF, S.r(V.x, V.y), S.r(V.x, V.y))))
    m += equation(S["q-first"](V.a)).to(S.collapse(S.match(SELF, S.r(V.a, V.y), S.r(V.a, V.y))))
    m += equation(S["q-second"](V.b)).to(S.collapse(S.match(SELF, S.r(V.x, V.b), S.r(V.x, V.b))))
    m += equation(S["q-both"](V.a, V.b)).to(S.collapse(S.match(SELF, S.r(V.a, V.b), S.r(V.a, V.b))))
    m += equation(S["q-rel"](V.r)).to(S.collapse(S.match(SELF, (V.r, 643, 3), (V.r, 643, 3))))

    m += equation(S["indexing-demo"](V.K)).to(
        S["let*"](((V.temp, S.addK(V.K)),
                   (V.all, S["q-all"]()),
                   (V.first, S["q-first"](7)),
                   (V.second, S["q-second"](3)),
                   (V.rel, S["q-rel"](S.r)),
                   (V.both, S["q-both"](42, 2))),
                  S["all:"](S.length(V.all),
                            S["first:"], S.length(V.first),
                            S["second:"], S.length(V.second),
                            S["rel:"], S.length(V.rel),
                            S["both:"], S.length(V.both))))

    assert list(m.one(S["indexing-demo"](1_000_000))) == COUNTS
