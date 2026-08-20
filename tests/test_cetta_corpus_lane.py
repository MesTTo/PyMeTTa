"""Purpose: the forward corpus lane verifies the re-pinned manifest and
discriminates: with the fork absent it says so and passes, with an entry
off its pin it fails naming the entry, and with the pin intact it holds.
The discrimination probes run on a copied manifest restricted to two
cheap entries, so the proof costs two engine runs, not 207; the full
replay is the check.sh cetta-corpus lane's job.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import json
import os
import subprocess
import sys


def _run_lane(repo_root, environment, extra):
    return subprocess.run(
        [sys.executable,
         str(repo_root / "tests" / "conformance" / "cetta_corpus.py"),
         *extra],
        capture_output=True, text=True, timeout=280, env=environment,
        cwd=repo_root,
    )


def test_the_forward_corpus_lane_verifies_the_repinned_manifest(
    repo_root, tmp_path
):
    absent = dict(os.environ, CETTA_PATH="/nonexistent-cetta-checkout")
    report = _run_lane(repo_root, absent, [])
    assert report.returncode == 0, report.stdout + report.stderr
    assert "not checked out" in report.stdout

    sys.path.insert(0, str(repo_root / "tests" / "conformance"))
    try:
        import cetta as lane
    finally:
        sys.path.pop(0)
    manifest_path = (
        lane.checkout() / "tests" / "petta" / "corpus" / "manifest.json"
    )
    if not manifest_path.is_file():
        return  # no fork on this machine; the absence branch above held

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    small = dict(manifest)
    small["entries"] = [
        entry for entry in manifest["entries"]
        if entry["name"] in ("basics/add.metta", "basics/arithmetics.metta")
    ] or manifest["entries"][:2]
    assert len(small["entries"]) == 2

    intact = tmp_path / "manifest_intact.json"
    intact.write_text(json.dumps(small), encoding="utf-8")
    holding = _run_lane(repo_root, dict(os.environ),
                        ["--manifest", str(intact)])
    assert holding.returncode == 0, holding.stdout + holding.stderr
    assert "2 match, 0 moved" in holding.stdout

    tampered_entries = json.loads(json.dumps(small))
    tampered_entries["entries"][0]["oracle"]["stdout"] = "not what it says\n"
    tampered = tmp_path / "manifest_tampered.json"
    tampered.write_text(json.dumps(tampered_entries), encoding="utf-8")
    broken = _run_lane(repo_root, dict(os.environ),
                       ["--manifest", str(tampered)])
    assert broken.returncode == 1, broken.stdout + broken.stderr
    name = tampered_entries["entries"][0]["name"]
    assert name in broken.stdout, (
        "an entry off its pin must be NAMED:\n" + broken.stdout
    )
