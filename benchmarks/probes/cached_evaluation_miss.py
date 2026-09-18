"""Purpose: price one evaluation through the cached door on its first ask, its
second, and a new shape, which is what the translation cache's dependency
index costs at a miss and nothing at a hit.
Assumes: run as `python extensions/python/benchmarks/probes/cached_evaluation_miss.py`
  from the repository root, in a fresh process, since janus holds one Prolog
  VM per process and a warm image hides the first miss.
Guarantees: prints `miss=<n> hit=<m> new_shape=<k> run=<r>`, the inferences
  the engine spent on `answers` for `(if (or (and True False) True) 1 2)`
  asked twice, then for a second shape, then on the run door for the source
  form; the cache hit is the floor the miss is measured against
  [measured 2026-09-18: 69d1511c0 miss=1602 hit=332 new_shape=1549;
  5416e741d miss=2523 hit=332 new_shape=2470; the producer-written index
  miss=1530; command=python extensions/python/benchmarks/probes/cached_evaluation_miss.py;
  commit=WORKTREE].
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

import sys

sys.path.insert(0, "extensions/python")
import janus_swi

janus_swi.cmd("system", "set_prolog_flag", "file_search_cache_time", 9223372036854775807)
from metta import FALSE, TRUE, MeTTa, and_, if_, or_  # noqa: E402


def main() -> int:
    """Print the four costs on their own line."""
    m = MeTTa(metta_path=".").self
    with m.stats() as first:
        assert m.answers(if_(or_(and_(TRUE, FALSE), TRUE), 1, 2)) == [1]
    with m.stats() as second:
        assert m.answers(if_(or_(and_(TRUE, FALSE), TRUE), 1, 2)) == [1]
    with m.stats() as third:
        assert m.answers(if_(or_(and_(TRUE, TRUE), FALSE), 3, 4)) == [3]
    with m.stats() as ran:
        m.run("!(if (or (and True False) True) 1 2)")
    print(
        f"miss={first.inferences} hit={second.inferences} "
        f"new_shape={third.inferences} run={ran.inferences}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
