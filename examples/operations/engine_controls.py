"""Purpose: the engine-control surface on one page. Per-call time and
inference bounds with their own error classes, engine counters read as a
stats block, print output captured beside the answers, and rows crossing
into a DataFrame.
Guarantees:
  - capture collects print output without changing the run result shape
    [tested: test_example_runs_and_verifies_itself; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from _common import check, done

import petta
from petta import MeTTa, S, V, tables
from petta.errors import InferenceLimitError, TimeLimitError

m = MeTTa().space("&bounds-demo")

# A function that spins for as long as it is allowed to.
m.run("(= (spin $n) (if (== $n 0) done (spin (- $n 1))))")

try:
    m.run(
        "!(with-pragma! ((max-stack-depth 1000000000)) (spin 100000000))",
        timeout=0.05,
    )
    raise AssertionError("the time bound did not fire")
except TimeLimitError:
    check("a 50ms bound stops a spin that would run for minutes", True)

try:
    m.eval(
        "(with-pragma! ((max-stack-depth 1000000000)) (spin 100000000))",
        inferences=10_000,
    )
    raise AssertionError("the inference bound did not fire")
except InferenceLimitError:
    check("an inference bound is the deterministic twin", True)

tables.add(m, "edge", [(i, i + 1) for i in range(200)])
rows = m.query(S.edge(V.a, V.b), S.edge(V.b, V.c), timeout=30.0)
check("a generous bound changes nothing", len(rows), 199)

with m.stats() as s:
    list(m.query(S.edge(V.a, V.b), S.edge(V.b, V.c)))
check("the stats block counts the engine steps spent", s.inferences > 100)

with m.capture() as output:
    groups = m.run("!(println! (hello world)) !(+ 1 2)")
check("captured print output", "(hello world)" in output.text)
check("the answers still arrive beside it", groups[1], [3])

try:
    import polars  # noqa: F401

    check("rows cross into a polars frame", rows.to_pl().columns, ["a", "b", "c"])
except ImportError:
    print("  (polars is not installed; rows.table() is the plain dict)")

done("engine_controls")
