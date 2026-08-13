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
from petta.atoms import Gnd, from_wire

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


@bench("term-operators")
def term_operators(m: MeTTa) -> float:
    def build() -> int:
        for i in range(20000):
            (V.age >= i) & (V.age <= i + 10) | ~V.retired
        return 20000

    return _rate(build)


@bench("query-where")
def query_where(m: MeTTa) -> float:
    with m.fresh_space() as s:
        s.add(*(S.person(S[f"p{i}"], i % 90) for i in range(2000)))
        guard = (V.age >= 18) & (V.age <= 40)
        return _rate(
            lambda: len(s.query(S.person(V.name, V.age), where=guard))
        )


@bench("prepared-vs-query")
def prepared_vs_query(m: MeTTa) -> float:
    """The prepared ladder: solves/second on a wired two-pattern join;
    compare against query-2k-rows for the wiring cost saved."""
    with m.fresh_space() as s:
        s.add(*(S.edge(i, i + 1) for i in range(500)))
        hop = s.prepare(S.edge(V.a, V.b), S.edge(V.b, V.c))
        return _rate(lambda: [hop.solve() for _ in range(20)] and 20)


@bench("query-bounded")
def query_bounded(m: MeTTa) -> float:
    """The guarded crossing: a generous timeout+inference bound on the
    same query as query-where's shape; the gap against an unbounded run
    is the guard's whole cost (measured 4.5% at adoption)."""
    with m.fresh_space() as s:
        s.add(*(S.edge(i, i + 1) for i in range(2000)))
        return _rate(
            lambda: len(
                s.query(S.edge(V.a, V.b), limit=50, timeout=30.0, inferences=50_000_000)
            )
        )


@bench("add-table-rows")
def add_table_rows(m: MeTTa) -> float:
    rows = [(i, i + 1) for i in range(2000)]

    def load() -> int:
        with m.fresh_space() as s:
            s.add_table("edge", rows)
        return 2000

    return _rate(load)


@bench("weighted-relation")
def weighted_relation_rate(m: MeTTa) -> float:
    from petta import measure

    with m.fresh_space() as s:
        measure.install(s)
        measure.weighted_relation(
            s, "bench-mood", lambda day: [0.25, 0.75], [S.calm, S.tense]
        )
        return _rate(
            lambda: [
                s.run("!(ws-best (collapse (bench-mood today)))")
                for _ in range(500)
            ]
            and 500
        )


@bench("register-op")
def register_op(m: MeTTa) -> float:
    """Registrations/second, declarations and reflection facts included."""

    def register_batch() -> int:
        for i in range(100):
            def fn(x: int) -> int:
                return x

            m.op(fn, name=f"bench-reg-{i}")
            m.unregister(f"bench-reg-{i}")
        return 100

    return _rate(register_batch)


@bench("subscribe-tax")
def subscribe_tax(m: MeTTa) -> float:
    """Adds/second WITH a live subscription elsewhere: the price every
    space write pays for the dispatch hook once any subscription exists,
    to compare against add-batch."""
    with m.fresh_space() as other, m.fresh_space() as s:
        subscription = other.subscribe(S.never(V.x))
        try:
            return _rate(lambda: s.add(*(S.n(i) for i in range(2000))) or 2000)
        finally:
            subscription.cancel()


@bench("save-load-fast-vs-metta")
def save_load_fast_vs_metta(m: MeTTa) -> float:
    """Compare real public save and load paths over 20,001 stored atoms.

    The detail line reports both atom rates and their ratio. The returned
    rate is the fast path so the common harness can print it too. On the
    adoption run, fast measured 556,498 atoms/s against text's 53,564,
    a 10.389x speedup on this workload.
    """
    import tempfile
    from pathlib import Path

    atom_count = 20_001
    with (
        tempfile.TemporaryDirectory(prefix="petta-fast-io-") as directory,
        m.fresh_space() as source,
        m.fresh_space() as target,
    ):
        source.add(*(S["bench-save-node"](i, i + 1) for i in range(20_000)))
        source.run("(= (bench-save-next $x) (+ $x 1))")

        def measure(format: str) -> float:
            path = Path(directory) / f"roundtrip.{format}"
            best = 0.0
            for _ in range(ROUNDS):
                target.clear()
                start = time.perf_counter()
                saved = source.save(path, format=format)
                groups = target.load(path)
                elapsed = time.perf_counter() - start
                if saved != atom_count or groups or target.count() != atom_count:
                    raise RuntimeError(
                        f"{format} benchmark did not round-trip {atom_count} atoms"
                    )
                if target.run("!(bench-save-next 41)") != [[42]]:
                    raise RuntimeError(f"{format} benchmark lost its equation")
                best = max(best, atom_count / elapsed)
            return best

        text_rate = measure("metta")
        fast_rate = measure("fast")
        print(
            f"save-load-fast-vs-metta detail: metta={text_rate:,.0f} atoms/s "
            f"fast={fast_rate:,.0f} atoms/s speedup={fast_rate / text_rate:.3f}x"
        )
        return fast_rate


def main(argv: list[str]) -> None:
    chosen = argv or sorted(BENCHES)
    m = MeTTa()
    width = max(len(n) for n in chosen)
    for name in chosen:
        rate = BENCHES[name](m)
        print(f"{name:<{width}}  {rate:>12,.0f} /s")


if __name__ == "__main__":
    main(sys.argv[1:])
