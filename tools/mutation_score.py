"""Purpose: print the mutation run's verdict as one line the gate log can hold.

`mutmut run` reports its tally by rewriting a single terminal line, so a
captured log carries several hundred half-drawn copies of it and no final
answer. mutmut's own `export-cicd-stats` writes the same counts as JSON; this
reads that file and says what they mean.

Assumes: `mutmut export-cicd-stats` has written its document, which it does
    into `mutants/mutmut-cicd-stats.json` beside the run.
Decides: the score is over the mutants a test actually REACHED, which is
    killed + survived + timed out. `total` in mutmut's document counts every
    mutant in the package, including the ones this run did not select, so
    dividing by it would report the fraction of the library covered rather than
    the quality of the tests; the mutants no test reaches are printed beside the
    score instead of being folded into it.
Fails when: the document is absent or unreadable, which it says and exits 2 for,
    because a mutation lane that prints nothing looks the same as one that found
    nothing wrong.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    """Read mutmut's stats document and print one verdict line."""
    if len(sys.argv) != 3:
        print("usage: mutation_score.py <mutmut-cicd-stats.json> <target>", file=sys.stderr)
        return 2
    document, target = Path(sys.argv[1]), sys.argv[2]
    try:
        counts = json.loads(document.read_text(encoding="utf-8"))
    except (OSError, ValueError) as unreadable:
        print(f"mutation: no verdict, {document} is {unreadable}", file=sys.stderr)
        return 2
    killed = counts["killed"]
    survived = counts["survived"]
    timed_out = counts["timeout"]
    unreached = counts["no_tests"]
    reached = killed + survived + timed_out
    score = f"{100 * killed / reached:.1f}%" if reached else "no score"
    print(
        f"mutation {target}: {score} of {reached} reached mutants killed "
        f"({killed} killed, {survived} survived, {timed_out} timed out); "
        f"{unreached} more are executed by no test"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
