"""Purpose: price what the executor adds per conjunctive match beside a single
pattern match, as the minimum of five runs, so a change to the admission gate
is held to the benchmark harness's four-inference allowance.
Assumes: `metta` imports (PYTHONPATH=extensions/python) and the engine boots;
  run as `python extensions/python/benchmarks/probes/conjunction_frame_cost.py`
  from the repository root.
Guarantees: prints `chain=<n>` and `single=<n>`, the inferences of a
  two-conjunct chain match and of a one-pattern match over a 64-edge chain,
  each the minimum of five runs after one warm-up [measured 2026-09-07: one
  extra frame on the conjunctive path is +1 inference, five over the harness's
  allowance on direct-join's five repeats, which is why both call sites read
  cyclic_join_planning_enabled/0 themselves; engine/spaces/generic_join.pl's
  shape predicate cites this probe; commit=a05f6d22e483826ef023fdf350f6533581258f9c].
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from metta import MeTTa


def rows(n):
    """The program that stores an n-edge chain."""
    return "\n".join(f"!(add-atom &self (edge {i} {i + 1}))" for i in range(n))


CHAIN = "!(match &self (, (edge $x $y) (edge $y $z)) (pair $x $z))"
ONE = "!(match &self (edge $x $y) (pair $x $y))"


def main() -> None:
    """Print the two prices, minimum of five."""
    with MeTTa() as m, m.space() as space:
        space.run(rows(64))
        for label, q in (("chain", CHAIN), ("single", ONE)):
            space.run(q)
            best = None
            for _ in range(5):
                with space.stats() as s:
                    space.run(q)
                best = int(s.inferences) if best is None else min(best, int(s.inferences))
            print(f"{label}={best}")


if __name__ == "__main__":
    main()
