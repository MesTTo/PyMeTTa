"""Purpose: every benchmark driver this repository ships can be imported.

A gate lane that dies before it measures a row is a lane that says nothing,
and it says nothing LOUDLY enough to be mistaken for a tree that moved. The
c-bench, mork-bench and node-bench lanes spent the extension-package merge
that way: the harness moved out of `metta.testing` into the
`metta_benchmarking` distribution, three seat drivers were left importing the
old name, and each lane's toolchain guard asked whether `metta.testing`
imported -- which it still did -- so the guard passed and the driver died on
`ImportError: cannot import name 'BenchmarkBaseline'`. Three GATE lanes
measured nothing and reported it as a failure of the tree.

The roster is DERIVED from the tree rather than listed, so a seat that gains a
driver is covered with no edit here, which is the property the sibling check
`test_every_module_invocation_in_the_gate_reaches_an_entry_point` has for
`python -m` targets in the gate.
Guarantees:
  - every `bench.py` the repository tracks answers `--help` with status 0,
    which runs its module body and therefore its imports
    [tested: test_every_benchmark_driver_imports; commit=WORKTREE]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


def drivers() -> list[Path]:
    """Every benchmark driver the repository tracks, in path order."""
    # git, with a fixed argument list, resolved from PATH the way every
    # other repository check in this suite resolves it.
    listed = subprocess.run(
        ["git", "ls-files", "*bench.py"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [ROOT / name for name in listed]


def test_the_driver_roster_is_not_empty():
    """A roster that resolved to nothing would make the check below vacuous."""
    found = drivers()
    assert found, "git ls-files '*bench.py' answered nothing in this checkout"
    for driver in found:
        assert driver.is_file(), driver


@pytest.mark.parametrize("driver", drivers(), ids=lambda path: str(path.relative_to(ROOT)))
def test_every_benchmark_driver_imports(driver):
    """`--help` runs the module body, so a broken import fails here.

    argparse answers `--help` with status 0 after everything at module level
    has run, which is exactly the import check and nothing more: no engine
    boots, no counter is read and no baseline is touched.
    """
    # A tracked driver of this repository, with one fixed flag.
    finished = subprocess.run(
        [sys.executable, str(driver), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    assert finished.returncode == 0, (
        f"{driver.relative_to(ROOT)} --help exited {finished.returncode}; its "
        f"lane would die before measuring a row:\n{finished.stderr[-2000:]}"
    )
