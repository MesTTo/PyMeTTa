"""Purpose: the two-runtime differential gates the shared fragment, proven
the leatta gate-selftest way: a built corpus with one agreeing and one
diverging file, the REAL lane run over it, and the exit code asserted in
both directions, plus the absence branch. The full-corpus run stays the
check.sh cetta lane's job; this proves the machinery discriminates.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
import subprocess
import sys

AGREEING = "!(+ 1 2)\n; MEASURED:\n;   [3]\n; STATUS: conforms\n"
DIVERGING = "!(+ 2 2)\n; MEASURED:\n;   [5]\n; STATUS: conforms\n"


def _run_lane(repo_root, environment, extra):
    return subprocess.run(
        [sys.executable, str(repo_root / "tests" / "conformance" / "cetta.py"),
         *extra],
        capture_output=True, text=True, timeout=280, env=environment,
        cwd=repo_root,
    )


def test_the_two_runtime_differential_corpus_gates_the_shared_fragment(
    repo_root, tmp_path
):
    pin = repo_root / "tests" / "conformance" / "cetta_shared_fragment.txt"
    pinned = [
        line
        for line in pin.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert pinned, "the shared-fragment pin is empty; the gate would be vacuous"

    absent = dict(os.environ, CETTA_PATH="/nonexistent-cetta-checkout")
    report = _run_lane(repo_root, absent, [])
    assert report.returncode == 0, report.stdout + report.stderr
    assert "not built" in report.stdout, (
        "with the fork absent the lane must SAY the differential is not "
        "checked rather than passing silently"
    )

    sys.path.insert(0, str(repo_root / "tests" / "conformance"))
    try:
        import cetta as lane
    finally:
        sys.path.pop(0)
    binary = lane.checkout() / "cetta"
    if not binary.is_file() or not os.access(binary, os.X_OK):
        return  # no fork on this machine; the absence branch above held

    corpus = tmp_path / "semantics"
    (corpus / "arith").mkdir(parents=True)
    (corpus / "arith" / "agreeing.metta").write_text(AGREEING)
    (corpus / "arith" / "diverging.metta").write_text(DIVERGING)
    fences = tmp_path / "fences.txt"
    fences.write_text("# no fences in this corpus\n")

    both = tmp_path / "fragment_both.txt"
    both.write_text("arith/agreeing.metta\narith/diverging.metta\n")
    broken = _run_lane(
        repo_root, dict(os.environ),
        ["--corpus", str(corpus), "--fences-file", str(fences),
         "--fragment-file", str(both)],
    )
    assert broken.returncode == 1, broken.stdout + broken.stderr
    assert "diverging.metta" in broken.stdout, (
        "a fragment file that stopped agreeing must be NAMED"
    )

    agreeing_only = tmp_path / "fragment_agreeing.txt"
    agreeing_only.write_text("arith/agreeing.metta\n")
    holding = _run_lane(
        repo_root, dict(os.environ),
        ["--corpus", str(corpus), "--fences-file", str(fences),
         "--fragment-file", str(agreeing_only)],
    )
    assert holding.returncode == 0, holding.stdout + holding.stderr
    assert "shared fragment holds" in holding.stdout
