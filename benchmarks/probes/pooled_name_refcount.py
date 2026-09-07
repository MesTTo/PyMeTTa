"""Purpose: show what a dropped space's leftover declaration refcounts do to the
next space that takes its pooled name, so the ops._forget_space hook is held to
the numbers that exposed the leak.
Assumes: `metta` imports (PYTHONPATH=extensions/python), numpy is installed and
  the engine boots; run as
  `python extensions/python/benchmarks/probes/pooled_name_refcount.py` from the
  repository root.
Guarantees: installs metta.arrays on a keeper space and on a second space,
  drops the second WITHOUT uninstalling, then installs on the next pooled
  space, and prints `dying=<n>`, `stale=<n>`, `reused=<bool>` and `new=<n>`:
  the atoms the dying space held, the refcount entries left under its name
  after the drop, whether the pool handed the same name out again, and the
  atoms the new life holds after its own install [measured 2026-09-07: at
  70ac99da, before ops._forget_space ran from Space.drop, stale=160 and new=37
  where a fresh name gets 197, the declaration adds skipped because the dead
  life's refcounts were still counted; on the tree that added the hook,
  stale=0 and new=197; extensions/python/metta/ops.py's _forget_space cites
  this probe; commit=f0c6cf586120cfac43229fbff7b7e4f320629cfd].
"""  # noqa: D205  -- the contract header is one continuous invariant, not summary-and-body prose

import numpy

from metta import MeTTa, arrays
from metta.ops import _DECLARATION_REFS


def main() -> None:
    """Print the four numbers."""
    with MeTTa() as m:
        keeper = m.space()
        arrays.install(keeper, default=numpy)
        dying = m.space()
        name = str(dying.name)
        arrays.install(dying, default=numpy)
        print(f"dying={len(dying.atoms())}")
        dying.drop()
        print(f"stale={len([key for key in _DECLARATION_REFS if key[0] == name])}")
        again = m.space()
        print(f"reused={str(again.name) == name}")
        arrays.install(again, default=numpy)
        print(f"new={len(again.atoms())}")


if __name__ == "__main__":
    main()
