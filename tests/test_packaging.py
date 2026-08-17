"""Purpose: pin the single package manifest, optional extras, entry points,
and version source that wheel builds publish.
Guarantees:
  - release history and citation metadata exist and enter source archives
    [tested test_release_and_citation_metadata_ship_in_source_archives]
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
    assert project["urls"] == {
        "Homepage": "https://github.com/trueagi-io/PeTTa",
        "Repository": "https://github.com/trueagi-io/PeTTa",
        "Issues": "https://github.com/trueagi-io/PeTTa/issues",
    }


def test_release_and_citation_metadata_ship_in_source_archives():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    source_manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()

    assert "## [Unreleased]" in changelog
    assert "## [1.0.5] - 2026-03-02" in changelog
    assert citation.startswith("cff-version: 1.2.0\n")
    assert 'repository-code: "https://github.com/trueagi-io/PeTTa"' in citation
    assert {"include CHANGELOG.md", "include CITATION.cff"} <= set(source_manifest)


def test_optional_integrations_have_installable_extras():
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


def test_python_gate_groups_files_in_process_workers():
    gate = (ROOT / "check.sh").read_text(encoding="utf-8")
    assert "-p no:benchmark -n auto --dist loadfile --max-worker-restart=0" in gate


def test_benchmark_gate_reports_the_whole_inventory():
    gate = (ROOT / "check.sh").read_text(encoding="utf-8")
    assert "bench.py --counter-only --keep-going" in gate


def test_dependency_audit_treats_tool_extras_as_development_dependencies():
    deptry = _manifest()["tool"]["deptry"]
    assert deptry["optional_dependencies_dev_groups"] == ["test", "checks"]
    assert {"bench.py", "benchmarks"} <= set(deptry["extend_exclude"])


def test_doc_gate_measures_the_public_surface_at_eighty_percent():
    interrogate = _manifest()["tool"]["interrogate"]
    assert interrogate["fail-under"] == 80
    assert interrogate["ignore-semiprivate"] is True
    assert interrogate["ignore-private"] is True


def test_integrations_group_is_left_to_third_parties():
    # The library ships no built-in integration: anything measure-like is
    # built on top, in its own package, publishing into the
    # petta.integrations entry-point group from its own manifest.
    manifest = _manifest()
    assert "petta.integrations" not in manifest["project"].get("entry-points", {})
    assert manifest["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "petta._version.__version__"
    }
    assert __version__ == "0.2.0"
