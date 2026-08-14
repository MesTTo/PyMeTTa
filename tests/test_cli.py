"""Purpose: command-line launcher arguments, environment, and error paths.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import os
from unittest.mock import Mock

import pytest

from petta import cli


def test_main_forwards_arguments_and_exit_status(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime with spaces"
    main_file = runtime / "src" / "main.pl"
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
        ],
        env=None,
    )


def test_main_preserves_optional_mork_behavior(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    mork_library = (
        runtime / "mork_ffi" / "target" / "release" / "libmork_ffi.so"
    )
    mork_library.parent.mkdir(parents=True)
    mork_library.touch()
    call = Mock(return_value=0)
    monkeypatch.setattr(cli, "_resolve_petta_path", lambda: str(runtime))
    monkeypatch.setattr(cli.subprocess, "call", call)
    monkeypatch.setenv("PETTA_CLI_TEST", "inherited")
    monkeypatch.setenv("LD_PRELOAD", "/caller/libexisting.so")

    assert cli.main(["program.metta"]) == 0

    command = call.call_args.args[0]
    child_env = call.call_args.kwargs["env"]
    assert command[-2:] == ["program.metta", "mork"]
    assert child_env["LD_PRELOAD"] == os.pathsep.join(
        (str(mork_library), "/caller/libexisting.so")
    )
    assert child_env["PETTA_CLI_TEST"] == "inherited"
    assert child_env is not os.environ


def test_main_names_the_missing_swipl_binary(monkeypatch, tmp_path):
    runtime = tmp_path / "runtime"
    main_file = runtime / "src" / "main.pl"
    main_file.parent.mkdir(parents=True)
    main_file.touch()
    monkeypatch.setattr(cli, "_resolve_petta_path", lambda: str(runtime))
    monkeypatch.setattr(
        cli.subprocess,
        "call",
        Mock(side_effect=FileNotFoundError("swipl")),
    )

    with pytest.raises(FileNotFoundError, match="SWI-Prolog.*swipl.*PATH"):
        cli.main([])
