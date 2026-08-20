"""Purpose: the conformance promotion rule, blackbox: a promoted area whose
only differences are the arbiter's own committed rulings is CLEAN, and a
file claiming agreement while differing is what blocks. Without the first
half no area could ever promote without adopting every deliberate
divergence, which is the trap the wave-9 burn-down measured.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import subprocess
import sys

CONFORMS = """\
; PURPOSE: fixture, agreeing file with a conforms status.
; MEASURED: printed on stdout:
;   [2]
; STATUS: conforms.

!(+ 1 1)
"""

COMMITTED_DIVERGENCE = """\
; PURPOSE: fixture, the arbiter ruled against upstream here, so the
;   difference below is the recorded state and not a regression.
; MEASURED: printed on stdout:
;   [9]
; STATUS: diverges.

!(+ 2 2)
"""

STALE_CLAIM = """\
; PURPOSE: fixture, claims agreement while differing: the one shape that
;   blocks a promoted area.
; MEASURED: printed on stdout:
;   [9]
; STATUS: conforms.

!(+ 4 4)
"""

OUTER_HEAD_MATCH = """\
; PURPOSE: fixture for the literal Atom head-matching arbiter.
; MEASURED: On the pinned arbiter,
;   produced verbatim `[outer-held]`.
;
; STATUS: conforms.

(: p020-inner-sum (-> Number Number Number))
(= (p020-inner-sum $x $y) (+ $x $y))
(: p020-outer-hold (-> Atom Symbol))
(= (p020-outer-hold (p020-inner-sum $x $y)) outer-held)
!(p020-outer-hold (p020-inner-sum 1 2))
"""

NESTED_HEAD_MATCH = """\
; PURPOSE: fixture for the nested Atom head-matching arbiter.
; MEASURED: On the pinned arbiter,
;   produced verbatim `[nested-argument-evaluated]`.
;
; STATUS: conforms.

(: P020-P3 (-> Type Type))
(: p020-pa3 (P020-P3 Atom))
(: p020-produce-pa3 (-> (P020-P3 Atom)))
(= (p020-produce-pa3) p020-pa3)
(: p020-nested-atom (-> (P020-P3 Atom) Symbol))
(= (p020-nested-atom p020-pa3) nested-argument-evaluated)
(= (p020-nested-atom (p020-produce-pa3)) nested-argument-held)
!(p020-nested-atom (p020-produce-pa3))
"""


def _run_lane(repo_root, corpus, gate_file):
    return subprocess.run(
        [sys.executable,
         str(repo_root / "tests" / "conformance" / "leatta.py"),
         "--corpus", str(corpus), "--engine", str(repo_root),
         "--timeout", "25", "--show", "20",
         "--gate-areas-file", str(gate_file)],
        capture_output=True,
        text=True,
        timeout=280,
        check=False,
    )


def test_a_recorded_divergence_does_not_block_area_promotion(repo_root, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    area = tmp_path / "delta"
    area.mkdir()
    (area / "agrees.metta").write_text(CONFORMS)
    (area / "committed.metta").write_text(COMMITTED_DIVERGENCE)
    gate_file = tmp_path / "gate.txt"
    gate_file.write_text("delta\n")

    promoted = _run_lane(repo_root, tmp_path, gate_file)
    assert promoted.returncode == 0, promoted.stdout
    assert "every promoted area conforms" in promoted.stdout
    assert "diverges: 1" in promoted.stdout

    (area / "stale.metta").write_text(STALE_CLAIM)
    blocked = _run_lane(repo_root, tmp_path, gate_file)
    assert blocked.returncode == 1, blocked.stdout
    assert "regressed: ['delta']" in blocked.stdout


def test_the_two_head_matching_arbiter_files_are_counted(repo_root, tmp_path):
    """The two P2.1 arbiters contribute answer groups instead of prose skips."""
    area = tmp_path / "types-meta"
    area.mkdir()
    (area / "19_atom_parameter_outer_call.metta").write_text(
        OUTER_HEAD_MATCH, encoding="utf-8"
    )
    (area / "15_atom_parameter_nested_parametric.metta").write_text(
        NESTED_HEAD_MATCH, encoding="utf-8"
    )
    gate_file = tmp_path / "gate.txt"
    gate_file.write_text("types-meta\n", encoding="utf-8")

    counted = _run_lane(repo_root, tmp_path, gate_file)

    assert counted.returncode == 0, counted.stdout + counted.stderr
    assert "2/2 checkable files agree, 2 answer groups compared" in counted.stdout
    assert "0 files state their MEASURED block as prose" in counted.stdout
    assert "0 MEASURED lines are printed output rather than answers" in counted.stdout
