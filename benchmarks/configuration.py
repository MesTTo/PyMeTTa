"""Purpose: the measurement configuration every counter baseline depends on,
shared by the bench fixture, the instruction checker, and the extension-cost
gate so all three stamp and verify the same facts.
Guarantees:
  - artifact presence plus the env override decide, the same two inputs
    parser.pl's gates read; a present-but-unloadable artifact is an engine
    defect the plt suite owns, not configuration drift. The C reader moved
    file-load 8704891 to 722264 with zero code change, the C writer moved
    space-digest 1400321 to 920299 the same way, and the C extension's
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
    c_extension = _ROOT / "examples" / "ch19-spaces-backed-by-anything" / "19-03-a-builtin-in-c"
    return {
        "c_reader": (
            (_ROOT / "engine" / "reader.so").is_file()
            and os.environ.get("METTA_C_READER") != "off"
        ),
        "c_writer": (
            (_ROOT / "engine" / "writer.so").is_file()
            and os.environ.get("METTA_C_WRITER") != "off"
        ),
        # json-wire reads 178,013 inferences with engine/json_codec.so present
        # and 169,336,779 without, so a baseline measured in one configuration
        # is unreadable in the other; the stamp is what makes a pin refuse to
        # compare across that line. Added at the json-c merge, which is where
        # the artifact joined the tree and where its own worker filed the gap.
        "c_json": (
            (_ROOT / "engine" / "json_codec.so").is_file()
            and os.environ.get("METTA_C_JSON") != "off"
        ),
        "c_extension": (
            (c_extension / "cbump.so").is_file()
            and (c_extension / "handle.so").is_file()
        ),
    }
