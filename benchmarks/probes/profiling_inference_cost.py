"""Purpose: show that profiling a program retires inferences of its own, so the
memo advisor measures each configuration twice, once under stats() for the
count and once under the profiler for the per-head counts, and never reads a
count from a profiled run.
Assumes: `metta` imports (PYTHONPATH=extensions/python) and the engine boots;
  run as `python extensions/python/benchmarks/probes/profiling_inference_cost.py`
  from the repository root.
Guarantees: prints the plain and the profiled inference counts of `!(twice 18)`
  over a naive fib, three fresh engines each [measured 2026-09-07: 20,538 plain
  against 145,284 profiled; extensions/python/benchmarks/memo_advisor.py's
  worker cites this probe; commit=WORKTREE].
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from metta import MeTTa

PROGRAM = (
    "(= (fib $n) (if (< $n 2) $n (+ (fib (- $n 1)) (fib (- $n 2)))))\n"
    "(= (twice $n) (+ (fib $n) (fib $n)))\n"
)


def plain() -> int:
    """Inferences of the run under stats() alone."""
    with MeTTa() as m:
        m.self.run(PROGRAM)
        with m.self.stats() as s:
            m.self.run("!(twice 18)")
        return int(s.inferences)


def profiled() -> int:
    """Inferences of the same run under the profiler."""
    with MeTTa() as m:
        m.self.run(PROGRAM)
        with m.self.stats() as s:
            m.self.profile("!(twice 18)")
        return int(s.inferences)


def main() -> None:
    """Print three readings of each."""
    print("plain   :", [plain() for _ in range(3)])
    print("profiled:", [profiled() for _ in range(3)])


if __name__ == "__main__":
    main()
