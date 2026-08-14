import importlib
import os
from pathlib import Path

import pytest

from petta import MeTTa

try:
    from hypothesis import settings
except ModuleNotFoundError:
    pass
else:
    # A red example must be reproducible: every failure prints its
    # reproduction blob, and HYPOTHESIS_PROFILE=ci derandomizes whole
    # runs while the default keeps exploring fresh examples.
    settings.register_profile("petta", print_blob=True)
    settings.register_profile("ci", print_blob=True, derandomize=True)
    settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "petta"))


@pytest.fixture(scope="session")
def repo_root():
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def petta_module():
    return importlib.import_module("petta")


@pytest.fixture(scope="session")
def petta_path(repo_root):
    return str(repo_root)


@pytest.fixture(scope="session")
def petta_instance(petta_module, petta_path):
    return petta_module.PeTTa(verbose=False, petta_path=petta_path)


@pytest.fixture(scope="session")
def petta_verbose(petta_module, petta_path):
    return petta_module.PeTTa(verbose=True, petta_path=petta_path)


@pytest.fixture(scope="session")
def dummy_metta_path(repo_root):
    return repo_root / "python" / "tests" / "data" / "dummy.metta"


@pytest.fixture(scope="session")
def metta(petta_path):
    """The rich surface, on the same engine the legacy fixtures use."""
    os.environ.setdefault("PETTA_PATH", petta_path)
    return MeTTa(petta_path=petta_path)
