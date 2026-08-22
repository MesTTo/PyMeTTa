"""Purpose: pin the single package manifest, optional extras, entry points,
and version source that wheel builds publish.
Guarantees:
  - release history and citation metadata exist and enter source archives
    [tested: test_release_and_citation_metadata_ship_in_source_archives;
    commit=dcfc20be4933c19140ccb5759291401d13058301]
  - the Python gate uses the fixed load-tested worker protocol
    [tested: test_the_pytest_lane_is_deterministic_under_load_protocol;
    commit=dcfc20be4933c19140ccb5759291401d13058301]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tomllib
from pathlib import Path

import pytest

import petta.atoms
from petta import __version__

ROOT = Path(__file__).resolve().parents[3]


def _manifest() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_package_and_tools_share_one_manifest():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert (ROOT / "bindings" / "python" / "pyproject.toml").samefile(ROOT / "pyproject.toml")
    project = _manifest()["project"]
    assert project["name"] == "petta"
    assert project["dynamic"] == ["version"]
    # 3.12 is the floor the style guide sets, because that is where the class
    # shape's own syntax arrives (PEP 695 generics), which the guide's worked
    # examples write. The library's own code uses nothing newer, so it runs
    # everywhere it claims [source: ai-python-conventions.md, "Version-gated
    # spellings"].
    assert project["requires-python"] == ">=3.12"
    assert project["urls"] == {
        "Homepage": "https://github.com/trueagi-io/PeTTa",
        "Repository": "https://github.com/trueagi-io/PeTTa",
        "Issues": "https://github.com/trueagi-io/PeTTa/issues",
    }


def test_release_and_citation_metadata_ship_in_source_archives():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    source_manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()

    assert "## [Unreleased]" in changelog
    assert "## [1.0.5] - 2026-03-02" in changelog
    assert citation.startswith("cff-version: 1.2.0\n")
    assert 'repository-code: "https://github.com/trueagi-io/PeTTa"' in citation
    assert {"include CHANGELOG.md", "include CITATION.cff"} <= set(source_manifest)


def test_optional_integrations_have_installable_extras():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    extras = _manifest()["project"]["optional-dependencies"]
    assert set(extras["arrays"]) == {"array-api-compat", "faiss-cpu", "numpy"}
    assert extras["das"] == ["websocket-client"]
    assert set(extras["dataframes"]) == {"pandas", "polars"}
    # No orjson extra: the JSON codec is the engine's library(json), and
    # no Python-side JSON implementation exists to accelerate.
    assert "orjson" not in extras
    assert "pytest-xdist>=3.8,<4" in extras["test"]
    assert "pytest-xdist>=3.8,<4" in extras["checks"]
    assert "pylint>=3.3,<4" in extras["checks"]


def test_the_pytest_lane_is_deterministic_under_load_protocol():
    """Pin the exact worker policy exercised by the repeated load protocol."""
    gate = (ROOT / "check.sh").read_text(encoding="utf-8")
    lane = next(line for line in gate.splitlines() if line.startswith("run GATE pytest"))
    protocol = re.search(
        r"-p no:benchmark -n (?P<workers>\S+) --dist (?P<dist>\S+) "
        r"--max-worker-restart=(?P<restarts>\d+)",
        lane,
    )
    assert protocol is not None, lane
    assert protocol.groupdict() == {
        "workers": "4",
        "dist": "loadfile",
        "restarts": "0",
    }
    assert "--reruns" not in lane


def _build_ext(destination: Path, environment: dict[str, str]) -> subprocess.CompletedProcess:
    """Run setup.py build_ext with everything written OUTSIDE the checkout.

    A build that wrote beside the source would leave an extension shadowing
    the module it was built from, for this run and every later one.
    """
    return subprocess.run(
        [
            sys.executable,
            "setup.py",
            "build_ext",
            "--build-lib",
            str(destination / "lib"),
            "--build-temp",
            str(destination / "temp"),
        ],
        cwd=ROOT,
        env=os.environ | environment,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )


def test_the_codec_builds_under_mypyc_as_an_option(tmp_path):
    """The wire codec compiles when PETTA_USE_MYPYC=1 asks it to, and the
    build everyone else runs is untouched.

    Measured 2026-08-19, minimum of three instructions:u runs of the
    wire-codec lane: 3457054691 interpreted against 2984812403 compiled,
    1.16x. _atoms_core.py is deliberately not in the compiled set and
    setup.py records each measured reason; this asserts the exclusion by
    naming the extensions the build is allowed to produce, so putting it
    back is a failing test rather than a silent behaviour change.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    pytest.importorskip("mypyc.build", reason="mypyc ships with mypy")
    if shutil.which(sysconfig.get_config_var("CC") or "cc") is None:
        pytest.skip("no C compiler")

    # The default: nothing compiled, and the import answers Python source.
    assert petta.atoms.__file__.endswith(".py")
    plain = _build_ext(tmp_path / "plain", {"PETTA_USE_MYPYC": ""})
    assert plain.returncode == 0, plain.stderr
    assert not list((tmp_path / "plain").rglob("*.so"))

    # Asked for, and delivered: exactly the codec, nothing else of petta's.
    compiled = _build_ext(tmp_path / "compiled", {"PETTA_USE_MYPYC": "1"})
    assert compiled.returncode == 0, compiled.stderr
    built = sorted(
        path.name.split(".")[0]
        for path in (tmp_path / "compiled" / "lib" / "petta").rglob("*.so")
    )
    assert built == ["_atom_wire", "atoms"]

    # Asked for and impossible: the build stops and names the fix, rather
    # than quietly handing back the pure-Python wheel nobody asked for. The
    # stub shadows mypyc as a MODULE, so `from mypyc.build import ...` fails
    # the same way an absent install does.
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    (shadow / "mypyc.py").write_text("", encoding="utf-8")
    refused = _build_ext(
        tmp_path / "refused",
        {"PETTA_USE_MYPYC": "1", "PYTHONPATH": str(shadow)},
    )
    assert refused.returncode != 0
    assert "pip install mypy" in refused.stdout + refused.stderr
    assert not list((tmp_path / "refused").rglob("*.so"))


