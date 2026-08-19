"""Purpose: the acceptance criteria of the Prolog-native property lane. The
    Python surface has hypothesis and the define fuzzer, and both reach the
    engine through janus, so nothing generated at the Prolog level until now.
    Three claims are checked here rather than read: the lane's generator really
    does generate, because five planted defects each go red through it; its
    vendored runner says where it came from and under what terms; and a gate
    run is the same run every time.
Assumes:
  - swipl is on PATH and the Prolog lanes' working-directory convention holds:
    tests/prolog/property_lane.pl is run from tests/prolog.
Guarantees:
  - the planted-violation test does not stop at "the selftest exits 0": it
    reads the per-plant verdict lines and requires each named plant to be
    CAUGHT and the shipped printer and reader not to be, so a selftest that
    stopped testing fails here.
  - the provenance test reads the vendored files for the licence, the upstream
    commit and the record of what the vendoring changed, and checks the licence
    text itself rather than a claim about it.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

# Each plant and the one generator feature it is caught by. A plant that stops
# being caught names the feature the generator stopped producing, which is what
# makes this a test OF THE GENERATOR rather than a second copy of the laws.
PLANTS = {
    "unescaped_quote": "a string holding a quote",
    "unnumbered_variable": "a variable occurring twice",
    "ascii_folded": "a symbol outside ASCII",
    "number_blind": "a number",
    "flattened_nesting": "a nested expression",
}

VENDORED = ("quickcheck.pl", "mavis.pl", "list_util.pl")


def _prolog(repo_root: Path, goal: str, *, env: dict[str, str] | None = None) -> str:
    finished = subprocess.run(
        ["swipl", "-q", "--on-error=status", "-g", goal, "-t", "halt(0)", "property_lane.pl"],
        capture_output=True,
        text=True,
        timeout=280,
        check=True,
        cwd=repo_root / "tests" / "prolog",
        env=env,
    )
    return finished.stdout


def test_a_prolog_property_lane_catches_a_planted_roundtrip_violation(repo_root):
    report = _prolog(repo_root, "property_lane_selftest")

    for plant, feature in PLANTS.items():
        assert f"plant {plant} ({feature}): caught" in report, report

    # And the shipped printer and reader pass the same law under the same
    # generator, so "caught" above means the plant was caught and not that the
    # law is red for everyone.
    assert "shipped printer and reader: uncaught" in report, report
    assert f"property lane selftest: {len(PLANTS)} plants, each caught" in report, report


def test_the_planted_violation_is_the_same_violation_every_run(repo_root):
    """A gate that flakes is worse than no gate, so the seed is fixed."""
    first = _prolog(repo_root, "property_lane_selftest")
    second = _prolog(repo_root, "property_lane_selftest")
    assert first == second


def test_the_generator_is_seeded_and_the_seed_can_be_widened(repo_root):
    show = (
        "consult('../../src/metta.pl'), "
        "property_seed(S), set_random(seed(S)), "
        "forall(between(1, 20, _), (property_term(full, T), print(T), nl))"
    )
    assert _prolog(repo_root, show) == _prolog(repo_root, show)

    # A different seed is a different run, so the sameness above comes from the
    # seed rather than from a generator that always answers the same thing.
    other = show.replace("property_seed(S)", "S = 20260820")
    assert _prolog(repo_root, other) != _prolog(repo_root, show)


def _unwrapped(path: Path) -> str:
    """A Prolog file's prose with comment markers and line breaks taken out.

    A header claim that happens to be wrapped across two lines is still one
    claim, and a test that reads it should not go red when someone reflows the
    paragraph around it.
    """
    stripped = (line.lstrip("%").strip() for line in path.read_text().splitlines())
    return " ".join(" ".join(stripped).split())


@pytest.mark.parametrize("name", VENDORED)
def test_the_vendored_runner_records_its_provenance(repo_root, name):
    path = repo_root / "tests" / "prolog" / "vendor" / name
    vendored = _unwrapped(path)

    # Whose work it is, under what terms, from which commit, and what the
    # vendoring changed. Without the last one the header is a courtesy rather
    # than something a reader can check the file against.
    assert "Michael Hendricks" in vendored
    assert "PUBLIC DOMAIN" in vendored
    assert "https://github.com/mndrix/" in vendored
    assert "read 2026-08-19" in vendored
    assert "What the vendoring changed" in vendored or "Nothing changed" in vendored

    # The banners that make a merged pack diff-able against its source, read
    # from the file itself rather than from the unwrapped prose.
    assert "%%%%%%%%%% vendored" in path.read_text()


def test_the_vendored_licence_is_the_unlicense_itself(repo_root):
    licence = (repo_root / "tests" / "prolog" / "vendor" / "LICENSE").read_text()
    assert "released into the public domain" in licence
    assert "http://unlicense.org" in licence
    # One copy for the directory is honest only because the three packs ship
    # the same file; a pack that changed its terms would stop matching.
    assert "Anyone is free to copy, modify, publish, use, compile, sell, or" in licence
