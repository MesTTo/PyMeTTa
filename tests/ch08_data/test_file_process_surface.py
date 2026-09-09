"""Purpose: exercise MeTTa file and process operations through public doors.

Process exit is confined to subprocesses. Fixtures own temporary files.
[tested: test_standard_streams_and_explicit_exit; commit=504f8dddfa890ced97e795a13ab10e239b1de2ce]
"""

import subprocess
from pathlib import Path

import pytest

from metta import MeTTa, S, lib
from metta._errors.errors import EngineError

ROOT = Path(__file__).resolve().parents[4]
EXAMPLES = ROOT / "examples/ch20-extending-the-engine/20-06-files-and-processes"


def test_standard_streams_and_explicit_exit():
    """EOF reads preserve text and stderr remains separate from stdout."""
    completed = subprocess.run(
        ["sh", "run.sh", str(EXAMPLES / "02-standard-streams.metta"), "--silent"],
        cwd=ROOT, input="first\nλ last\n", text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == "first\nλ last\nstandard streams complete\n"
    assert "λ last" not in completed.stdout


def test_exit_is_process_termination_even_inside_catch():
    """An exit status is not a recoverable function return."""
    completed = subprocess.run(
        ["sh", "run.sh", str(EXAMPLES / "_fixtures/exit-status.metta"), "--silent"],
        cwd=ROOT, text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 17, completed.stderr
    assert "unreachable" not in completed.stderr


def test_file_permission_errors_have_names_and_remedies(tmp_path):
    """The OS distinguishes an unreadable source from an absent source."""
    source = tmp_path / "private"
    destination = tmp_path / "copy"
    source.write_bytes(b"secret")
    source.chmod(0)
    try:
        with MeTTa() as metta:
            metta += lib.file
            with pytest.raises(EngineError, match="file-permission-denied") as caught:
                list(metta.eval(S["copy-file!"](str(source), str(destination))))
            assert "Check access permissions" in str(caught.value)
            assert "Unknown error term" not in str(caught.value)
        assert not destination.exists()
    finally:
        source.chmod(0o600)
