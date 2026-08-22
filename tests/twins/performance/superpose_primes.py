"""Purpose: examples/performance/superpose_primes.metta in Python: four divisor searches.

Four eight-digit primes, each found by trial division, sharing one branch
budget. The two equations are what the benchmark IS, so they stay in the engine
and only the claim moves to Python.

Neither equation can be compiled, and the second reason is the interesting one.
`find-divisor` recurses, and a compiled body names a callee by exactly its MeTTa
spelling, which no Python identifier writes with a hyphen. On top of that,
Python's `==` inside a compiled body always lowers to the prelude's `py-eq`, a
host crossing, never to MeTTa's own `==`; here that sits in the inner loop of a
divisor search. RE-MEASURED 2026-08-22 on this tree, on the same program with
Python-spellable names so both routes were reachable: the compiled route cost
913,809 inferences against the term door's 531,461, +71.96%, three runs each,
identical every time, and the compiled equation reads
`(if (py-eq (% $n $d) 0) ...)` where the example writes `(== 0 (% $n $d))`
[ai-tmp/probe/f_primes_ab.py]. That is a regression in the very benchmark this
example exists to run, so the equations are built as the terms they are and both
walls are filed as friction.

`with-pragma!` stays too: the four searches overflow the evaluator's default
stack depth without it, measured here, and `m.limits` bounds inferences and
time but not stack depth.
Guarantees:
  - every ordered atom assembled in this file passes one iterable to
    Expression [tested: test_expression_assembles_one_ordered_atom_from_an_iterable; commit=b1599bdc8201a04a3689c1a88707b6f4b53b4d22]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from petta import TRUE, Expression, S, V, equation

#: Why this file sits below the top rung: both equations ARE the benchmark and
#: neither can be compiled, so their MeTTa bodies stay MeTTa. `find-divisor`
#: recurses under a hyphenated name no Python identifier writes, and `==` in a
#: compiled body lowers to the prelude's `py-eq`, re-measured at +71.96% on this
#: very search (see the docstring above).
RUNG = "both equations are the benchmark and neither compiles: a hyphenated recursive callee, and `==` lowering to py-eq at +71.96%"

#: The equality head, needed with a GROUND left operand, which is the one shape
#: Python's own operators cannot build: `0 == x` compares rather than building.
EQ = S["=="]

#: Inferences this twin spends, its own tripwire.
#: RE-PINNED 2026-08-22, 536577 to 536319, -258 (-0.048%), by the twin contract
#: change: the `test` wrapper left the engine for Python's own `assert`, which
#: is all that could move here. The two equations and the four searches under
#: them are the benchmark. Against the example's 542340 the ratio is 0.9889
#: [measured 2026-08-22 min-of-3: `twin_coverage.py --measure
#: examples/performance/superpose_primes.metta`]. Prior: ADDED 2026-08-22 at
#: 536577 by the wave-3 twin baseline.
BUDGET = 536319


def twin(m):
    """Define trial division, then ask it about four primes."""
    m += equation(S["find-divisor"](V.n, V["test-divisor"])).to(
        S["if"](V["test-divisor"] * V["test-divisor"] > V.n,
                V.n,
                S["if"]((EQ, 0, V.n % V["test-divisor"]),
                        V["test-divisor"],
                        S["find-divisor"](V.n, V["test-divisor"] + 1))))
    m += equation(S["prime?"](V.n)).to(V.n.eq(S["find-divisor"](V.n, 2)))

    # Four searches share one branch budget, so the benchmark states a finite
    # allowance above the evaluator's 100000 default.
    searches = (S["prime?"](53537257), S["prime?"](53781811),
                S["prime?"](54218443), S["prime?"](54734431))
    assert m.eval(
        S["with-pragma!"]((S["max-stack-depth"](1000000),), searches)
    ) == [Expression((TRUE, TRUE, TRUE, TRUE))]
