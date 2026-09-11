"""Purpose: pin the single package manifest, optional extras, entry points,
and version source that wheel builds publish.
Guarantees:
  - the optional mypyc wire/factory pair executes native rational decoding,
    ordering and Vector composition in its built package [tested:
    test_the_codec_builds_under_mypyc_as_an_option; commit=WORKTREE]
  - release history and citation metadata exist and enter source archives
    [tested: test_release_and_citation_metadata_ship_in_source_archives;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the Python gate uses the fixed load-tested worker protocol
    [tested: test_the_pytest_lane_is_deterministic_under_load_protocol;
    commit=f88aa8be03cb64cb59d3307515ded8701f418321]
  - the blocking NetworkX and NumPy gallery has installable dependencies in
    the test extras, and the minimal-version matrix DELIBERATELY installs none
    of them, so the suite's skip-clean property stays testable on a floor with
    nothing but the engine binding and the runner. The claim here said the
    matrix installed them too and named a test asserting the opposite of what
    the one in the tree asserts [tested:
    test_every_extra_installs_packages_and_never_a_library,
    test_the_minimal_version_matrix_installs_no_optional_integration;
    commit=b615b5a33b43252ef9826e5387da7c9bd7f6b543]
  - a roster is read by requirement NAME and a pin by its exact string, so
    adding a floor to a member is not adding a member, and every integration
    extra reaches the floor-matrix check from the manifest rather than from a
    list kept here [tested:
    test_every_extra_installs_packages_and_never_a_library,
    test_the_minimal_version_matrix_installs_no_optional_integration;
    commit=0800a2651599aec83dc553657aa94a567cd986fb]
  - every ``python -m`` target named by a check.sh command reaches a real
    entry point, so no lane can exit 0 having run nothing [tested:
    test_every_module_invocation_in_the_gate_reaches_an_entry_point;
    commit=dfda5555bdc4b53a57da7084054826236ab1446e]
  - source-tree fixture loading coexists with installed pytest entry-point
    metadata [tested:
    test_source_tree_fixtures_coexist_with_installed_plugin_metadata;
    commit=993608c01049bcca7530931b680c416c81023543]
  - wheel-owned source and runtime data carry durable public authorities, not
    private agent scratch references [tested:
    test_the_wheel_carries_no_agent_scratch_references;
    commit=af5821f5ffb7ce186e516706f003d02f5c1d3b4a]
  - the public lint authority names the immutable catalogue shipped in this
    repository [tested:
    test_the_lint_authority_matches_the_public_repository_snapshot;
    commit=2a32acb6d254ea12085526913c7b9a1a555b8ee0]
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
from collections.abc import Iterable
from pathlib import Path

import pytest
from packaging.requirements import Requirement

import metta._atoms.factories as metta_atoms
from metta import __version__
from metta._spaces.intents import _LINT_CATALOGUE

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


def test_the_wheel_carries_no_agent_scratch_references():
    """Published package data must cite sources users can retrieve."""
    package = Path(metta_atoms.__file__).resolve().parents[1]
    forbidden = re.compile(
        r"(?i)(?:\bai[-_/][\w./-]*|\bcodex\b|\bclaude\b|\bchatgpt\b|"
        r"\bopenai\b|\banthropic\b)"
    )
    offenders = {}
    for path in sorted(package.rglob("*")):
        if path.is_file() and path.suffix in {".py", ".pyi", ".pl"}:
            matches = sorted(set(forbidden.findall(path.read_text(encoding="utf-8"))))
            if matches:
                offenders[str(path.relative_to(package))] = matches

    assert not offenders, offenders


def test_the_lint_authority_matches_the_public_repository_snapshot():
    """The immutable authority belongs to this project and names its real guide."""
    repository = _manifest()["project"]["urls"]["Repository"]
    match = re.fullmatch(
        rf"{re.escape(repository)}/blob/(?P<commit>[0-9a-f]{{40}})/"
        r"(?P<path>[^#]+)#(?P<anchor>[a-z0-9-]+)",
        _LINT_CATALOGUE,
    )
    assert match is not None, _LINT_CATALOGUE
    assert match.group("commit") == "7de3d32d25a7166b12f7c68c179e9cbb931ac044"
    guide = (ROOT / match.group("path")).read_text(encoding="utf-8")
    assert "## Lint a space" in guide
    assert "operation-crossing-in-loop" in guide


def _resolved_extra(extras: dict, name: str) -> set[str]:
    """One extra's requirements with any `pymetta[other]` self-reference expanded.

    `checks` is a strict superset of `test` and says so with the PEP 508
    self-reference rather than repeating six pins, so a membership test against
    the literal list would now read false for every one of them. What the extra
    INSTALLS is the contract; how it spells the overlap is not. `test` uses the
    same spelling to pull in every extension package this repository ships.
    """
    resolved: set[str] = set()
    for requirement in extras[name]:
        # One reference may name several extras, which is how `test` pulls in
        # every extension package at once.
        reference = re.fullmatch(r"pymetta\[([\w,\s-]+)\]", requirement)
        if reference:
            for referenced in reference.group(1).split(","):
                resolved |= _resolved_extra(extras, referenced.strip())
        else:
            resolved.add(requirement)
    return resolved


def _names(requirements: Iterable[str]) -> set[str]:
    """The distribution names one requirement list installs.

    An extra's members are REQUIREMENTS, and a version floor constrains a
    member rather than adding one, so a ROSTER is compared by name and
    `polars>=1.3` still reads as polars. PEP 508 owns that parse and
    `packaging` implements it; every installer already ships it, pytest
    depends on it, and the minimal version matrix therefore has it too. The
    pin assertions below stay on the exact strings, which is the other half
    of the same distinction: a roster says WHICH package, a pin says which
    version of it.
    """
    return {Requirement(requirement).name for requirement in requirements}


def test_every_extra_installs_packages_and_never_a_library():
    """The ruling, read off the manifest: an extra names our own packages.

    Every library the Python seat can be extended by is its own distribution
    under `extensions/python/ext/`, and an extra is the convenience name for a
    set of them, the shape `apache-airflow[amazon]` has. So the command a user
    types does not change and this file names no third-party library; that
    every name here IS a workspace member is what
    `tests/checks/check_layering.py` holds.
    """
    extras = _manifest()["project"]["optional-dependencies"]
    assert _names(extras["arrays"]) == {"metta-arrays", "metta-faiss", "metta-numpy"}
    # Two producers answering two questions: one builds the C structs a
    # PyCapsule carries, the other writes and reads the IPC streaming format
    # that crosses the gateway as bytes.
    assert _names(extras["arrow"]) == {"metta-nanoarrow", "metta-pyarrow"}
    assert _names(extras["das"]) == {"metta-websocket"}
    assert _names(extras["dataframes"]) == {"metta-pandas", "metta-polars", "metta-tables"}
    assert _names(extras["graphql"]) == {"metta-graphql"}
    assert _names(extras["models"]) == {"metta-pydantic"}
    assert _names(extras["otel"]) == {"metta-otel"}
    assert _names(extras["sql"]) == {"metta-duckdb", "metta-sqlite", "metta-tables"}
    assert _names(extras["live"]) == {"metta-live"}
    assert _names(extras["remote"]) == {"metta-remote"}
    # The engine is the one dependency that is not a package of ours: it is
    # the bridge this seat embeds, not a library it integrates with.
    assert _names(extras["engine"]) == {"janus-swi"}
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
    assert {"pytest-xdist>=3.8,<4", "networkx>=3.6,<4"} <= test_requirements
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
    # Every INTEGRATION extra, read from the manifest rather than listed here,
    # so a new one cannot reach the floor unnoticed the way `arrow` would have:
    # the three that were named by hand missed it the day it shipped.
    integrations = set().union(
        *(
            _names(members)
            for extra, members in extras.items()
            if extra not in {"engine", "test", "checks"}
        )
    )
    integrations |= {"networkx"}
    for package in sorted(integrations):
        assert package not in matrix, package


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
    # The WHOLE job, not one line of it. The install was a single line when
    # this was written and reading it that way made the check hostage to
    # formatting: splitting it in two raised StopIteration before a single
    # dependency was compared.
    installed = set(_version_matrix_job().split())
    manifest = _manifest()["project"]
    # The `engine` extra is checked beside the required list, not instead of
    # it: janus-swi moved there so a plain install cannot fail inside its
    # build, and a suite that runs the engine still needs it. Reading only
    # `dependencies` would have stopped noticing the day it moved.
    required = [*manifest["dependencies"], *manifest["optional-dependencies"]["engine"]]
    for requirement in required:
        name = Requirement(requirement).name
        # janus-swi is spelled with the underscore its distribution uses,
        # because --no-binary names the same package again.
        assert {name, name.replace("-", "_")} & installed, requirement
    # And the package is INSTALLED rather than put on the path, because metta
    # ships its pytest fixtures through the pytest11 entry point and an entry
    # point exists only for an installed distribution.
    assert "-e" in installed, _version_matrix_job()


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


def test_source_tree_fixtures_coexist_with_installed_plugin_metadata(tmp_path):
    """The repository suite loads its fixture plugin exactly once.

    A wheel build leaves distribution metadata beside the source. Pytest then
    discovers the shipped entry point before it reads the repository
    conftest, the same order as an editable installation.
    """
    metadata = tmp_path / "pymetta-0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: pymetta\nVersion: 0\n",
        encoding="utf-8",
    )
    (metadata / "entry_points.txt").write_text(
        "[pytest11]\nmetta = metta.pytest_plugin\n",
        encoding="utf-8",
    )
    environment = os.environ | {
        "PYTHONPATH": os.pathsep.join(
            (str(tmp_path), str(ROOT / "extensions" / "python"))
        )
    }
    environment.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/ch16_events_and_standing_queries/test_events.py::"
            "test_an_abandoned_watch_cancels_itself",
            "-q",
            # The gate's own flag, and this is the only child that needs it:
            # the others set PYTEST_DISABLE_PLUGIN_AUTOLOAD, while this one
            # POPS it, because autoload finding the entry point is the whole
            # claim. That also loads pytest-benchmark, which warns
            # "Benchmarks are automatically disabled because xdist plugin is
            # active" during pytest_configure whenever it sees the
            # PYTEST_XDIST_WORKER this child inherits from its worker -- and
            # under `filterwarnings = error` a warning raised there is an
            # INTERNALERROR before a single test runs [measured 2026-09-07].
            "-p",
            "no:benchmark",
        ],
        cwd=ROOT / "extensions" / "python",
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


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
    1.16x. _atoms/model.py is deliberately not in the compiled set and
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
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    built = sorted(
        path.name.split(".")[0]
        for path in (tmp_path / "compiled" / "lib" / "metta").rglob("*.so")
    )
    assert built == ["factories", "wire"]

    # Complete the built package with interpreted modules. Its two compiled
    # extensions win normal import resolution over the copied Python sources.
    compiled_package = tmp_path / "compiled" / "lib"
    shutil.copytree(
        ROOT / "extensions/python/metta", compiled_package / "metta",
        dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "_runtime"),
    )
    executed = subprocess.run(
        [sys.executable, "-c", """
