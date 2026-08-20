"""Purpose: the tree partitions by seam, and this test is the fence.
Guarantees:
  - engine/ names no seat: its only bindings/ mention is the decider glob,
    and no hosts/ path survives anywhere in it
    [tested: test_the_tree_partitions_by_seam]
  - the engine discovers the python seat through the glob, and the legacy
    python.petta alias still resolves to the canonical package
    [tested: test_the_tree_partitions_by_seam]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import importlib
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

DECIDER_GLOB = "'../bindings/*/decider.pl'"


def test_the_tree_partitions_by_seam():
    """The folder boundary states what a grep used to.

    The partition stages the recorded end form, a kernel repository with
    satellite seats, so nothing in engine/ may name a seat: the one
    allowed bindings/ mention is the decider glob the engine reaches
    seats through, and hosts/ is gone entirely.
    """
    # CODE lines only: a comment may cite a seat test as evidence (the
    # evidence lane verifies those names), but no directive or clause may
    # reach for a seat PATH, the one decider glob excepted. The negative
    # lookbehind keeps a predicate like canonical_specialization_bindings/2
    # out of it: a path mention starts a word, an arity slash ends one.
    seat_path = re.compile(r"(?<![\w])(bindings|hosts)/")
    offenders = []
    for source in sorted((REPO / "engine").iterdir()):
        if not source.is_file():
            continue
        comment_lead = ";" if source.suffix == ".metta" else "%"
        for lineno, line in enumerate(source.read_text().splitlines(), 1):
            code = line.split(comment_lead, 1)[0]
            if seat_path.search(code) and DECIDER_GLOB not in code:
                offenders.append(f"engine/{source.name}:{lineno}: {line.strip()}")
    assert not offenders, "engine/ names a seat:\n" + "\n".join(offenders)

    assert not (REPO / "hosts").exists(), "hosts/ dissolved into bindings/"

    deciders = sorted(
        p.relative_to(REPO).as_posix() for p in (REPO / "bindings").glob("*/decider.pl")
    )
    assert "bindings/python/decider.pl" in deciders

    legacy = importlib.import_module("python.petta")
    import petta

    assert legacy is petta

    # The compat shim points one way: the seat never imports the legacy
    # package. Asserted over source rather than import-linter because the
    # imports lane runs inside the seat, where the repo-root shim is not
    # importable and a linter contract on it would silently lose its teeth.
    one_way = []
    for source in sorted((REPO / "bindings" / "python" / "petta").rglob("*.py")):
        for lineno, line in enumerate(source.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith(("import python", "from python")):
                one_way.append(
                    f"{source.relative_to(REPO)}:{lineno}: {stripped}"
                )
    assert not one_way, "the seat imports the shim:\n" + "\n".join(one_way)
