import importlib
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def repo_root():
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def petta_module():
    return importlib.import_module("python.petta")


@pytest.fixture(scope="session")
def metta_src_path(repo_root):
    return str(repo_root / "python")


@pytest.fixture(scope="session")
def petta_instance(petta_module, metta_src_path):
    return petta_module.PeTTa(verbose=False, metta_src_path=metta_src_path)


@pytest.fixture(scope="session")
def petta_verbose(petta_module, metta_src_path):
    return petta_module.PeTTa(verbose=True, metta_src_path=metta_src_path)


@pytest.fixture(scope="session")
def dummy_metta_path(repo_root):
    return repo_root / "python" / "tests" / "data" / "dummy.metta"
