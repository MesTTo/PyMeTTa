"""Purpose: prove scaffold names, packaging shape and failed-write cleanup.

Guarantees: no rejected input or failed write leaves a partial distribution,
and generated declarations carry the same namespace as their metadata
[tested: this file; commit=WORKTREE].
"""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from metta.__main__ import _extension_files, main


@given(st.from_regex(r"[A-Z][a-z]{1,8}[-._][a-z]{1,8}", fullmatch=True))
def test_scaffold_projects_normalized_names_into_all_sources(name):
    """Mixed case and separators stay consistent across metadata and source."""
    files = _extension_files(name)
    manifest = tomllib.loads(files["pyproject.toml"])
    project = manifest["project"]
    (module,) = manifest["tool"]["setuptools"]["py-modules"]
    assert project["entry-points"]["metta.extensions"] == {project["name"]: module + ":register"}
    assert module + ".py" in files
    for path, source in files.items():
        if path.endswith(".py"):
            ast.parse(source, filename=path)
    assert f'Provider("{project["name"]}", "{module}")' in files[module + ".py"]
    assert f"context.{module}.echo(42)" in files[f"tests/test_{module}.py"]


@pytest.mark.parametrize("name", ["", "../outside", "bad/name", "bad\\name", "a\n", "λ", "_private", "9lives", "class", "metta", "sys", "eval"])
def test_scaffold_refuses_invalid_or_reserved_names_before_writing(name, tmp_path, monkeypatch):
    """Every refusal leaves the selected working directory untouched."""
    monkeypatch.chdir(tmp_path)
    assert main(["extension", "new", name]) == 1
    assert not list(tmp_path.iterdir())


def test_scaffold_keeps_an_existing_directory_and_its_contents(tmp_path, monkeypatch):
    """A second invocation cannot overwrite or remove a user's directory."""
    monkeypatch.chdir(tmp_path)
    target = tmp_path / "aurora"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("owned before the command")
    assert main(["extension", "new", "aurora"]) == 1
    assert sentinel.read_text() == "owned before the command"
    assert list(target.iterdir()) == [sentinel]


def test_scaffold_removes_partial_output(tmp_path, monkeypatch, capsys):
    """A write refusal after earlier files removes the newly owned directory."""
    monkeypatch.chdir(tmp_path)
    original = Path.open

    def refuse_readme(path, *args, **kwargs):
        if path.name == "README.md":
            message = "fixture disk write refused"
            raise OSError(message)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", refuse_readme)
    assert main(["extension", "new", "aurora"]) == 1
    assert "fixture disk write refused" in capsys.readouterr().err
    assert not list(tmp_path.iterdir())


def test_scaffold_cleanup_failure_retains_both_errors(tmp_path, monkeypatch):
    """Failure to abandon a partial tree cannot mask the original write error."""
    import shutil

    monkeypatch.chdir(tmp_path)
    original = Path.open

    def refuse_readme(path, *args, **kwargs):
        if path.name == "README.md":
            message = "fixture disk write refused"
            raise OSError(message)
        return original(path, *args, **kwargs)

    def refuse_cleanup(_path):
        message = "fixture cleanup refused"
        raise PermissionError(message)

    monkeypatch.setattr(Path, "open", refuse_readme)
    monkeypatch.setattr(shutil, "rmtree", refuse_cleanup)
    with pytest.raises(ExceptionGroup) as caught:
        main(["extension", "new", "aurora"])
    assert [str(error) for error in caught.value.exceptions] == ["fixture disk write refused", "fixture cleanup refused"]


def test_scaffold_writes_every_documented_member_part(tmp_path, monkeypatch):
    """The command's tree contains every documented member part."""
    monkeypatch.chdir(tmp_path)
    assert main(["extension", "new", "Aurora-Beam"]) == 0
    target = tmp_path / "Aurora-Beam"
    files = {str(path.relative_to(target)): path.read_text() for path in target.rglob("*") if path.is_file()}
    assert files == _extension_files("Aurora-Beam")
    assert {"pyproject.toml", "aurora_beam.py", "README.md", "MANIFEST.in", "tests/test_aurora_beam.py", "examples/echo.py", "benchmarks/echo.py"} == files.keys()
