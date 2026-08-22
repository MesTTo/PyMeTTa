"""Purpose: one canonical TEXT form for an answer, so a recorded transcript
records the answer rather than the engine's variable counter.

Assumes:
  - a fresh variable prints as `$_` followed by digits, which is the engine's
    own spelling for a variable it invented [source: engine/metta.pl's writer;
    commit=WORKTREE]
Guarantees:
  - two alpha-equivalent printed answers canonicalize identically, and two
    variables never collapse into one [tested: test_alpha_text_canonicalizes_by_first_appearance]
Decides:
  - renaming is by FIRST APPEARANCE, not by sorting, because appearance order
    is stable under the engine's allocation order changing while a sort over
    the original names is not
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""  # noqa: D205  -- the module contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import re

#: A variable the engine invented, which it numbers from a per-process counter.
MACHINE_VARIABLE = re.compile(r"\$_\d+")


def canonical(text: str) -> str:
    """One printed answer, with machine variable names renamed in appearance order.

    Answer equivalence is ALPHA-equivalence by the law (`=alpha`, and the
    stdlib's own assertAlpha family), so a transcript recording `$_98110`
    records a fact about a counter rather than about an answer. Two measured
    instances, which is why this is one function rather than two: the
    differential oracle compares two CLI runs whose allocation histories differ
    by consult order, and the stdlib phrasebook froze `($_98110 $_98518)` and
    went red on a merge that changed no semantics at all, because the engine
    reached that point having invented ten fewer variables.
    """
    seen: dict[str, str] = {}
    return MACHINE_VARIABLE.sub(
        lambda hit: seen.setdefault(hit.group(0), f"$_v{len(seen)}"), text
    )
