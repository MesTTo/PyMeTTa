"""Purpose: hold metta._host.activate() to its contract over a planted bundled host.

A Linux wheel of pymetta carries the patched SWI home and the janus bridge
built against it; the py3-none-any wheel and a checkout carry neither. Each
case plants the two directories a wheel would hold in its own scratch tree and
points the module at them, so the rule is exercised as it ships without a
wheel having to be built for the suite.
Guarantees:
  - with no bundled home, activate() answers None and touches neither
    SWI_HOME_DIR nor sys.path [tested: test_a_checkout_carries_no_host]
  - with one, it sets SWI_HOME_DIR and puts the vendor directory first on
    sys.path, once however often it is called
    [tested: test_the_bundled_host_is_selected_once]
  - it refuses a foreign SWI_HOME_DIR and a janus_swi imported from anywhere
    but the vendor directory, and accepts the vendored one
    [tested: test_a_foreign_home_is_refused, test_a_foreign_bridge_is_refused,
    test_the_vendored_bridge_on_a_foreign_home_is_refused,
    test_the_vendored_bridge_already_loaded_is_accepted]
Open Obligations:
  To Do: None
  Hacks: None
  Future Enhancements: None
"""

import sys
import types
from pathlib import Path

import pytest

from metta import _host


@pytest.fixture
def bundled(tmp_path, monkeypatch):
    """A planted host: the home and vendor directories a Linux wheel holds."""
    home = tmp_path / "swipl" / "lib" / "swipl"
    home.mkdir(parents=True)
    vendor = tmp_path / "_vendor"
    vendor.mkdir()
    monkeypatch.setattr(_host, "HOME", home)
    monkeypatch.setattr(_host, "_VENDOR", vendor)
    monkeypatch.delenv("SWI_HOME_DIR", raising=False)
    monkeypatch.delitem(sys.modules, "janus_swi", raising=False)
    monkeypatch.setattr(sys, "path", list(sys.path))
    return home, vendor


def test_a_checkout_carries_no_host(monkeypatch):
    """With no bundled home, activate() answers None and changes nothing."""
    monkeypatch.setattr(_host, "HOME", None)
    monkeypatch.setenv("SWI_HOME_DIR", "/untouched")
    before = list(sys.path)
    assert _host.activate() is None
    assert sys.path == before
    assert _host.os.environ["SWI_HOME_DIR"] == "/untouched"


def test_the_bundled_host_is_selected_once(bundled):
    """A bundled home becomes SWI_HOME_DIR and its vendor directory leads sys.path, once."""
    home, vendor = bundled
    assert _host.activate() == home
    assert _host.activate() == home
    assert _host.os.environ["SWI_HOME_DIR"] == str(home)
    assert sys.path[0] == str(vendor)
    assert sys.path.count(str(vendor)) == 1


@pytest.mark.usefixtures("bundled")
def test_a_foreign_home_is_refused(monkeypatch):
    """An SWI_HOME_DIR naming another home is refused, not overridden."""
    monkeypatch.setenv("SWI_HOME_DIR", "/usr/lib/swi-prolog")
    with pytest.raises(RuntimeError, match="Unset SWI_HOME_DIR"):
        _host.activate()


@pytest.mark.usefixtures("bundled")
def test_a_foreign_bridge_is_refused(monkeypatch):
    """A janus_swi already imported from elsewhere is refused."""
    foreign = types.ModuleType("janus_swi")
    foreign.__file__ = "/usr/lib/python3/dist-packages/janus_swi/__init__.py"
    monkeypatch.setitem(sys.modules, "janus_swi", foreign)
    with pytest.raises(RuntimeError, match="not the bridge this pymetta carries"):
        _host.activate()


def test_the_vendored_bridge_on_a_foreign_home_is_refused(bundled, monkeypatch):
    """The vendored janus_swi is still refused when SWI_HOME_DIR names another home."""
    home, vendor = bundled
    ours = types.ModuleType("janus_swi")
    ours.__file__ = str(Path(vendor) / "janus_swi" / "__init__.py")
    monkeypatch.setitem(sys.modules, "janus_swi", ours)
    monkeypatch.setenv("SWI_HOME_DIR", "/usr/lib/swi-prolog")
    with pytest.raises(RuntimeError, match="Unset SWI_HOME_DIR"):
        _host.activate()


def test_the_vendored_bridge_already_loaded_is_accepted(bundled, monkeypatch):
    """The vendored janus_swi, already imported, is accepted with the bundled home."""
    home, vendor = bundled
    ours = types.ModuleType("janus_swi")
    ours.__file__ = str(Path(vendor) / "janus_swi" / "__init__.py")
    monkeypatch.setitem(sys.modules, "janus_swi", ours)
    assert _host.activate() == home
