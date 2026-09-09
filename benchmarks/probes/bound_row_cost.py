"""Purpose: measure what it costs to hold a policy bound as a `(limit ...)`
row rather than a module constant, on both sides of the trade -- the reader,
which is a cursor asking for its chunk cap when it opens, and the writer, which
is every `&metta` write the catalog's watch point now passes through.

The A/B is the same tree twice: `Config.chunk_cap` patched to a constant is
exactly the shape the bound had before it became a row, so the difference is
the row and nothing else. Wall clock is reported beside the inference counts
because the crossing the mirror removes is 1.4 microseconds of floor that no
cheaper goal reaches, and the inference counter cannot see it.

Assumes:
  - it runs from the repository root with `extensions/python` importable, and
    a loaded box: inferences are the verdict and the wall figures are minima
    over five runs of 20,000 operations, interleaved arm by arm
Guarantees:
  - `--read` reports inferences and microseconds per one-answer `match` with
    the bound as a row and as a constant, and they agree
    [measured 2026-09-08: 24.0 against 24.0 inferences, and 33.5 and 35.5
    microseconds against 33.7 and 34.6 over two runs, where consulting the
    catalog per read instead measured 45.1 inferences and 42.0 microseconds;
    command=python extensions/python/benchmarks/probes/bound_row_cost.py --read;
    fixture=a 50-atom space, 20,000 matches per arm, minimum of five]
  - `--write` reports inferences per write on the space the point watches and
    on one it does not, so the price of the watch is visible where it lands
    [measured 2026-09-08: 37.02 per `&metta` write against a control
    checkout's 36.02, and 27.02 either way per `&self` write;
    command=python extensions/python/benchmarks/probes/bound_row_cost.py --write;
    fixture=300 writes per arm]
  - `--subscription` reports what the same mirror costs when it is kept in
    step by a standing `&metta` subscription instead, which is the option the
    watch point replaced: one `seam:atom_added/2` clause wraps the write door
    for every space in the process
    [measured 2026-09-08: with a `(limit $n $v)` subscription standing, 70.03
    against 37.02 inferences per non-matching `&metta` write and 43.02
    against 27.02 per `&self` write;
    command=python extensions/python/benchmarks/probes/bound_row_cost.py --subscription;
    fixture=200 writes per arm, both arms in one process]
Fails when: run without a working janus; it needs the engine.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import metta
import metta._catalog.bounds as config_module
from metta import MeTTa, S, V

#: What the constant was before the bound became a row [source:
#: extensions/python/metta/_catalog/bounds.py:206, _DEFAULTS; commit=cd62330ceacc8f1254eed9791c3f6203b48a1c9e].
SHIPPED_CHUNK_CAP = 64


def _inferences(context, work, repeats: int = 3, rounds: int = 200) -> float:
    """Inferences per operation, the minimum of `repeats` counted rounds."""
    work()
    counts = []
    for _ in range(repeats):
        with context.stats() as spent:
            for _ in range(rounds):
                work()
        counts.append(spent.inferences)
    return min(counts) / rounds


def _microseconds(work, rounds: int = 20_000, repeats: int = 5) -> float:
    """Microseconds per operation, the minimum of `repeats` timed rounds."""
    for _ in range(rounds // 10):
        work()
    best = None
    for _ in range(repeats):
        started = time.perf_counter()
        for _ in range(rounds):
            work()
        spent = time.perf_counter() - started
        best = spent if best is None else min(best, spent)
    return best * 1e6 / rounds


def _as_a_constant():
    """Patch the bound back to the module constant it used to be.

    Returns what to restore. This is the B arm: the property answers without
    reading the mirror, the catalog or anything else, which is what the code
    did before the bounds became rows.
    """
    held = config_module.Config.chunk_cap
    config_module.Config.chunk_cap = property(lambda _self: SHIPPED_CHUNK_CAP)
    return held


def read() -> None:
    """What a one-answer `match` costs with the bound as a row and as a constant."""
    with MeTTa() as m:
        space = m.self
        for n in range(50):
            space.add(S.n(n))
        one = S.n(0)

        def match_one():
            next(iter(space.match(one)))

        row_inferences = _inferences(m, match_one)
        row_wall = _microseconds(match_one)
        held = _as_a_constant()
        try:
            constant_inferences = _inferences(m, match_one)
            constant_wall = _microseconds(match_one)
        finally:
            config_module.Config.chunk_cap = held

        print(f"{'arm':>10} {'inferences':>12} {'microseconds':>14}")
        print(f"{'row':>10} {row_inferences:12.1f} {row_wall:14.2f}")
        print(f"{'constant':>10} {constant_inferences:12.1f} {constant_wall:14.2f}")
        print(
            "delta "
            f"{row_inferences - constant_inferences:+.1f} inferences, "
            f"{row_wall - constant_wall:+.2f} microseconds"
        )


def write() -> None:
    """What the catalog's watch point costs the writers it passes through."""
    with MeTTa() as m:
        written = [0]

        def catalog_write():
            written[0] += 1
            metta.catalog.add(S["probe-row"](S[f"n{written[0]}"]))

        def self_write():
            written[0] += 1
            m.self.add(S.n(written[0]))

        def equation_write():
            written[0] += 1
            m.self.run(f"(= (probe{written[0]} $x) $x)")

        print(f"{'write':>12} {'inferences':>12}")
        print(f"{'&metta':>12} {_inferences(m, catalog_write, rounds=300):12.2f}")
        print(f"{'&self':>12} {_inferences(m, self_write, rounds=300):12.2f}")
        print(f"{'equation':>12} {_inferences(m, equation_write, rounds=100):12.2f}")


