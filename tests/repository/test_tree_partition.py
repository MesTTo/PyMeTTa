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


# The contract files the `metta` CLI's own header names: build.sh, check.sh,
# run.sh, test.sh, bench.sh. A component is a directory carrying at least one of
# them, which is the same rule check.sh's discovery loop, build.sh's and the CLI's
# components() all apply.
COMPONENTS = ("engine", *(f"extensions/{seat}" for seat in ("python", "node", "cmetta", "mork")))


def _components() -> list[Path]:
    return [REPO / name for name in COMPONENTS if (REPO / name).is_dir()]


def test_the_component_list_is_not_empty():
    """A path list that stopped resolving would make the checks below vacuous."""
    assert len(_components()) >= 4


def test_a_component_that_ships_a_benchmark_suite_ships_its_baseline():
    """A suite with no committed pin measures without deciding anything.

    The whole point of a component's bench.sh is that a regression is named
    against a number somebody agreed to. A suite that ships without one runs,
    prints, and gates nothing.
    """
    unpinned = [
        component.name
        for component in _components()
        if (component / "bench.sh").is_file()
        and not list(component.glob("**/*baseline*.json"))
    ]
    assert not unpinned, (
        f"these components run a benchmark suite against no committed baseline: "
        f"{unpinned}. A suite with no pin cannot report a regression"
    )


def test_a_component_that_owns_tests_ships_the_script_that_runs_them():
    """Tests reachable only by whoever knows the path are tests nobody runs.

    MORK shipped for months with what tests it had living in the Python seat's
    ch19 chapter and the prolog suites, so the seat could be present and broken
    in a configuration neither of those exercised.
    """
    unrunnable = [
        component.name
        for component in _components()
        if any((component / directory).is_dir() for directory in ("tests", "test"))
        and not (component / "test.sh").is_file()
    ]
    assert not unrunnable, (
        f"these components own a test directory and no test.sh to run it: "
        f"{unrunnable}. The gate and the developer should run one file"
    )


def test_every_seat_ships_a_cheat_sheet_for_using_it():
    """A seat a consumer can reach is a seat a consumer can be told how to use.

    llms.txt is the consumer's file: what this thing is, how to install it, and
    what to type. It is not the contributor's -- gates, test counts and build
    protocol belong in the seat's README and in DEVELOPING.md -- and it is not
    an inventory, which is why the root file stopped pinning how many lines the
    engine is.
    """
    seats = sorted(
        control.parent
        for control in (REPO / "extensions").glob("*/extension.pl")
    )
    assert seats, "no extension.pl found at all, so this check proves nothing"
    missing = [seat.name for seat in seats if not (seat / "llms.txt").is_file()]
    assert not missing, (
        f"these seats ship with no llms.txt telling a consumer how to use them: "
        f"{missing}"
    )
