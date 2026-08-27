"""Purpose: the tree partitions by seam, and this test is the fence.
Guarantees:
  - engine/ names no seat: its only extensions/ mention is the control-file
    glob, and no `bindings`, `backends` or `hosts` path survives anywhere in it
    [tested: test_the_tree_partitions_by_seam]
  - the engine discovers the python seat through the glob, the merged
    extensions/ folder is the only seat root, and the removed legacy root
    python package stays removed
    [tested: test_the_tree_partitions_by_seam]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]

CONTROL_GLOB = "'../extensions/*/extension.pl'"


def test_the_tree_partitions_by_seam():
    """The folder boundary states what a grep used to.

    The partition stages the recorded end form, a kernel repository with
    satellite seats, so nothing in engine/ may name a seat: the one
    allowed extensions/ mention is the control-file glob the engine reaches
    seats through. The `bindings`, `backends` and `hosts` roots are gone, the
    first two merged into extensions/ because who DRIVES the engine and what
    the engine CONSULTS are two roles a seat holds rather than two kinds of
    folder.
    """
    # CODE lines only: a comment may cite a seat test as evidence (the
    # evidence lane verifies those names), but no directive or clause may
    # reach for a seat PATH, the one control-file glob excepted. The negative
    # lookbehind keeps a predicate like canonical_specialization_bindings/2
    # out of it: a path mention starts a word, an arity slash ends one.
    seat_path = re.compile(r"(?<![\w])(extensions|bindings|backends|hosts)/")
    offenders = []
    # Sources only: engine/reader.so is a built artifact beside its .c and
    # has no lines to hold to the rule.
    for source in sorted((REPO / "engine").iterdir()):
        if not source.is_file() or source.suffix not in {".pl", ".metta", ".c"}:
            continue
        comment_lead = ";" if source.suffix == ".metta" else "%"
        for lineno, line in enumerate(source.read_text().splitlines(), 1):
            code = line.split(comment_lead, 1)[0]
            if seat_path.search(code) and CONTROL_GLOB not in code:
                offenders.append(f"engine/{source.name}:{lineno}: {line.strip()}")
    assert not offenders, "engine/ names a seat:\n" + "\n".join(offenders)

    assert not (REPO / "hosts").exists(), "hosts/ dissolved into the seat root"
    for merged in ("bindings", "backends"):
        assert not (REPO / merged).exists(), f"{merged}/ merged into extensions/"

    controls = sorted(
        p.relative_to(REPO).as_posix() for p in (REPO / "extensions").glob("*/extension.pl")
    )
    # Both roles, in one folder: the seat the engine CONSULTS and the seat that
    # DRIVES it are found by the same glob and told apart by their entry/2 rows.
    assert "extensions/python/extension.pl" in controls
    assert "extensions/mork/extension.pl" in controls

    assert not (REPO / "python" / "__init__.py").exists(), (
        "the retired root python package still exists"
    )
