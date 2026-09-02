"""Purpose: no tracked file cites an absolute workspace path. The repository
may be published, and a reader's machine has no such user directory; a
citation spells the arbiter repo-relative (LeaTTa tests/...) and machinery
reaches the oracle through the LEATTA_PATH environment override, whose three
carriers are the one documented exception.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re
import subprocess

import pytest

_FIXED_ORACLE_PATH_PATTERN = {
    "tests/conformance/cetta.py",
    "tests/conformance/cetta_corpus.py",
    "extensions/python/tests/conformance/test_critical_pair_oracle.py",
}

# Built in pieces so the tracked scanner never matches its own needle.
_WORKSPACE_ROOT = "/" + "home/"
# A Windows checkout roots at a drive letter, so a citation copied from one
# reads C:\\Users\\... or D:\\a\\... and the POSIX needle above never sees it.
_WINDOWS_ROOT = re.compile(r"[A-Za-z]:[\\\\/](?:Users|home|a)[\\\\/]")


def test_no_tracked_file_cites_an_absolute_workspace_path(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    listing = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root, capture_output=True, text=True, timeout=60, check=False,
    )
    if listing.returncode != 0:
        # Nothing to assert about a tree git will not enumerate. A CI checkout
        # git declines to read, over ownership or otherwise, is a fact about
        # that machine; reporting it as a repository defect blames the wrong
        # thing and hides whatever the run was meant to catch.
        pytest.skip(f"git ls-files is unavailable here: {listing.stderr.strip()[:200]}")
    tracked = listing.stdout.splitlines()
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
            if _WORKSPACE_ROOT in line or _WINDOWS_ROOT.search(line):
                offenders.append(f"{name}:{number}: {line.strip()[:80]}")
    assert not offenders, (
        "a tracked file cites an absolute workspace path; respell it "
        "repo-relative, or reach the oracle through LEATTA_PATH:\n"
        + "\n".join(offenders)
    )
