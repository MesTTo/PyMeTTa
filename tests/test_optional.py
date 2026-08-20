"""Purpose: optional imports distinguish an absent extra from a broken install.
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None.
"""

import pytest

from petta import _optional


def test_optional_import_names_an_absent_requested_package(monkeypatch):
    def missing(name):
        raise ModuleNotFoundError(name="example", path=None)

    monkeypatch.setattr(_optional, "import_module", missing)

    with pytest.raises(ImportError, match="install example-extra"):
        _optional.require_module("example.feature", "install example-extra")


def test_optional_import_preserves_broken_dependency_errors(monkeypatch):
    failure = ModuleNotFoundError(name="internal_dependency", path=None)

    def broken(name):
        raise failure

    monkeypatch.setattr(_optional, "import_module", broken)

    with pytest.raises(ModuleNotFoundError) as caught:
        _optional.require_module("example", "install example-extra")
    assert caught.value is failure
