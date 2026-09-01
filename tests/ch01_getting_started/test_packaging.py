"""Purpose: pin the single package manifest, optional extras, entry points,
and version source that wheel builds publish.
Guarantees:
  - release history and citation metadata exist and enter source archives
    [tested: test_release_and_citation_metadata_ship_in_source_archives;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the Python gate uses the fixed load-tested worker protocol
    [tested: test_the_pytest_lane_is_deterministic_under_load_protocol;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the blocking NetworkX and NumPy gallery has installable dependencies in
    both test extras and the minimal-version matrix [tested:
    test_optional_integrations_have_installable_extras,
    test_minimal_version_matrix_installs_blocking_gallery_dependency;
    commit=8bfe05c3850776543ece25a85038242f10b1d841]
  - every ``python -m`` target named by a check.sh command reaches a real
    entry point, so no lane can exit 0 having run nothing [tested:
    test_every_module_invocation_in_the_gate_reaches_an_entry_point;
    commit=dfda5555bdc4b53a57da7084054826236ab1446e]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

from __future__ import annotations

import ast
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import tomllib
from pathlib import Path

import pytest

import metta.atoms as metta_atoms
from metta import __version__

ROOT = Path(__file__).resolve().parents[4]


def _manifest() -> dict:
    return tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


#: The gate is the root driver plus every component check.sh it SOURCES, and
#: the three lanes read below are the Python component's, so they live in
#: extensions/python/check.sh. Reading the root file alone is not a narrower
#: check, it is a check that stops seeing its subject: measured 2026-08-28, the
#: `python -m` scan fell from 18 targets to 1 the moment those lanes moved, and
#: it went on passing, which is the shape of a lane that can no longer fail.
GATE_SCRIPTS = ("check.sh", "engine/check.sh", "extensions/*/check.sh")


def _gate_text() -> str:
    """Every gate script's text, discovered the way check.sh discovers them."""
    return "\n".join(
        path.read_text(encoding="utf-8")
        for pattern in GATE_SCRIPTS
        for path in sorted(ROOT.glob(pattern))
    )


def test_package_and_tools_share_one_manifest():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert (ROOT / "extensions" / "python" / "pyproject.toml").samefile(ROOT / "pyproject.toml")
    project = _manifest()["project"]
    assert project["name"] == "pymetta"
    assert project["dynamic"] == ["version"]
    # 3.12 is the floor the style guide sets, because that is where the class
    # shape's own syntax arrives (PEP 695 generics), which the guide's worked
    # examples write. The library's own code uses nothing newer, so it runs
    # everywhere it claims [source: ai-python-conventions.md, "Version-gated
    # spellings"].
    assert project["requires-python"] == ">=3.12"
    assert project["urls"] == {
        "Homepage": "https://github.com/MesTTo/MeTTa-Kernel",
        "Repository": "https://github.com/MesTTo/MeTTa-Kernel",
        "Issues": "https://github.com/MesTTo/MeTTa-Kernel/issues",
    }


def test_release_and_citation_metadata_ship_in_source_archives():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    source_manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()

    assert "## [Unreleased]" in changelog
    assert "## [1.0.5] - 2026-03-02" in changelog
    assert citation.startswith("cff-version: 1.2.0\n")
    assert 'repository-code: "https://github.com/MesTTo/MeTTa-Kernel"' in citation
    assert {"include CHANGELOG.md", "include CITATION.cff"} <= set(source_manifest)


def _resolved_extra(extras: dict, name: str) -> set[str]:
    """One extra's requirements with any `pymetta[other]` self-reference expanded.

    `checks` is a strict superset of `test` and says so with the PEP 508
    self-reference rather than repeating six pins, so a membership test against
    the literal list would now read false for every one of them. What the extra
    INSTALLS is the contract; how it spells the overlap is not.
    """
    resolved: set[str] = set()
    for requirement in extras[name]:
        reference = re.fullmatch(r"pymetta\[([\w-]+)\]", requirement)
        if reference:
            resolved |= _resolved_extra(extras, reference.group(1))
        else:
            resolved.add(requirement)
    return resolved


def test_optional_integrations_have_installable_extras():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    extras = _manifest()["project"]["optional-dependencies"]
    assert set(extras["arrays"]) == {"array-api-compat", "faiss-cpu", "numpy"}
    assert extras["das"] == ["websocket-client"]
    assert set(extras["dataframes"]) == {"pandas", "polars"}
    # No orjson extra: the JSON codec is the engine's library(json), and
    # no Python-side JSON implementation exists to accelerate.
    assert "orjson" not in extras
    test_requirements = _resolved_extra(extras, "test")
    checks_requirements = _resolved_extra(extras, "checks")
    # The relation itself, which is what the self-reference exists to state.
    # Asserting it directly is stronger than the six membership pairs this
    # replaced: those could all hold while a seventh pin drifted between the
    # two lists, and this cannot.
    assert test_requirements <= checks_requirements
    assert {"pytest-xdist>=3.8,<4", "networkx>=3.6,<4", "numpy"} <= test_requirements
    assert "pylint>=3.3,<4" in checks_requirements
    assert "pylint>=3.3,<4" not in test_requirements
    # No literal duplication survives: every shared pin reaches `checks` through
    # the reference, never by being written twice.
    assert not set(extras["checks"]) & set(extras["test"])


