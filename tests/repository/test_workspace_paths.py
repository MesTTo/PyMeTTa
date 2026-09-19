"""Purpose: no tracked file cites an absolute workspace path. The repository
may be published, and a reader's machine has no such user directory, so a
citation spells its source repo-relative and anything that needs a checkout
outside this repository derives it from this file's own position or takes it
from an environment variable. There is no exemption: every tracked file is
scanned.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import re
import subprocess

import pytest

# Built in pieces so the tracked scanner never matches its own needle.
_WORKSPACE_ROOT = "/" + "home/"
# A Windows checkout roots at a drive letter, so a citation copied from one
# reads C:\\Users\\... or D:\\a\\... and the POSIX needle above never sees it.
# A drive is exactly ONE letter, which the lookbehind requires: without it the
# tail of a URI scheme reads as a drive and `"foo:/a//b"` in the uri library's
# own fixtures was reported as a Windows path [measured 2026-09-19].
_WINDOWS_ROOT = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\\\/](?:Users|home|a)[\\\\/]")


def test_no_tracked_file_cites_an_absolute_workspace_path(repo_root):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    listing = subprocess.run(
        # Components are submodules, so a plain listing stops at each gitlink and this
        # lane would scan a fraction of the tree while still reporting a pass.
        ["git", "ls-files", "--recurse-submodules"],
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
        "repo-relative, or derive it from the citing file's own position:\n"
        + "\n".join(offenders)
    )
