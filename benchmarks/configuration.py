"""Purpose: the measurement configuration every counter baseline depends on,
shared by the bench fixture, the instruction checker, and the extension-cost
gate so all three stamp and verify the same facts.
Guarantees:
  - artifact presence plus the env override decide, the same two inputs
    parser.pl's gate reads; a present-but-unloadable artifact is an engine
    defect the plt suite owns, not configuration drift. The C reader moved
    file-load 8704891 to 722264 with zero code change, and the C extension's
    shared objects gate a bench case (handle-round-trip skips without
    handle.so) and an extension-cost tier (the C row needs cbump.so), which
    is why a counter run must declare all of them
    [tested: test_baseline_stamps_and_verifies_counter_configuration].
"""  # noqa: D205  -- the API contract is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]


def counter_configuration() -> dict[str, bool]:
    """The live configuration a counter measurement runs in."""
    c_extension = _ROOT / "examples" / "integration" / "c_extension"
    return {
        "c_reader": (
            (_ROOT / "engine" / "reader.so").is_file()
            and os.environ.get("PETTA_C_READER") != "off"
        ),
        "c_extension": (
            (c_extension / "cbump.so").is_file()
            and (c_extension / "handle.so").is_file()
        ),
    }
