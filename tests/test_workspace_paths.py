"""Purpose: no tracked file cites an absolute workspace path. The repository
may be published, and a reader's machine has no such user directory; a
citation spells the arbiter repo-relative (LeaTTa tests/...) and machinery
reaches the oracle through the LEATTA_PATH environment override, whose three
carriers are the one documented exception.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import subprocess

_FIXED_ORACLE_PATH_PATTERN = {
    "tests/conformance/leatta.py",
    "tests/conformance/cetta.py",
    "tests/conformance/cetta_corpus.py",
    "bindings/python/tests/test_presented_core_oracle.py",
    "bindings/python/tests/test_critical_pair_oracle.py",
}

# Built in two pieces so the tracked scanner never matches its own needle.
_WORKSPACE_ROOT = "/" + "home/"


def test_no_tracked_file_cites_an_absolute_workspace_path(repo_root):
    tracked = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root, capture_output=True, text=True, timeout=60, check=True,
    ).stdout.splitlines()
    offenders = []
    for name in tracked:
        if name in _FIXED_ORACLE_PATH_PATTERN:
            continue
        path = repo_root / name
        try:
            text = path.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if _WORKSPACE_ROOT in line:
                offenders.append(f"{name}:{number}: {line.strip()[:80]}")
    assert not offenders, (
        "a tracked file cites an absolute workspace path; respell it "
        "repo-relative, or reach the oracle through LEATTA_PATH:\n"
        + "\n".join(offenders)
    )