import importlib.machinery
import pickle
from fractions import Fraction
import metta._atoms.factories as factories
import metta._atoms.wire as wire
from metta import Expression, G, MeTTa, S, arrow, convert, lib, typed
import sys
for module in (factories, wire):
    assert any(module.__file__.endswith(suffix) for suffix in importlib.machinery.EXTENSION_SUFFIXES)
value = Fraction(1, 3)
atom = convert.atom_from_wire(["n", value])
assert atom != G(value)
assert pickle.loads(pickle.dumps(atom)).to_wire() == ["n", value]
assert Expression(sorted([G(1), atom, G(0)])) == Expression(G(0), atom, G(1))
assert arrow(int, float) == Expression(S["->"], S.Number, S.Number)
assert typed(S.f, int) == Expression(S[":"], S.f, S.Number)
with MeTTa(metta_path=sys.argv[1]) as engine:
    engine += lib.vector
    ratios = engine.fn.vector_divide((1, 2), (3, 3)).one()
    assert engine.fn.vector_scale(ratios, 3).one() == (1, 2)
""", str(ROOT)],
        cwd=tmp_path, env=os.environ | {"PYTHONPATH": str(compiled_package)},
        capture_output=True, text=True, check=False,
    )
    assert executed.returncode == 0, executed.stdout + executed.stderr

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
        # why metta/_binding/shim.pl needs no directive of its own.
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

    In a checkout the shim is `extensions/python/metta/_binding/shim.pl` and the engine
    is four levels up; in a wheel the shim is `metta/_binding/shim.pl` and the engine
    is in the sibling runtime, at `metta/_runtime/engine/`. The directive used to spell
    the checkout's depth, so the installed copy resolved it to nothing --- and
    a `use_module` that resolves to nothing only WARNS, so the wheel loaded,
    booted, answered arithmetic, and failed every metta._binding.json call with
    `Unknown procedure: json_codec_write/3` [measured 2026-08-29 against a
    wheel installed into a fresh venv outside the checkout].
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    shim = (ROOT / "extensions" / "python" / "metta" / "_binding" / "json.pl").read_text(
        encoding="utf-8"
    )
    # Both layouts are named, and the search runs from the shim's own directory
    # rather than from one hard-coded depth.
    assert "prolog_load_context(directory, Here)" in shim, (
        "the shim no longer resolves the codec from its own directory"
    )
    for layout in ("'../../../../engine/json_codec.pl'", "'../_runtime/engine/json_codec.pl'"):
        assert layout in shim, f"the shim stopped looking for the codec at {layout}"

    import metta._binding.json as _json

    # Calling it is the proof the alias resolved: json_codec_write/3 reaches
    # this side only through that import, and it is the half that was broken
    # in the wheel while arithmetic went on answering.
    assert _json.loads(_json.dumps({"a": [1, 2]})) == {"a": [1, 2]}
