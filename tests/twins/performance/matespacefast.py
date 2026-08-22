"""examples/performance/matespacefast.metta in Python: a million and a half atoms.

`rewriteK` writes three atoms per level and recurses down two branches, so
nineteen levels leave 1,572,862 atoms in the space; `mate-space-demo` runs that
and then matches everything back out. The claim is how many came back.

Both equations stay in the engine, and both ARE the benchmark. Neither can be
compiled: their bodies write with `add-atom` and match `&self`, and a compiled
body names a function by exactly its MeTTa spelling, which `add-atom` is not a
Python identifier for (residue, P14.4).

The `collapse` stays too, and that is the measured half. The dissolution table
makes `(collapse X)` into `list(...)`, and everywhere else in this corpus that
is free, because the answers are small. Here it is not: `len(m.eval(...))`
builds 1,572,862 Python atoms and OVERFLOWS the Prolog stack before it can
count them, where the engine's own `(length (collapse ...))` never materialises
one. The general shape is measured beside this file in peanofast.py: bringing
matches across to count them is quadratic in the term depth where the engine's
route is linear. So the count stays engine-side, and the missing door, a query
that projects or aggregates before it crosses, is filed as friction.
"""

from petta import S, V, equation

#: Why this file sits below the top rung: both equations are the benchmark and
#: neither compiles, and the count cannot cross into Python at this size.
RUNG = "both equations write with add-atom and match &self, and 1.5M answers cannot cross into a Python list"

#: The space these equations write into and match, named as a symbol because a
#: term carries no handle.
SELF = S["&self"]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 34349629 to 34349474, -155 (-0.00045%), by the twin
#: contract change: the `test` wrapper left the engine for Python's own
#: `assert`. Nothing else could move: the 1.5 million writes, the match over
#: them and the count of that match are the benchmark, and the count is the one
#: place in this folder where the Python spelling does not fit in memory.
#: Against the example's 37501826 the ratio is 0.9159 [measured 2026-08-22
#: min-of-3: `twin_coverage.py --measure
#: examples/performance/matespacefast.metta`]. Prior: ADDED 2026-08-22 at
#: 34349629 by the wave-3 twin baseline.
BUDGET = 34349474


def twin(m):
    """Rewrite nineteen levels deep, then count what landed."""
    m += equation(S.rewriteK(V.t, V.n)).to(
        S["if"](V.n.eq(0),
                S.done,
                S["let*"](((V._1, S["add-atom"](SELF, S.num(S.M(V.t)))),
                           (V._2, S["add-atom"](SELF, S.num(S.W(V.t)))),
                           (V._3, S["add-atom"](SELF, S.num(S.C(V.t))))),
                          (S.rewriteK(S.M(V.t), V.n - 1),
                           S.rewriteK(S.W(V.t), V.n - 1)))))

    m += equation(S["mate-space-demo"](V.K)).to(
        S["let*"](((V.s, S["add-atom"](SELF, S.num(S.Z))),
                   (V.g, S.rewriteK(S.Z, V.K))),
                  S.match(SELF, S.num(V.stored), S.num(V.stored))))

    assert m.eval(S.length(S.collapse(S["mate-space-demo"](19)))) == [1572862]