def test_the_minimal_version_matrix_installs_no_optional_integration():
    """The floor matrix proves the suite skips cleanly without the extras.

    Its whole subject is the library on three Pythons with nothing but the
    engine binding and the test runner. Installing an integration package
    there would make the skip-clean property untestable and would fail the
    job whenever that package has no wheel for a new Python.
    """
    matrix = _version_matrix_job()
    extras = _manifest()["project"]["optional-dependencies"]
    integrations = set(extras["arrays"]) | set(extras["das"]) | set(extras["dataframes"])
    integrations |= {"networkx>=3.6,<4"}
    for package in integrations:
        assert package.split(">")[0] not in matrix, package


def _version_matrix_job() -> str:
    workflow = (ROOT / ".github" / "workflows" / "checks.yml").read_text(encoding="utf-8")
    return workflow.split("  versions:", 1)[1].split("\n  wheel:", 1)[0]


def test_the_minimal_version_matrix_installs_every_required_dependency():
    """A new required dependency must reach the matrix or nothing imports.

    docstring-parser became required on 2026-08-23 and was not added to this
    job's install line, so `import metta` raised ModuleNotFoundError in every
    matrix environment from that day. The branch was never pushed, so no CI
    run reported it. This is the check that would have.
    """
    matrix = _version_matrix_job()
    install = next(
        line for line in matrix.splitlines() if "janus_swi" in line and "pytest" in line
    )
    installed = set(install.split())
    manifest = _manifest()["project"]
    # The `engine` extra is checked beside the required list, not instead of
    # it: janus-swi moved there so a plain install cannot fail inside its
    # build, and a suite that runs the engine still needs it. Reading only
    # `dependencies` would have stopped noticing the day it moved.
    required = [*manifest["dependencies"], *manifest["optional-dependencies"]["engine"]]
    for requirement in required:
        name = re.split(r"[<>=!\[]", requirement)[0]
        # janus-swi is spelled with the underscore its distribution uses,
        # because --no-binary names the same package again.
        assert {name, name.replace("-", "_")} & installed, requirement


def test_the_pytest_lane_is_deterministic_under_load_protocol():
    """Pin the exact worker policy exercised by the repeated load protocol.

    The policy lives in the seat's own test.sh, so a developer running that file
    gets the settings that make the run correct rather than a plainer pytest
    invocation sharing one engine across workers. Both halves are pinned: the
    lane must DELEGATE to that file, and that file must carry the protocol.
    Pinning only the lane let the policy walk out of the gate's reach the moment
    the command moved.
    """
    lane = next(
        line for line in _gate_text().splitlines() if line.startswith("run GATE pytest")
    )
    entry = "extensions/python/test.sh"
    assert entry in lane, f"the pytest lane no longer delegates to {entry}: {lane}"

    protocol = re.search(
        r"-p no:benchmark -n (?P<workers>\S+) --dist (?P<dist>\S+) "
        r"--max-worker-restart=(?P<restarts>\d+)",
        (ROOT / entry).read_text(encoding="utf-8"),
    )
    assert protocol is not None, f"{entry} no longer states the worker protocol"
    assert protocol.groupdict() == {
        "workers": "4",
        "dist": "loadfile",
        "restarts": "0",
    }
    # A retry would make a flaky test pass by repetition, and it would now be
    # added where the command is rather than where the lane is.
    assert "--reruns" not in lane
    assert "--reruns" not in (ROOT / entry).read_text(encoding="utf-8")


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
    """The wire codec compiles when PYMETTA_USE_MYPYC=1 asks it to, and the
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
    assert metta_atoms.__file__.endswith(".py")
    plain = _build_ext(tmp_path / "plain", {"PYMETTA_USE_MYPYC": ""})
    assert plain.returncode == 0, plain.stderr
    assert not list((tmp_path / "plain").rglob("*.so"))

    # Asked for, and delivered: exactly the codec, nothing else of metta's.
    compiled = _build_ext(tmp_path / "compiled", {"PYMETTA_USE_MYPYC": "1"})
    assert compiled.returncode == 0, compiled.stderr
    built = sorted(
        path.name.split(".")[0]
        for path in (tmp_path / "compiled" / "lib" / "metta").rglob("*.so")
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
        {"PYMETTA_USE_MYPYC": "1", "PYTHONPATH": str(shadow)},
    )
    assert refused.returncode != 0
    assert "pip install mypy" in refused.stdout + refused.stderr
    assert not list((tmp_path / "refused").rglob("*.so"))


def test_benchmark_gate_reports_the_whole_inventory():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    assert "bench.py --counter-only --keep-going" in _gate_text()


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
    # metta.integrations entry-point group from its own manifest.
    manifest = _manifest()
    assert "metta.integrations" not in manifest["project"].get("entry-points", {})
    assert manifest["tool"]["setuptools"]["dynamic"]["version"] == {
        "attr": "metta._version.__version__"
    }
    # The SHAPE, not the number. The assertion above is the real contract --
    # the manifest reads the version from metta._version rather than carrying
    # its own copy -- and pinning today's literal beside it tests nothing
    # except that somebody edited two files instead of one, which is the
    # chore the dynamic declaration exists to remove.
    assert re.fullmatch(r"\d+\.\d+\.\d+([abrc]\w*)?", __version__), __version__


def test_every_runtime_resource_reaches_the_source_archive(repo_root):
    """The sdist carries everything the wheel build reads, or PyPI breaks.

    `python -m build` builds the wheel FROM the sdist, so a resource the sdist
    drops is one the wheel build cannot find. Measured 2026-08-23: five of the
    nine `RUNTIME_RESOURCES` entries were absent from `MANIFEST.in` and
    `python -m build` died on the first of them, `extensions/mork/extension.pl`,
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
        # why metta/shim.pl needs no directive of its own.
        if resource.startswith("extensions/python/metta/"):
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


