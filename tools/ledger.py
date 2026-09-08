"""Purpose: query door kinds and sugar contracts for the shrink ledger.

Guarantees: the ledger shares the door generator's contracts and rendering
  [tested: test_the_shrink_ledger_covers_every_derived_door,
  test_the_shrink_ledger_page_is_up_to_date; commit=WORKTREE].
Decides: a sugar is an explicit parameter point. Calls between public
  methods do not classify ownership, transactions, or query composition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from doorgen import ROOT, all_rows, contract_findings, ledger_page  # noqa: E402

PAGE = ROOT / "website/reference/shrink-ledger.md"


def main(argv: list[str]) -> int:
    """Check the row contracts and their ledger, or regenerate its page."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    arguments = parser.parse_args(argv)
    problems = contract_findings()
    rows = all_rows()
    rendered = ledger_page(rows)
    if not problems and arguments.write:
        PAGE.write_text(rendered, encoding="utf-8")
    elif not PAGE.is_file() or PAGE.read_text(encoding="utf-8") != rendered:
        problems.append("shrink ledger differs from door rows; run tools/doorgen.py --write")
    for problem in problems:
        print(problem)
    print(f"ledger: {len(problems)} findings over {len(rows)} door contracts")
    return int(bool(problems))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
