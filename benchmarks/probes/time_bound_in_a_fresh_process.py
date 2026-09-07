"""Purpose: show that a caller's wall-clock bound RAISES in a fresh engine
process, round after round, so the intermittent that the shared test process
produces (`(Error (spin) StackOverflow)` returned as an ANSWER after 2,670
tests have grown the loop) is placed on the shared process and not on the door.
Assumes: `metta` imports (PYTHONPATH=extensions/python) and the engine boots;
  run as `python extensions/python/benchmarks/probes/time_bound_in_a_fresh_process.py`
  from the repository root; the spin program is written under `ai-tmp/probes/`.
Guarantees: asks the same two doors twelve times in one fresh process, an
  inference bound (`inferences=20_000`) and a time bound (`timeout=0.3`), over
  a program that never returns, and prints per round what each answered and
  how long it took [measured 2026-09-07: TimeLimitError twelve times out of
  twelve at 0.301s to 0.307s, and InferenceLimitError twelve times out of
  twelve, where the same time bound inside the whole-suite process ran 66.170
  seconds and came back as an answer; extensions/python/tests/ch18_performance/
  test_bounds.py cites this probe; commit=11afdcdbad5bbbe37168b5d8528c23a21c42b4b6].
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "extensions" / "python"))

import metta  # noqa: E402
from metta.errors import InferenceLimitError, TimeLimitError  # noqa: E402

SPIN = REPO / "ai-tmp" / "probes" / "time-bound-forever.metta"


def main() -> int:
    """Twelve rounds of the two bounds over a program that never returns."""
    SPIN.parent.mkdir(parents=True, exist_ok=True)
    SPIN.write_text(
        "(= (spin) (spin))\n"
        "!(with-pragma! ((max-stack-depth 300000000)) (spin))\n",
        encoding="utf-8",
    )
    m = metta.MeTTa()
    for round_number in range(1, 13):
        started = time.monotonic()
        try:
            answers = m.load(SPIN, inferences=20_000)
            budget = f"RETURNED {str(answers)[:60]}"
        except InferenceLimitError:
            budget = "InferenceLimitError"
        inference_wall = time.monotonic() - started

        started = time.monotonic()
        try:
            answers = m.load(SPIN, timeout=0.3)
            timed = f"RETURNED {str(answers)[:60]}"
        except TimeLimitError:
            timed = "TimeLimitError"
        timed_wall = time.monotonic() - started
        print(
            f"round {round_number:2}: inferences={budget} ({inference_wall:.3f}s)  "
            f"timeout={timed} ({timed_wall:.3f}s)"
        )
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
