"""Purpose: hold `metta._roots` to answering both roots without counting levels.

The point of the contract is that it keeps answering when a file MOVES, which a
`parents[N]` count cannot. So the tests ask from several depths and from a file
planted at a depth nothing in the tree uses, rather than only from here.

Guarantees: covered by the assertions below.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from metta._roots import seat, workspace


def test_the_seat_is_the_component_this_package_ships_from():
    """Found by a marker that survives a copy, not by `.git` alone.

    Asserting `.git` was this test's own bug and it failed in the tree the gates run
    in, which is populated by `rsync` and has no history at all.
    """
    assert (seat() / "metta" / "_roots.py").is_file()
    assert (seat() / "pyproject.toml").exists() or (seat() / ".git").exists()
    assert seat() == seat()


def test_the_workspace_is_what_mounts_the_components():
    """It holds both `engine/` and `lib/`, which is what makes it the workspace."""
    assert (workspace() / "engine").is_dir()
    assert (workspace() / "lib").is_dir()
    assert seat().is_relative_to(workspace())


@pytest.mark.parametrize("depth", [1, 2, 3, 4, 5])
def test_the_answer_does_not_depend_on_how_deep_the_asking_file_sits(tmp_path, depth):
    """A planted file at any depth under the seat answers the same two roots.

    This is the property a level count cannot have, and the reason for the contract:
    the counts this replaced were spread over six different depths because each was
    written for wherever its file happened to be. A file that moves keeps working.
    """
    top = seat() / "ai-tmp-roots-probe"
    planted = top.joinpath(*[f"level{n}" for n in range(depth - 1)]) / "probe.py"
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text(
        "from metta._roots import seat, workspace\n"
        "print(seat(), workspace())\n", encoding="utf-8")
    try:
        done = subprocess.run([sys.executable, str(planted)], capture_output=True, text=True,
                              cwd=tmp_path, env={**os.environ, "PYTHONPATH": str(seat())}, check=True)
    finally:
        shutil.rmtree(top, ignore_errors=True)
    answered_seat, answered_workspace = done.stdout.split()
    assert Path(answered_seat) == seat()
    assert Path(answered_workspace) == workspace()


def test_an_operator_naming_the_tree_outranks_anything_inferred(monkeypatch, tmp_path):
    """`METTA_WORKSPACE` wins, because an operator who says where the tree is knows."""
    (tmp_path / "engine").mkdir()
    (tmp_path / "lib").mkdir()
    monkeypatch.setenv("METTA_WORKSPACE", str(tmp_path))
    workspace.cache_clear()
    try:
        assert workspace() == tmp_path.resolve()
    finally:
        monkeypatch.delenv("METTA_WORKSPACE", raising=False)
        workspace.cache_clear()


@pytest.mark.parametrize("component", ["engine", "lib", "examples", "ext", "extensions/node"])
def test_a_component_answers_its_own_root_when_it_names_its_own_file(component):
    """A caller outside the seat passes its `__file__` and gets ITS component.

    `ext/` is ONE component holding every `metta-*` distribution, not nine, so asking
    from inside `ext/metta-arrays` answers `ext`. That is the right answer and the
    reason the marker is a repository rather than a `pyproject.toml`.
    """
    root = workspace() / component
    if not (root / ".git").exists():
        pytest.skip(f"this checkout has no {component} component mounted")
    assert seat(str(root / "anything-at-all.txt")) == root