def test_benchmark_gate_reports_the_whole_inventory():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    gate = (ROOT / "check.sh").read_text(encoding="utf-8")
    assert "bench.py --counter-only --keep-going" in gate


def test_dependency_audit_treats_tool_extras_as_development_dependencies():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    deptry = _manifest()["tool"]["deptry"]
    assert deptry["optional_dependencies_dev_groups"] == ["test", "checks"]
    assert {"bench.py", "benchmarks"} <= set(deptry["extend_exclude"])


def test_doc_gate_measures_the_public_surface_at_eighty_percent():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    interrogate = _manifest()["tool"]["interrogate"]
    assert interrogate["fail-under"] == 80
    assert interrogate["ignore-semiprivate"] is True
    assert interrogate["ignore-private"] is True


def test_integrations_group_is_left_to_third_parties():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    # The library ships no built-in integration: anything measure-like is
    # built on top, in its own package, publishing into the
    # petta.integrations entry-point group from its own manifest.
    manifest = _manifest()
    assert "petta.integrations" not in manifest["project"].get("entry-points", {})
    assert manifest["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "petta._version.__version__"
    }
    assert __version__ == "0.2.0"


def test_every_runtime_resource_reaches_the_source_archive(repo_root):
    """The sdist carries everything the wheel build reads, or PyPI breaks.

    `python -m build` builds the wheel FROM the sdist, so a resource the sdist
    drops is one the wheel build cannot find. Measured 2026-08-23: five of the
    nine `RUNTIME_RESOURCES` entries were absent from `MANIFEST.in` and
    `python -m build` died on the first of them, `backends/mork/decider.pl`,
    while `python -m build --wheel` succeeded because it reads the working tree
    directly. CI ran only the second, so the path every installer takes was the
    one path never exercised.

    Checked statically against MANIFEST.in rather than by building, because
    building an archive costs more than the whole pytest lane; the CI wheel job
    runs the real `python -m build` and installs from the sdist it produces.
    """
    import ast
    import fnmatch

    tree = ast.parse((repo_root / "setup.py").read_text(encoding="utf-8"))
    mapping = next(
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", None) == "RUNTIME_RESOURCES" for t in node.targets)
    )
    resources = [ast.literal_eval(key) for key in mapping.keys]

    directives = [
        line.split(maxsplit=2)
        for line in (repo_root / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    def covered(resource: str) -> bool:
        # setuptools also ships a package's own declared package-data, which is
        # why petta/shim.pl needs no directive of its own.
        if resource.startswith("bindings/python/petta/"):
            return True
        for directive in directives:
            verb = directive[0]
            if verb == "include" and resource in directive[1:]:
                return True
            if verb == "recursive-include" and len(directive) > 1:
                root = directive[1]
                if resource == root or resource.startswith(root + "/"):
                    return True
                if fnmatch.fnmatch(resource, root + "/*"):
                    return True
        return False

    missing = [resource for resource in resources if not covered(resource)]
    assert not missing, (
        f"MANIFEST.in does not carry {missing} into the source archive, so "
        f"`python -m build` cannot build the wheel from it and `pip install` "
        f"from PyPI fails"
    )
