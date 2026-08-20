"""Purpose: prove the parity lane detects a difference, ignores a difference
in spelling that is not one, and preserves the per-form grouping, and that
the llms lane's builtin-count claim distinguishes a missing build product
from documentation drift. A lane that cannot be shown failing is not
evidence of anything, so these plant differences and require the lanes to
report them.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "bindings" / "python" / "tools"))

import example_parity as parity  # noqa: E402


def test_the_corpus_is_one_definition():
    """Discovery lives here and nowhere else. It used to be duplicated
    across runners, matching on basename rather than path, and the copies
    disagreed [source: ai-audit-md-review.md section 12].
    """
    found = parity.corpus()
    assert found, "the corpus is empty, which means discovery is broken"
    assert all(path.suffix == ".metta" for path in found)
    assert not any(path.is_symlink() for path in found)
    assert not any("_fixtures" in path.parts for path in found)
    declared = set(parity.skips())
    assert not (declared & {str(p.relative_to(REPO)) for p in found})


def test_every_declared_skip_resolves_and_would_otherwise_run():
    """A skip naming a file that does not exist, or one discovery would
    never have yielded anyway, is a line nobody will notice is dead.
    check.sh carried exactly that: it skipped import_error_broken.metta,
    which lives under _fixtures/ and is excluded before any skip is
    consulted [measured 2026-08-18].
    """
    for path, reason in parity.skips().items():
        assert (REPO / path).is_file(), f"{path} does not exist"
        assert reason, f"{path} has no reason"
        assert not (REPO / path).is_symlink(), f"{path} is an alias"
        assert "_fixtures" not in Path(path).parts, f"{path} is excluded anyway"


def test_example_parity_reports_a_planted_difference():
    """A real difference in ANSWERS survives the value comparison."""
    engine = parity.Outcome(["((1, 2))"], None)
    library = parity.Outcome(["((- 1 2))"], None)
    assert parity._value(engine.groups[0]) != parity._value(library.groups[0])


def test_spelling_is_not_a_difference():
    """The engine writes `true` where the library writes `True`, and both
    parse to the same value. Comparing text reported this on 191 of 200
    examples; comparing values reports it on none [measured 2026-08-18].
    """
    assert parity._value("(true)") == parity._value("(True)")
    assert parity._value("(false)") == parity._value("(False)")
    assert parity._value("(1 2)") != parity._value("(- 1 2)")


def test_an_unparseable_group_stays_visible():
    """A group neither side can parse compares as its own text, so a
    malformed answer is not collapsed to equal-by-failure.
    """
    assert parity._value("(a") == "(a"
    assert parity._value("(a") != parity._value("(b")


def test_the_grouping_is_preserved():
    """`!(superpose (1 2 3))` then `!(+ 1 1)` must not read the same as
    `!(superpose (1 2))` then `!(superpose (3 2))`. Both flatten to the
    answers 1 2 3 2, and the first version of this lane could not tell them
    apart because it printed one line per ANSWER.
    """
    one = parity.Outcome(["(1 2 3)", "(2)"], None)
    two = parity.Outcome(["(1 2)", "(3 2)"], None)
    assert one.groups != two.groups
    flat_one = " ".join(one.groups).replace("(", "").replace(")", "")
    flat_two = " ".join(two.groups).replace("(", "").replace(")", "")
    assert flat_one == flat_two, "the flattened forms really are identical"


def test_an_empty_group_is_an_observation():
    """A form answering nothing prints `()` rather than nothing, because
    dropping it would misalign every group after it.
    """
    outcome = parity._read("LEATTA-ANSWER ()\nLEATTA-ANSWER (2)\n")
    assert outcome.groups == ["()", "(2)"]
    assert outcome.error is None


def test_an_error_line_is_not_an_empty_run():
    outcome = parity._read("LEATTA-ERROR something broke\n")
    assert outcome.error == "something broke"
    assert outcome.groups == []


@pytest.mark.parametrize("name", ["control/forall.metta", "types/types.metta"])
def test_a_known_agreeing_example_agrees(name):
    """Two examples that do agree, so a change breaking the comparison
    itself is caught rather than reading as a corpus finding.
    """
    difference = parity.compare(REPO / "examples" / name)
    assert difference is None, str(difference)


def test_the_stated_corpus_size_is_the_real_one():
    """Three places used to state this number and all three were wrong,
    each by a different amount: examples/README.md said 184, llms.txt said
    242 (a glob counting 24 symlink aliases and 12 fixtures), and the
    survey ledger said 169, against 200 that run [measured 2026-08-18]. A
    number nothing derives is a number that drifts.
    """
    import re

    size = len(parity.corpus())
    readme = (REPO / "examples" / "README.md").read_text()
    stated = re.search(r"contains (\d+) examples that run", readme)
    assert stated, "examples/README.md no longer states its corpus size"
    assert int(stated.group(1)) == size, (
        f"examples/README.md says {stated.group(1)}, the runners run {size}"
    )


def test_the_llms_lane_names_a_missing_artefact_instead_of_a_count_mismatch(
    tmp_path,
):
    """A worktree without a backend's build product reads the truth, not red.

    The builtin count is the one llms.txt claim carrying a CONFIGURATION:
    backends register builtins only where their artefact is built, and both
    wave-10 agents lost a gate run to the bare mismatch message. The
    backends declare their registrations as metta_backend_builtin/1 facts,
    so when the absent artefact explains the difference exactly, the lane
    passes with a note naming the artefact and every registration; a
    difference the artefact does not explain stays a failing drift claim.
    """
    from llmsdoc import _absent_artefact_diagnosis

    backend = tmp_path / "backends" / "mork" / "mork_ffi"
    backend.mkdir(parents=True)
    (backend / "morkspaces.pl").write_text(
        "metta_backend_builtin('mm2-exec').\n"
        "metta_backend_builtin('mork-add-atoms').\n"
        "metta_backend_builtin('mork-flush').\n"
    )
    note = _absent_artefact_diagnosis(225, 222, root=tmp_path)
    assert note is not None
    assert "backends/mork/mork_ffi/target/release/libmork_ffi.so" in note
    for name in ("mm2-exec", "mork-add-atoms", "mork-flush"):
        assert name in note
    # A delta the declarations do not explain is genuine drift, not config.
    assert _absent_artefact_diagnosis(225, 221, root=tmp_path) is None
    # With the artefact present the diagnosis stands aside entirely.
    artefact = backend / "target" / "release"
    artefact.mkdir(parents=True)
    (artefact / "libmork_ffi.so").touch()
    assert _absent_artefact_diagnosis(225, 222, root=tmp_path) is None
