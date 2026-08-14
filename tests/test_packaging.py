"""Purpose: pin the single package manifest, optional extras, entry points,
and version source that wheel builds publish.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from petta import __version__

ROOT = Path(__file__).resolve().parents[2]


def _manifest() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_package_and_tools_share_one_manifest():
    assert (ROOT / "python" / "pyproject.toml").samefile(ROOT / "pyproject.toml")
    project = _manifest()["project"]
    assert project["name"] == "petta"
    assert project["dynamic"] == ["version"]
    assert project["requires-python"] == ">=3.11"


def test_optional_integrations_have_installable_extras():
    extras = _manifest()["project"]["optional-dependencies"]
    assert set(extras["arrays"]) == {"array-api-compat", "faiss-cpu", "numpy"}
    assert extras["das"] == ["websocket-client"]
    assert set(extras["dataframes"]) == {"pandas", "polars"}
    assert extras["orjson"] == ["orjson>=3.10,<4"]
    assert "pytest-xdist>=3.8,<4" in extras["test"]
    assert "pytest-xdist>=3.8,<4" in extras["checks"]
    assert "pylint>=3.3,<4" in extras["checks"]


def test_python_gate_groups_files_in_process_workers():
    gate = (ROOT / "check.sh").read_text(encoding="utf-8")
    assert "-p no:benchmark -n auto --dist loadfile --max-worker-restart=0" in gate


def test_dependency_audit_treats_tool_extras_as_development_dependencies():
    deptry = _manifest()["tool"]["deptry"]
    assert deptry["optional_dependencies_dev_groups"] == ["test", "checks"]
    assert {"bench.py", "benchmarks"} <= set(deptry["extend_exclude"])


def test_measure_integration_and_version_are_published_from_their_modules():
    manifest = _manifest()
    assert manifest["project"]["entry-points"]["petta.integrations"] == {
        "measure": "petta.measure"
    }
    assert manifest["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "petta._version.__version__"
    }
    assert __version__ == "0.2.0"
