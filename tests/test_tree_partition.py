"""Purpose: the tree partitions by seam, and this test is the fence.
Guarantees:
  - engine/ names no seat: its only bindings/ mention is the decider glob,
    and no hosts/ path survives anywhere in it
    [tested: test_the_tree_partitions_by_seam]
  - the engine discovers the python seat through the glob, and the removed
    legacy python.petta alias stays removed
    [tested: test_the_tree_partitions_by_seam]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

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

    # Upstream's conftest imports python.petta, so this package-identity shim
    # is the one retained compatibility boundary.
    assert (REPO / "python" / "__init__.py").exists(), (
        "the upstream python.petta entry point is missing"
    )
