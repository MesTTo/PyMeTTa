"""Purpose: price soft-match under both spellings of soft-fold's name parameter.

The declared `Symbol` is what the name actually is; `%Undefined%` is the
metatype spelling that reaches the typing-rule registry. lib_soft's own comment
cites the ratio between them, so this DERIVES that ratio rather than leaving it
to be remembered: a quotient in a comment outlives the mechanism that produced
it, and the one this replaces no longer reproduced.

Guarantees:
  - both arms are measured in one run, from a checkout, with no absolute path
  - each arm gets a fresh space, so a compiled clause from one spelling cannot
    price the other
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import os
import sys
from pathlib import Path

#: The checkout, derived rather than written: a tracked file may not cite an
#: absolute workspace path, and the ai-tmp probe this replaces did.
ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(ROOT / "extensions" / "python"))
os.environ["METTA_PATH"] = str(ROOT)

from metta import Space  # noqa: E402  -- the path above has to be set first

#: Enough candidates that per-candidate cost dominates the fixed setup.
CANDIDATES = 400
SHIPPED = "(-> Symbol Atom Atom Number)"
METATYPE = "(-> %Undefined% Atom Atom Number)"
PATTERNS = (
    ("mismatch at position 0", "(hates $a $b $c $d $e $f)"),
    ("match at position 0", "(adores $a $b $c $d $e $f)"),
)


def arm(declaration: str) -> dict[str, int]:
    """Inference counts for one declaration of soft-fold's name parameter."""
    space = Space(metta_path=str(ROOT))
    space.run("!(import! &self (library lib_measure))")
    space.run("!(import! &self (library lib_soft))")
    if declaration != SHIPPED:
        space.run(f"!(remove-atom &self (: soft-fold {SHIPPED}))")
        space.run(f"!(add-atom &self (: soft-fold {declaration}))")
    space.run("(similar likes adores 0.9)")
    for index in range(CANDIDATES):
        space.run(f"!(add-atom &big (likes s{index} fish and more and more))")

    counts: dict[str, int] = {}
    for label, pattern in PATTERNS:
        # Twice, because the first run pays a compile the second does not.
        for _ in range(2):
            with space.stats() as stats:
                space.run(
                    f"!(size-atom (collapse (soft-match &big {pattern} 0.5)))"
                )
            counts[label] = stats.inferences
    return counts


def main() -> int:
    """Print both arms and the tax the metatype spelling carries."""
    shipped, metatype = arm(SHIPPED), arm(METATYPE)
    for label, _ in PATTERNS:
        tax = metatype[label] / shipped[label]
        print(
            f"  {label:24} Symbol {shipped[label]:>9,}"
            f"   %Undefined% {metatype[label]:>9,}   tax {tax:.2f}x",
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
