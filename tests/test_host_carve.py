"""Purpose: the engine's CODE names no host, permanently. Every host
reaches the engine through the declared seams (metta_host_builtin,
metta_host_import, metta_host_object, metta_form_rewriter, the grounded
type family, the error hooks), and every per-host line lives in that
host's own hosts/ bridge, so the next host cannot regress the property by
editing the engine.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import re
from pathlib import Path

import pytest

_HOST_TOKEN = re.compile(r"\bpy_|\bpython|\bjanus", re.IGNORECASE)


def _engine_sources():
    root = Path(__file__).resolve().parents[2]
    return sorted((root / "src").glob("*.pl"))


@pytest.mark.parametrize("source", _engine_sources(), ids=lambda p: p.name)
def test_no_code_in_the_engine_names_a_host(source):
    """A comment may explain a host; a code line may not name one.

    The word boundary is what keeps copy_term/2 out of the count, the
    measured inflation the first census had. The tokens are the Python
    host's whole vocabulary; a new host's vocabulary joins this scan in
    the commit that adds its bridge.
    """
    offenders = []
    for number, line in enumerate(source.read_text().splitlines(), 1):
        if line.lstrip().startswith("%"):
            continue
        if _HOST_TOKEN.search(line):
            offenders.append(f"{source.name}:{number}: {line.strip()[:80]}")
    assert not offenders, (
        "the engine's code names a host; move the line behind a seam into "
        "the host's own hosts/ bridge:\n" + "\n".join(offenders)
    )
