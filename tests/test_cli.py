"""Purpose: command-line launcher arguments, environment, and error paths.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import os
import subprocess
import sys
from unittest.mock import Mock

import pytest

from petta import cli


def test_package_import_does_not_require_janus():  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    program = (
        "import importlib\n"
        "real_import_module = importlib.import_module\n"
        "def guarded_import_module(name, package=None):\n"
        "    if name == 'janus_swi':\n"
        "        raise AssertionError('janus_swi imported during package import')\n"
        "    return real_import_module(name, package)\n"
        "importlib.import_module = guarded_import_module\n"
        "import petta\n"
        "import petta.cli\n"
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
    monkeypatch.setattr(cli, "_resolve_petta_path", lambda: str(runtime))
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
            "backends",
        ]
    )


def test_main_asks_for_native_backends_and_names_none(monkeypatch, tmp_path):
    """The launcher asks the engine to load every backend that is built, and
    knows about no backend in particular.

    It used to test for MORK's shared library and LD_PRELOAD it, so a second
    native backend needed a second branch in a file that has nothing to do with
    backends. Which backends exist is backends/*.pl now, and whether one is
    usable is that backend's own business. The preload went with it: a backend
    opens its own library with global symbol visibility.
    """  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose
    runtime = tmp_path / "runtime"
    call = Mock(return_value=0)
    monkeypatch.setattr(cli, "_resolve_petta_path", lambda: str(runtime))
    monkeypatch.setattr(cli.subprocess, "call", call)

    assert cli.main(["program.metta"]) == 0

    command = call.call_args.args[0]
    assert command[-2:] == ["program.metta", "backends"]
    assert not any("mork" in part for part in command)
    assert "env" not in call.call_args.kwargs


def test_main_names_the_missing_swipl_binary(monkeypatch, tmp_path):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    runtime = tmp_path / "runtime"
    main_file = runtime / "engine" / "main.pl"
    main_file.parent.mkdir(parents=True)
    main_file.touch()
    monkeypatch.setattr(cli, "_resolve_petta_path", lambda: str(runtime))
    monkeypatch.setattr(
        cli.subprocess,
        "call",
        Mock(side_effect=FileNotFoundError("swipl")),
    )

    with pytest.raises(FileNotFoundError, match=r"SWI-Prolog.*swipl.*PATH"):
        cli.main([])
