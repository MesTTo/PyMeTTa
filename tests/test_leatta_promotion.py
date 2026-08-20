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
