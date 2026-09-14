"""Purpose: verify atom-index loading from source and compiled Prolog.

Guarantees: runtime artifact presence selects a usable index even when the
QLF was compiled with the C artifact [tested:
test_atom_index_loads_with_runtime_artifact_presence; commit=dfd348d37d4cbe3d42d877bd6dcf415b54f82179].
Owns resources: pytest owns copied artifacts; every subprocess is joined.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("compiled", (False, True))
@pytest.mark.parametrize("native", (False, True))
@pytest.mark.parametrize("autoload", (False, True))
def test_atom_index_loads_with_runtime_artifact_presence(tmp_path, compiled, native, autoload):
    """A cached wrapper cannot assume its build machine's optional artifact."""
    artifact = ROOT / "engine/atom_index.so"
    if not artifact.exists():
        pytest.skip("build engine/atom_index.so to exercise artifact transitions")
    source = tmp_path / "atom_index.pl"
    binary = tmp_path / "atom_index.so"
    shutil.copyfile(ROOT / "engine/atom_index.pl", source)
    shutil.copyfile(artifact, binary)
    if compiled:
        result = subprocess.run(
            ["swipl", "-q", "-f", "none", "-g", "qcompile('atom_index.pl'),halt"],
            cwd=tmp_path, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        source = source.with_suffix(".qlf")
    if not native:
        binary.unlink()
    result = subprocess.run(
        ["swipl", "-q", "-f", "none", "-g",
         f"set_prolog_flag(autoload,{str(autoload).lower()}),use_module('{source.name}'),"
         "metta_atom_index_new(I),metta_atom_index_bind(I,key,X,true),"
         "metta_atom_index_get(I,key,Y),X==Y,"
         "\\+ (metta_atom_index_bind(I,new,_,true),fail),"
         "\\+metta_atom_index_get(I,new,_),"
         "(predicate_property(atom_index:metta_c_atom_index_new(_),foreign)"
         "->writeln(native);writeln(prolog)),halt"],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stderr, result.stderr
    assert result.stdout.strip() == ("native" if native else "prolog")


def test_atom_index_reload_preserves_native_owner(tmp_path):
    """Reconsulting the wrapper leaves existing native indexes usable."""
    artifact = ROOT / "engine/atom_index.so"
    if not artifact.exists():
        pytest.skip("build engine/atom_index.so to exercise native reload")
    shutil.copyfile(ROOT / "engine/atom_index.pl", tmp_path / "atom_index.pl")
    shutil.copyfile(artifact, tmp_path / "atom_index.so")
    result = subprocess.run(
        ["swipl", "-q", "-f", "none", "-s", "atom_index.pl", "-g",
         "metta_atom_index_new(I),metta_atom_index_bind(I,key,X,true),"
         "load_files('atom_index.pl',[if(true)]),"
         "predicate_property(atom_index:metta_c_atom_index_new(_),foreign),"
         "metta_atom_index_get(I,key,Y),X==Y,halt"],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_broken_atom_index_artifact_refuses_engine_loading(tmp_path):
    """The engine's load boundary preserves a present artifact's error."""
    shutil.copyfile(ROOT / "engine/atom_index.pl", tmp_path / "atom_index.pl")
    shutil.copyfile(ROOT / "engine/source_loading.pl", tmp_path / "source_loading.pl")
    (tmp_path / "atom_index.so").write_text("invalid shared object\n")
    result = subprocess.run(
        ["swipl", "-q", "-f", "none", "-s", "source_loading.pl", "-g",
         "catch((loading_loudly(use_module('atom_index.pl')),halt(1)),"
         "error(metta_load_failed(_),_),halt)"],
        cwd=tmp_path, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "atom_index.so" in result.stderr
