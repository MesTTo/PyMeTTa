"""Purpose: the examples that came from another project stay credited.

This replaces a check that pinned a README lineage section naming the upstream
project as this repository's origin. That framing is withdrawn; what survives
it, and matters more, is the narrower obligation: 142 of the example programs
are other people's work, MIT licensed, and the directory has to say so.

The list is derived rather than remembered, so this asserts that the committed
manifest still describes the tree, that it credits per FILE rather than naming
only the most prolific contributor, and that the README states the split. When
the upstream checkout is absent the derivation cannot run, and the structural
checks still do.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MANIFEST = REPO / "examples" / "ORIGINS.tsv"
README = REPO / "examples" / "README.md"
TOOL = REPO / "extensions" / "python" / "tools" / "example_origins.py"


def _rows() -> list[list[str]]:
    return [
        line.split("\t")
        for line in MANIFEST.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]


def test_every_derived_example_names_its_source_and_its_authors():
    """Four fields a citation needs: ours, theirs, how much, and whose."""
    rows = _rows()
    assert rows, "the origins manifest lists nothing"
    for row in rows:
        assert len(row) == 4, f"{row[0] if row else row} is missing citation fields"
        ours, upstream, retained, authors = row
        assert (REPO / ours).exists(), f"{ours} is credited and not there"
        assert upstream.endswith(".metta"), upstream
        assert 0.0 < float(retained) <= 1.0, retained
        assert authors.strip(), f"{ours} credits nobody"


def test_the_credit_is_per_file_rather_than_one_name():
    """Naming only the most prolific contributor would miscredit the rest."""
    named = {name for row in _rows() for name in row[3].split("; ") if name}
    assert len(named) > 1, (
        f"every derived example credits {named}, which cannot be right: the "
        f"upstream examples have several authors and the manifest is supposed "
        f"to record each file's own"
    )


def test_the_examples_readme_states_the_split():
    """A reader of the directory learns what is theirs and what is ours."""
    text = README.read_text(encoding="utf-8")
    derived = len(_rows())
    total = len(list((REPO / "examples").rglob("*.metta")))
    assert "## Origins" in text, "the origins section is gone"
    section = text.split("## Origins", 1)[1]
    for required in (str(derived), str(total - derived), "MIT", "ORIGINS.tsv"):
        assert required in section, f"the origins section no longer states {required!r}"


def test_the_manifest_still_describes_the_tree():
    """Derived, not remembered: the tool recomputes and compares."""
    result = subprocess.run(  # this repository's own tool, on its own path
        [sys.executable, str(TOOL)],
        cwd=REPO, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
