"""Purpose: the library's benchmark harness: where the time goes, measured,
so performance work argues from numbers. Each benchmark reports operations
per second as the best of three rounds (min wall per op), the shape the
sibling bench harness proved. Run: python bench.py [name ...]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import sys
import time
from typing import Callable

from petta import MeTTa, S, V, expr
from petta.atoms import Expr, Gnd, from_wire

ROUNDS = 3


def _rate(fn: Callable[[], int]) -> float:
    """Best ops/second over ROUNDS runs of fn, which returns its op count."""
    best = 0.0
    for _ in range(ROUNDS):
        start = time.perf_counter()
        count = fn()
        elapsed = time.perf_counter() - start
        best = max(best, count / elapsed)
    return best


BENCHES: dict[str, Callable[[MeTTa], float]] = {}


def bench(name: str):
    def apply(fn):
        BENCHES[name] = fn
        return fn

    return apply


@bench("add-single")
def add_single(m: MeTTa) -> float:
    with m.fresh_space() as s:
        return _rate(lambda: [s.add(S.n(i)) for i in range(2000)] and 2000)


@bench("add-batch")
def add_batch(m: MeTTa) -> float:
    with m.fresh_space() as s:
        return _rate(lambda: s.add(*(S.n(i) for i in range(2000))) or 2000)


@bench("query-2k-rows")
def query_rows(m: MeTTa) -> float:
    with m.fresh_space() as s:
        s.add(*(S.edge(i, i + 1) for i in range(2000)))
        return _rate(lambda: len(s.query(S.edge(V.a, V.b))))


@bench("eval-arith")
def eval_arith(m: MeTTa) -> float:
    return _rate(lambda: [m.eval(expr(S["+"], i, 1)) for i in range(2000)] and 2000)


@bench("op-raw")
def op_raw(m: MeTTa) -> float:
    @m.op(name="bench-raw", raw=True, typed=False)
    def bench_raw(a, b):
        return a + b

    return _rate(lambda: [m.eval(expr(S["bench-raw"], i, 1)) for i in range(2000)] and 2000)


@bench("op-encoded")
def op_encoded(m: MeTTa) -> float:
    @m.op(name="bench-enc", typed=False)
    def bench_enc(a, b):
        return a + b

    return _rate(lambda: [m.eval(expr(S["bench-enc"], i, 1)) for i in range(2000)] and 2000)


@bench("loop-1m")
def loop_million(m: MeTTa) -> float:
    m.run("(= (bench-cd $n) (if (> $n 0) (bench-cd (- $n 1)) done))")
    return _rate(lambda: m.run("!(bench-cd 1000000)") and 1_000_000)


@bench("wire-codec")
def wire_codec(m: MeTTa) -> float:
    atom = expr(S.deep, *[expr(S.node, i, Gnd(float(i)), S.leaf) for i in range(50)])

    def round_trips() -> int:
        for _ in range(2000):
            from_wire(atom.to_wire())
        return 2000 * 152  # atoms per trip, both directions

    return _rate(round_trips)


@bench("run-source")
def run_source(m: MeTTa) -> float:
    return _rate(lambda: [m.run("!(+ 1 2)") for _ in range(1000)] and 1000)


def main(argv: list[str]) -> None:
    chosen = argv or sorted(BENCHES)
    m = MeTTa()
    width = max(len(n) for n in chosen)
    for name in chosen:
        rate = BENCHES[name](m)
        print(f"{name:<{width}}  {rate:>12,.0f} /s")


if __name__ == "__main__":
    main(sys.argv[1:])
