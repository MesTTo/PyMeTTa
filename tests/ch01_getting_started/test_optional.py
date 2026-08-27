"""Purpose: optional imports distinguish an absent extra from a broken install.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""  # noqa: D205  -- the scenario narrative is one continuous invariant, not summary-and-body prose

import pytest

from metta import _optional


def test_optional_import_names_an_absent_requested_package(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    def missing(name):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        raise ModuleNotFoundError(name="example", path=None)

    monkeypatch.setattr(_optional, "import_module", missing)

    with pytest.raises(ImportError, match="install example-extra"):
        _optional.require_module("example.feature", "install example-extra")


def test_optional_import_preserves_broken_dependency_errors(monkeypatch):  # noqa: D103  -- pytest discovers or injects this callable; its descriptive name states the contract
    failure = ModuleNotFoundError(name="internal_dependency", path=None)

    def broken(name):  # noqa: ARG001  -- the test reflects this callable signature, so every declared parameter must remain visible
        raise failure

    monkeypatch.setattr(_optional, "import_module", broken)

    with pytest.raises(ModuleNotFoundError) as caught:
        _optional.require_module("example", "install example-extra")
    assert caught.value is failure
