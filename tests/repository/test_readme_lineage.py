"""Purpose: pin Phase 9 item P9.4: the README records the fork
relationship, so a reader landing on either repository learns whose engine
this is, where the canonical home is, and what this branch adds.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

from pathlib import Path

README = Path(__file__).resolve().parents[4] / "README.md"


def test_the_readme_records_the_fork_relationship():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    text = README.read_text(encoding="utf-8")
    assert "### Lineage" in text, "the lineage section is gone"
    section = text.split("### Lineage", 1)[1].split("###", 1)[0]
    for required in (
        "Patrick Hammer",
        "github.com/trueagi-io/PeTTa",
        "github.com/patham9/PeTTa",
        "`python-library` branch",
        "upstream contract",
    ):
        assert required in section, f"the lineage section no longer states {required!r}"
