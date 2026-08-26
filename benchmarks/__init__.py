"""Purpose: hold the calibrated Python benchmark suite and its workloads.

Guarantees:
  - `atomic_json` replaces a document or leaves the old one intact, so an
    interrupted run cannot leave a half-written pin behind for the next run to
    compare against
    [tested: test_atomic_json_keeps_the_previous_document_when_a_write_fails;
    commit=906a4057ac57a340a3544ad909e829f851f35af3].
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def atomic_json(path: Path, document: Mapping[str, Any]) -> None:
    """Write `document` to `path` through a temporary file and one rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(document, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