def _one_subscription_arm(*, standing: bool) -> None:
    """One arm of the subscription comparison, printed."""
    with MeTTa() as m:
        written = [0]
        if standing:
            metta.catalog.subscribe(
                S.limit(V.name, V.value), lambda _event: None, on="both"
            )

        def catalog_write():
            written[0] += 1
            metta.catalog.add(S["probe-row"](S[f"n{written[0]}"]))

        def self_write():
            written[0] += 1
            m.self.add(S.n(written[0]))

        label = "subscribed" if standing else "plain"
        catalog = _inferences(m, catalog_write, rounds=200)
        own = _inferences(m, self_write, rounds=200)
        print(f"{label:>12} &metta {catalog:8.2f}   &self {own:8.2f}")


def subscription() -> None:
    """What the rejected option cost: a standing subscription on `&metta`.

    A subscription installs a `seam:atom_added/2` clause, and one such clause
    wraps the write door for every space in the process, so the cost lands on
    writes that have nothing to do with the bounds. Both arms run in one
    process, the second with the subscription standing, so the difference is
    the subscription and not the box.
    """
    _one_subscription_arm(standing=False)
    _one_subscription_arm(standing=True)


def bounds() -> None:
    """That the row is still the source: a program's own write reaches the read."""
    with MeTTa() as m:
        print("shipped   ", metta.config.chunk_cap)
        m.self.run("!(add-atom &metta (limit chunk-cap 8))")
        print("overridden", metta.config.chunk_cap)
        m.self.run("!(remove-atom &metta (limit chunk-cap 8))")
        print("restored  ", metta.config.chunk_cap)
        rows = {
            str(answer.name): answer.value.value
            for answer in metta.catalog.match(S.limit(V.name, V.value))
        }
        print("rows      ", dict(sorted(rows.items())))


def main() -> int:
    """Run whichever measurement was asked for."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--read", action="store_true", help="the reader's side")
    parser.add_argument("--write", action="store_true", help="the writer's side")
    parser.add_argument(
        "--subscription", action="store_true", help="the option the point replaced"
    )
    parser.add_argument("--bounds", action="store_true", help="the rows themselves")
    asked = parser.parse_args()
    if asked.read or not (asked.write or asked.bounds or asked.subscription):
        read()
    if asked.write:
        write()
    if asked.subscription:
        subscription()
    if asked.bounds:
        bounds()
    return 0


if __name__ == "__main__":
    sys.exit(main())
