"""Purpose: the conformance gate's own discrimination proof. A gate that
cannot be pointed at a planted disagreement is a wall nobody has watched
fail, so this builds a three-entry pin -- one file that agrees, one whose
difference is a recorded ruling, and one claiming agreement while differing
-- and requires the gate to pass the first two and block on the third.

The pin is a temporary directory rather than the shipped one, through
PETTA_PIN, so the proof runs on every checkout and needs no upstream.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
RUNNER = ROOT / "tests" / "conformance" / "petta.py"


def _pin(tmp_path: Path, entries: dict[str, tuple[str, str, str]]) -> Path:
    """Write a pin: name -> (source, expected stdout, status).

    A `diverges` row records what THIS engine prints, which for every fixture
    here is the answer to `!(+ 1 1)`.
    """
    (tmp_path / "examples").mkdir()
    (tmp_path / "expected").mkdir()
    manifest = {"captured_with": "test", "commit": "planted",
                "engine_flag": "silent", "entries": {}}
    for name, (source, expected, status) in entries.items():
        (tmp_path / "examples" / name).write_text(source, encoding="utf-8")
        (tmp_path / "expected" / f"{name}.out").write_text(expected, encoding="utf-8")
        row: dict[str, object] = {"rc": 0, "status": status}
        if status == "diverges":
            row["ours"] = OURS
            row["ours_rc"] = 0
        manifest["entries"][name] = row
    (tmp_path / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


def _gate(pin: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--gate", "--timeout", "90"],
        cwd=ROOT, capture_output=True, text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(Path.home()), "PETTA_PIN": str(pin)},
        check=False,
    )


AGREES = "!(+ 1 1)\n"
OURS = "2\n"


def test_an_agreeing_entry_passes(tmp_path):
    """The ordinary case: what the pin recorded is what this engine prints."""
    pin = _pin(tmp_path, {"agrees.metta": (AGREES, "2\n", "conforms")})
    done = _gate(pin)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "blocking        : 0" in done.stdout


def test_a_recorded_ruling_passes_while_it_stays_exactly_that(tmp_path):
    """A divergence the pin RULED on is clean, and only in the recorded shape.

    Without this half no entry could ever be ruled on without the gate
    adopting it as agreement, and the difference could then drift freely.
    """
    pin = _pin(tmp_path, {"ruled.metta": (AGREES, "4\n", "diverges")})
    done = _gate(pin)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "recorded rulings: 1" in done.stdout


def test_a_file_claiming_agreement_while_differing_blocks(tmp_path):
    """The one shape a conformance lane exists to catch."""
    pin = _pin(tmp_path, {"stale.metta": (AGREES, "9\n", "conforms")})
    done = _gate(pin)
    assert done.returncode != 0, done.stdout
    assert "stale.metta" in done.stdout


def test_an_absent_pin_is_a_configuration_error_not_a_quiet_pass(tmp_path):
    """An empty corpus passing quietly is how a lane stops meaning anything."""
    done = _gate(tmp_path / "nowhere")
    assert done.returncode != 0
    assert "pin" in (done.stdout + done.stderr).lower()