def test_every_module_invocation_in_the_gate_reaches_an_entry_point():
    """A `python -m X` whose X has no entry point exits 0 having run nothing.

    Measured 2026-08-26: `python -m importlinter.cli lint_imports` printed
    nothing and exited 0, because importlinter.cli only defines its click
    commands. The `imports` lane had therefore checked nothing since it was
    written, while 62 real contract violations accumulated behind it.
    """
    commands = "\n".join(
        line for line in _gate_text().splitlines() if not line.lstrip().startswith("#")
    )
    targets = sorted(set(re.findall(r"-m ([A-Za-z_][\w.]*)", commands)))
    assert targets, commands

    checked, absent = [], []
    for target in targets:
        try:
            spec = importlib.util.find_spec(target)
        except ModuleNotFoundError:
            spec = None
        if spec is None:
            absent.append(target)
            continue
        checked.append(target)
        if spec.submodule_search_locations is not None:
            assert importlib.util.find_spec(f"{target}.__main__") is not None, (
                f"{target} is a package with no __main__; `python -m {target}` "
                f"cannot run"
            )
            continue
        assert spec.origin is not None, target
        source = Path(spec.origin).read_text(encoding="utf-8", errors="replace")
        guarded = any(
            isinstance(node, ast.If) and "'__main__'" in ast.dump(node.test)
            for node in ast.parse(source).body
        )
        assert guarded, (
            f"{target} has no `if __name__ == '__main__'` block; "
            f"`python -m {target}` imports it and exits 0 without running"
        )

    assert checked, f"nothing was checked; every target was absent: {absent}"
    for target in absent:
        assert target.split(".")[0] not in {"metta", "benchmarks", "pytest"}, (
            f"{target} is a first-party target and must resolve"
        )


def test_the_shim_reaches_the_engine_by_alias_rather_than_by_depth():
    """A relative path from the shim to the engine is right in exactly one
    layout, and this package ships two.

    In a checkout the shim is `extensions/python/metta/shim.pl` and the engine
    is three levels up; in a wheel the shim is `metta/shim.pl` and the engine
    is one level DOWN, at `metta/_runtime/engine/`. The directive used to spell
    the checkout's depth, so the installed copy resolved it to nothing --- and
    a `use_module` that resolves to nothing only WARNS, so the wheel loaded,
    booted, answered arithmetic, and failed every metta._json call with
    `Unknown procedure: json_codec_write/3` [measured 2026-08-29 against a
    wheel installed into a fresh venv outside the checkout].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    shim = (ROOT / "extensions" / "python" / "metta" / "shim.pl").read_text(
        encoding="utf-8"
    )
    # Both layouts are named, and the search runs from the shim's own directory
    # rather than from one hard-coded depth.
    assert "prolog_load_context(directory, Here)" in shim, (
        "the shim no longer resolves the codec from its own directory"
    )
    for layout in ("'../../../engine/json_codec.pl'", "'_runtime/engine/json_codec.pl'"):
        assert layout in shim, f"the shim stopped looking for the codec at {layout}"

    from metta import _json

    # Calling it is the proof the alias resolved: json_codec_write/3 reaches
    # this side only through that import, and it is the half that was broken
    # in the wheel while arithmetic went on answering.
    assert _json.loads(_json.dumps({"a": [1, 2]})) == {"a": [1, 2]}
