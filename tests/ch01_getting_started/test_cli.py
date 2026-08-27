"""Purpose: command-line launcher arguments, environment, and error paths.
Guarantees:
  - both retained upstream and current runtime layouts keep their own command
    contracts [tested: test_main_retains_the_upstream_layout and
    test_main_forwards_arguments_and_exit_status; commit=f88aa8be03cb64cb59d3307515ded8701f418321]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from metta import cli


def test_package_import_does_not_require_janus():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    program = (
        "import importlib\n"
        "real_import_module = importlib.import_module\n"
        "def guarded_import_module(name, package=None):\n"
        "    if name == 'janus_swi':\n"
        "        raise AssertionError('janus_swi imported during package import')\n"
        "    return real_import_module(name, package)\n"
        "importlib.import_module = guarded_import_module\n"
        "import metta\n"
        "import metta.cli\n"
    )
    done = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        text=True,
        timeout=30,
    )
    assert done.returncode == 0, done.stderr


def test_main_forwards_arguments_and_exit_status(monkeypatch, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime = tmp_path / "runtime with spaces"
    main_file = runtime / "engine" / "main.pl"
    main_file.parent.mkdir(parents=True)
    main_file.touch()
    call = Mock(return_value=23)
    monkeypatch.setattr(cli, "_resolve_metta_path", lambda: str(runtime))
    monkeypatch.setattr(cli.subprocess, "call", call)

    status = cli.main(["program with spaces.metta", "--example"])

    assert status == 23
    call.assert_called_once_with(
        [
            "swipl",
            f"--stack_limit={cli.config.stack_limit}",
            "-q",
            "-s",
            str(main_file),
            "--",
            "program with spaces.metta",
            "--example",
            "extensions",
        ]
    )


def test_main_retains_the_upstream_layout(monkeypatch, tmp_path):
    """A ``src/main.pl`` runtime receives the upstream command unchanged."""
    runtime = tmp_path / "upstream runtime with spaces"
    main_file = runtime / "src" / "main.pl"
    main_file.parent.mkdir(parents=True)
    main_file.touch()
    call = Mock(return_value=23)
    monkeypatch.setattr(cli, "_resolve_metta_path", lambda: str(runtime))
    monkeypatch.setattr(cli.subprocess, "call", call)

    assert cli.main(["program with spaces.metta", "--example"]) == 23
    call.assert_called_once_with(
        [
            "swipl",
            "--stack_limit=8g",
            "-q",
            "-s",
            str(main_file),
            "--",
            "program with spaces.metta",
            "--example",
        ],
        env=None,
    )


def test_main_retains_the_upstream_optional_mork_preload(monkeypatch, tmp_path):
    """The original runtime still opts into its own MORK shared library."""
    runtime = tmp_path / "upstream runtime"
    mork_library = runtime / "mork_ffi" / "target" / "release" / "libmork_ffi.so"
    mork_library.parent.mkdir(parents=True)
    mork_library.touch()
    call = Mock(return_value=0)
    monkeypatch.setattr(cli, "_resolve_metta_path", lambda: str(runtime))
    monkeypatch.setattr(cli.subprocess, "call", call)
    monkeypatch.setenv("METTA_CLI_TEST", "inherited")

    assert cli.main(["program.metta"]) == 0
    assert call.call_args.args[0][-2:] == ["program.metta", "mork"]
    child_env = call.call_args.kwargs["env"]
    assert child_env["LD_PRELOAD"] == str(mork_library)
    assert child_env["METTA_CLI_TEST"] == "inherited"
    assert child_env is not os.environ


def test_main_asks_for_native_backends_and_names_none(monkeypatch, tmp_path):
    """The launcher asks the engine to load every seat whose needs hold, and
    knows about no seat in particular.

    It used to test for MORK's shared library and LD_PRELOAD it, so a second
    native backend needed a second branch in a file that has nothing to do with
    backends. Which seats exist is extensions/*/extension.pl now, and whether
    one is usable is that seat's own declaration. The preload went with it: a
    backend opens its own library with global symbol visibility.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    runtime = tmp_path / "runtime"
    call = Mock(return_value=0)
    monkeypatch.setattr(cli, "_resolve_metta_path", lambda: str(runtime))
    monkeypatch.setattr(cli.subprocess, "call", call)

    assert cli.main(["program.metta"]) == 0

    command = call.call_args.args[0]
    assert command[-2:] == ["program.metta", "extensions"]
    assert not any("mork" in part for part in command)
    assert "env" not in call.call_args.kwargs


def test_main_names_the_missing_swipl_binary(monkeypatch, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime = tmp_path / "runtime"
    main_file = runtime / "engine" / "main.pl"
    main_file.parent.mkdir(parents=True)
    main_file.touch()
    monkeypatch.setattr(cli, "_resolve_metta_path", lambda: str(runtime))
    monkeypatch.setattr(
        cli.subprocess,
        "call",
        Mock(side_effect=FileNotFoundError("swipl")),
    )

    with pytest.raises(FileNotFoundError, match=r"SWI-Prolog.*swipl.*PATH"):
        cli.main([])


def test_the_bare_demo_runs_the_interop_example_and_backend_selftests():
    """The no-argument launcher is the first thing a human runs, and no lane
    executed it: the space model moved &self out of user and the demo's bare
    listing raised across two green batteries, while the MORK selftest had
    failed silently since add-atom's answer became unit, swallowed by
    forall/2 over solutions. Exit 0, the printed answer, and the selftest's
    own output line pin all three, in the bare form and the extensions form
    the packaged launcher passes.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    repo = Path(__file__).resolve().parents[4]
    mork_built = (
        repo / "extensions" / "mork" / "mork_ffi" / "target" / "release" / "libmork_ffi.so"
    ).exists()
    for extra in ([], ["--", "extensions"]):
        done = subprocess.run(
            ["swipl", "-q", "-s", str(repo / "engine" / "main.pl"), *extra],
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
            timeout=120,
            check=False,
            cwd=repo,
        )
        assert done.returncode == 0, (extra, done.stdout, done.stderr)
        assert "mettafunc(30) = 31" in done.stdout, (extra, done.stdout)
        if extra and mork_built:
            assert "MORK query result:" in done.stdout, done.stdout


def test_the_launcher_answers_version_and_help_without_booting(capsys):
    """A released command answers `--version`; it does not report a missing file.

    The bare `metta` command keeps upstream's launcher contract and forwards
    everything to the engine, which is deliberate and documented. Forwarding
    these two produced `source_sink '--version' does not exist`, an engine error
    about a missing FILE in answer to the one flag every installed tool is asked
    first. They are answered ONLY as the whole command line, so a MeTTa program
    taking its own `--help` still receives it, and answering them boots nothing.
    """
    from metta._version import __version__
    from metta.cli import main

    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"metta {__version__}"

    assert main(["-V"]) == 0
    assert capsys.readouterr().out.strip() == f"metta {__version__}"

    assert main(["--help"]) == 0
    printed = capsys.readouterr().out
    assert "usage: metta" in printed
    assert "python -m metta" in printed, "the help names the subcommand surface"

    # Not the whole command line, so it belongs to the program being run.
    assert "--help" not in metta_cli_self_answered_for(["program.metta", "--help"])


def metta_cli_self_answered_for(argv):
    """Which of argv the launcher would answer itself, as a set."""
    from metta.cli import SELF_ANSWERED

    return {flag for flag in argv if len(argv) == 1 and flag in SELF_ANSWERED}
