"""Purpose: pin the repo-side residue of a specification correction. The
seam specification's normative `&sqlite` demonstration said the diagonal
shape `(edge $x $x)` is handled at `Sound` fidelity; the shipped demo
declares `Exact` and PROVES it by deriving `WHERE a = b` from the repeated
variable, so the specification under-claimed its own backend and was
corrected to `Exact` [P9.2, 2026-08-19]. This keeps the demo declaring
what it proves, so the correction cannot silently un-happen from the
code side.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import re
from pathlib import Path

DEMO = (
    Path(__file__).resolve().parents[3]
    / "bindings" / "python" / "examples" / "integration" / "sqlite_space.py"
)


def test_the_sqlite_demo_declares_exact_on_the_diagonal():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    text = DEMO.read_text(encoding="utf-8")
    diagonal = re.search(
        r'declare_handles\(name,\s*"\(edge \$x \$x\)",\s*"(\w+)"\)', text
    )
    assert diagonal, "the diagonal declaration is gone from the sqlite demo"
    assert diagonal.group(1) == "Exact", (
        f"the diagonal is declared {diagonal.group(1)}; the demo derives "
        "WHERE a = b from the repeated variable, which is exact filtering"
    )
    assert 'check("the diagonal derives WHERE a = b"' in text, (
        "the proof that the diagonal is exact has been removed"
    )
