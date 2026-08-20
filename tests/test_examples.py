"""Purpose: every example in the topical folder tree runs and verifies
itself, or skips for a named missing dependency; an example that stops
working fails the build, so the tree cannot drift from the library. The
last three tests hold the harness itself to that, since `OK name` is what
this file accepts as proof and a helper that cannot fail proves nothing.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES_ROOT = Path(__file__).resolve().parents[1] / "examples"
EXAMPLES = sorted(
    path for path in EXAMPLES_ROOT.rglob("*.py") if path.name != "_common.py"
)


def _example_id(path: Path) -> str:
    return path.relative_to(EXAMPLES_ROOT).with_suffix("").as_posix()


@pytest.mark.parametrize("example", EXAMPLES, ids=_example_id)
def test_example_runs_and_verifies_itself(example):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    repo = EXAMPLES_ROOT.parents[2]
    result = subprocess.run(
        [sys.executable, str(example)],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(example.parent),
        env={
            **os.environ,
            "PETTA_PATH": str(repo),
            "JAX_PLATFORMS": "cpu",
            "PYTHONPATH": str(EXAMPLES_ROOT)
            + os.pathsep
            + os.environ.get("PYTHONPATH", ""),
        },
    )
    output = result.stdout
    if result.returncode == 0 and output.startswith("SKIP:"):
        pytest.skip(output.strip())
    assert result.returncode == 0, (
        f"{_example_id(example)} failed:\n{result.stdout}\n{result.stderr[-2000:]}"
    )
    assert f"OK {example.stem}" in output, (
        f"{_example_id(example)} did not verify itself:\n{output}"
    )


def _run_example_source(tmp_path, source: str, *flags: str):
    """One throwaway example, run the way the runner above runs a real one."""
    script = tmp_path / "throwaway.py"
    script.write_text(source)
    return subprocess.run(
        [sys.executable, *flags, str(script)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(tmp_path),
        env={
            **os.environ,
            "PETTA_PATH": str(EXAMPLES_ROOT.parents[2]),
            "PYTHONPATH": str(EXAMPLES_ROOT)
            + os.pathsep
            + os.environ.get("PYTHONPATH", ""),
        },
    )


# check() has two spellings and each carried its own assert: an expected
# value, and a bare truthiness claim.
WRONG = [
    ("check('two', 1 + 1, 3)", "two: expected 3, got 2"),
    ("check('nonempty', [])", "nonempty: expected a truthy result, got []"),
]


@pytest.mark.parametrize("flags", [(), ("-O",)], ids=["plain", "optimized"])
@pytest.mark.parametrize("claim,message", WRONG, ids=["value", "truthy"])
def test_a_wrong_value_fails_under_O_too(tmp_path, flags, claim, message):  # noqa: N802  -- the symbolic test spelling mirrors the notation whose translation is under test
    """`python -O` removes assert statements outright while the print beside
    one still runs, so the harness's check had to stop asserting: a wrong
    value used to print as a successful check under that flag.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    result = _run_example_source(
        tmp_path,
        f"from _common import check, done\n{claim}\ndone('throwaway')\n",
        *flags,
    )
    assert result.returncode != 0, result.stdout
    assert message in result.stderr, result.stderr
    assert "OK throwaway" not in result.stdout, result.stdout


@pytest.mark.parametrize("flags", [(), ("-O",)], ids=["plain", "optimized"])
def test_a_right_value_still_passes_under_O_too(tmp_path, flags):  # noqa: N802  -- the symbolic test spelling mirrors the notation whose translation is under test
    """The other half of the claim: refusing a wrong value is only worth
    something if the right one is still accepted, under either interpreter.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    result = _run_example_source(
        tmp_path,
        "from _common import check, done\ncheck('two', 1 + 1, 2)\ndone('throwaway')\n",
        *flags,
    )
    assert result.returncode == 0, result.stderr
    assert "OK throwaway" in result.stdout, result.stdout


def test_an_example_that_checks_nothing_is_not_OK(tmp_path):  # noqa: N802  -- the symbolic test spelling mirrors the notation whose translation is under test
    """The runner above reads `OK name` as proof the example verified itself,
    so a file that verified nothing must not be able to print it.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    result = _run_example_source(
        tmp_path, "from _common import done\ndone('throwaway')\n"
    )
    assert result.returncode != 0, result.stdout
    assert "checked nothing" in result.stderr, result.stderr
    assert "OK throwaway" not in result.stdout, result.stdout
